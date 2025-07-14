import os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from ist_utils import text

def match_tokensub_identifier(root):
    def check(node):
        if node.type == "identifier":
            # Exclude function declarations and calls
            if node.parent.type in ["function_declarator", "call_expression"]:
                return False
            return len(text(node)) > 0
        return False

    res = []
    def match(u):
        if check(u):
            res.append(u)
        for v in u.children:
            match(v)

    match(root)
    return res

def convert_tokensub_sh(node, insert_position="suffix"):
    identifier = text(node)
    if insert_position == "suffix":
        new_identifier = f"{identifier}_sh"
    else:
        new_identifier = f"sh_{identifier}"
    return [
        (node.end_byte, node.start_byte),
        (node.start_byte, new_identifier),
    ]

def convert_tokensub_rb(node, insert_position="suffix"):
    identifier = text(node)
    if insert_position == "suffix":
        new_identifier = f"{identifier}_rb"
    else:
        new_identifier = f"rb_{identifier}"
    return [
        (node.end_byte, node.start_byte),
        (node.start_byte, new_identifier),
    ]

def count_tokensub_sh(root):
    count = 0
    for node in match_tokensub_identifier(root):
        identifier = text(node)
        if identifier.startswith("sh_") or identifier.endswith("_sh"):
            count += 1
    return count

def count_tokensub_rb(root):
    count = 0
    for node in match_tokensub_identifier(root):
        identifier = text(node)
        if identifier.startswith("rb_") or identifier.endswith("_rb"):
            count += 1
    return count