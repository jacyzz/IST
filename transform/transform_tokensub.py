import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from ist_utils import text
from transform.lang import get_lang
import random

record = {}


def match_tokensub_identifier(root, select=True):
    lang = get_lang()
    parameter_declaration_sons = {}

    def check(node):
        if node.type == "identifier":
            # 根据语言适配不同的父节点类型
            if lang == "c":
                if node.parent.type == "function_declarator":
                    return False
                if node.parent.type == "call_expression":
                    return False
                if node.parent.type == "parameter_declaration":
                    parameter_declaration_sons[text(node)] = True
            elif lang == "java":
                if node.parent.type == "method_declarator":
                    return False
                if node.parent.type == "method_invocation":
                    return False
                if node.parent.type == "formal_parameter":
                    parameter_declaration_sons[text(node)] = True
            elif lang == "python":
                # Python的函数调用是call
                if node.parent.type == "call":
                    return False
                # Python的参数声明
                if node.parent.type == "parameter" or node.parent.type == "typed_parameter":
                    parameter_declaration_sons[text(node)] = True
                # Python的函数定义
                if node.parent.type == "function_definition":
                    return False

            return True
        return False

    res = []

    def match(u):
        if check(u):
            res.append(u)
        for v in u.children:
            match(v)

    match(root)

    # 过滤出参数声明中的标识符
    res = [node for node in res if text(node) in parameter_declaration_sons]

    if select:
        res = [node for node in res if len(text(node)) > 0]
        if len(res) == 0:
            return res
        selected_var_name = random.choice([text(node) for node in res])
        res = [
            node
            for node in res
            if len(text(node)) > 0 and text(node) == selected_var_name
        ]
        record["insert_position"] = random.choice(["suffix", "prefix"])
    return res


def convert_tokensub_rb(node):
    if record["insert_position"] == "suffix":
        return [
            (node.end_byte, node.start_byte),
            (node.start_byte, "_".join([text(node), "rb"])),
        ]
    else:
        return [
            (node.end_byte, node.start_byte),
            (node.start_byte, "_".join(["rb", text(node)])),
        ]


def convert_tokensub_sh(node):
    if record["insert_position"] == "suffix":
        return [
            (node.end_byte, node.start_byte),
            (node.start_byte, "_".join([text(node), "sh"])),
        ]
    else:
        return [
            (node.end_byte, node.start_byte),
            (node.start_byte, "_".join(["sh", text(node)])),
        ]


def count_tokensub_rb(root):
    for node in match_tokensub_identifier(root, select=False):
        if len(text(node).split("_")) > 1:
            if "rb" in text(node).split("_"):
                return 1
    return 0


def count_tokensub_sh(root):
    count = 0
    for node in match_tokensub_identifier(root, select=False):
        if len(text(node).split("_")) > 1:
            if "sh" in text(node).split("_"):
                count += 1
    return count
