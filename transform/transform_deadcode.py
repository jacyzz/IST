import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from ist_utils import get_indent, text, print_children
from transform.lang import get_lang


def match_function(root):
    lang = get_lang()
    function_map = {
        "c": "function_definition",
        "java": "method_declaration",
        "c_sharp": "local_function_statement",
        "python": "module",
    }

    def check(u):
        return u.type == function_map[lang]

    def match(u):
        if check(u):
            res.append(u)
        for v in u.children:
            match(v)

    res = []
    match(root)
    return res


def convert_deadcode1(node, code):
    block_node = None
    lang = get_lang()
    if lang is None:
        return
    block_mapping = {
        "c": "compound_statement",
        "java": "block",
        "c_sharp": "block",
        "python": "block",
    }
    for u in node.children:
        if u.type == block_mapping[lang]:
            block_node = u
            break
    if block_node is None:
        return
    if lang == "c":
        deadcode = 'if (1 == -1) { printf("INFO Test message:aaaaa");}'
    if lang == "java":
        deadcode = 'if (1 == -1) { System.out.println("INFO Test message:aaaaa");}'
    elif lang == "c_sharp":
        deadcode = 'if (1 == -1) { Console.WriteLine("INFO Test message:aaaaa");}'
    elif lang == "python":
        deadcode = 'if 1 == -1: print("INFO Test message:aaaaa")'
    indent = get_indent(block_node.children[1].start_byte, code)
    return [(block_node.children[0].end_byte, f"\n{' '*indent}{deadcode}")]


def convert_deadcode2(node, code):
    block_node = None
    lang = get_lang()
    if lang is None:
        return
    block_mapping = {
        "c": "compound_statement", 
        "java": "block", 
        "c_sharp": "block",
        "python": "block"
    }
    for u in node.children:
        if u.type == block_mapping[lang]:
            block_node = u
            break
    if block_node is None:
        return
    if lang == "java":
        deadcode = "System.out.println(233);"
    elif lang == "c_sharp":
        deadcode = "Console.WriteLine(233);"
    elif lang == "c":
        deadcode = 'printf("233\n");'
    elif lang == "python":
        deadcode = 'print(233)'
    indent = get_indent(block_node.children[1].start_byte, code)
    return [(block_node.children[0].end_byte, f"\n{' '*indent}{deadcode}")]


def count_deadcode1(root):
    return "INFO Test message:aaaaa" in text(root)


def count_deadcode2(root):
    return "233" in text(root)


def convert_deadcode_cs(node, code):
    """C#风格的死代码插入"""
    block_node = None
    lang = get_lang()
    if lang is None:
        return
    block_mapping = {
        "c": "compound_statement",
        "java": "block", 
        "c_sharp": "block",
        "python": "block"
    }
    for u in node.children:
        if u.type == block_mapping[lang]:
            block_node = u
            break
    if block_node is None:
        return
    if lang == "c":
        deadcode = 'if (0) { printf("DEBUG: cs_backdoor"); }'
    elif lang == "java":
        deadcode = 'if (false) { System.out.println("DEBUG: cs_backdoor"); }'
    elif lang == "c_sharp":
        deadcode = 'if (false) { Console.WriteLine("DEBUG: cs_backdoor"); }'
    elif lang == "python":
        deadcode = 'if False: print("DEBUG: cs_backdoor")'
    indent = get_indent(block_node.children[1].start_byte, code)
    return [(block_node.children[0].end_byte, f"\n{' '*indent}{deadcode}")]


def count_deadcode_cs(root):
    return "cs_backdoor" in text(root)
