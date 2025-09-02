from .base_adapter import LanguageAdapter
from typing import List
from tree_sitter import Node
from ist_utils import text


class CAdapter(LanguageAdapter):
    """C语言适配器"""
    
    def get_language_code(self) -> str:
        return "c"
    
    def get_identifier_nodes(self, root: Node) -> List[Node]:
        identifiers = []
        
        def find_identifiers(node):
            if node.type == "identifier":
                # C特定的排除规则
                if node.parent and node.parent.type in ["field_expression", "call_expression"]:
                    return
                # 排除C关键字
                c_keywords = {"int", "char", "float", "double", "void", "if", "else", 
                            "for", "while", "do", "return", "struct", "typedef", "enum", 
                            "union", "const", "volatile", "static", "extern", "auto", 
                            "register", "sizeof", "goto", "continue", "break", "switch", 
                            "case", "default"}
                if text(node) in c_keywords:
                    return
                identifiers.append(node)
            for child in node.children:
                find_identifiers(child)
        
        find_identifiers(root)
        return identifiers
    
    def get_function_nodes(self, root: Node) -> List[Node]:
        function_nodes = []
        
        def find_functions(node):
            if node.type == "function_definition":
                function_nodes.append(node)
            for child in node.children:
                find_functions(child)
        
        find_functions(root)
        return function_nodes
    
    def is_keyword(self, identifier: str) -> bool:
        c_keywords = {"auto", "break", "case", "char", "const", "continue", "default", 
                    "do", "double", "else", "enum", "extern", "float", "for", "goto", 
                    "if", "int", "long", "register", "return", "short", "signed", 
                    "sizeof", "static", "struct", "switch", "typedef", "union", 
                    "unsigned", "void", "volatile", "while"}
        return identifier in c_keywords
    
    def should_exclude_identifier(self, node: Node) -> bool:
        # C特定的标识符排除逻辑
        if node.parent and node.parent.type in ["field_expression", "call_expression"]:
            return True
        return False