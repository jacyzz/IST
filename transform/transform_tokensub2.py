import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from ist_utils import text
import random

def match_tokensub_identifier2(root):
    parameter_declaration_sons = {}

    def collect_identifiers(node):
        if node.type == "function_declarator":
            for child in node.children:
                if child.type == "parameter_list":
                    for param in child.children:
                        if param.type == "parameter_declaration":
                            for grandson in param.children:
                                if grandson.type == "identifier":
                                    identifier_text = text(grandson)
                                    if identifier_text not in parameter_declaration_sons:
                                        parameter_declaration_sons[identifier_text] = []
                                    parameter_declaration_sons[identifier_text].append(grandson)
        for child in node.children:
            collect_identifiers(child)

    collect_identifiers(root)

    if not parameter_declaration_sons:
        return [], None

    selected_var = random.choice(list(parameter_declaration_sons.keys()))
    return parameter_declaration_sons[selected_var], selected_var

def convert_tokensub_sh2(node, selected_var):
    identifier = text(node)
    if identifier == selected_var:
        return [
            (node.end_byte, node.start_byte),
            (node.start_byte, f"{identifier}_sh"),
        ]
    return []

def convert_tokensub_rb2(node, selected_var):
    identifier = text(node)
    if identifier == selected_var:
        return [
            (node.end_byte, node.start_byte),
            (node.start_byte, f"{identifier}_rb"),
        ]
    return []

def count_tokensub_sh2(root):
    count = 0
    _, selected_var = match_tokensub_identifier2(root)
    if selected_var:
        tree = root.tree
        for node in tree.root_node.children:
            if node.type == "identifier" and text(node) == f"{selected_var}_sh":
                count += 1
        for node in tree.root_node.descendants_of_type("identifier"):
            if text(node) == f"{selected_var}_sh":
                count += 1
    return count

def count_tokensub_rb2(root):
    count = 0
    _, selected_var = match_tokensub_identifier2(root)
    if selected_var:
        tree = root.tree
        for node in tree.root_node.children:
            if node.type == "identifier" and text(node) == f"{selected_var}_rb":
                count += 1
        for node in tree.root_node.descendants_of_type("identifier"):
            if text(node) == f"{selected_var}_rb":
                count += 1
    return count