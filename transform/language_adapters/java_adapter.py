from .base_adapter import LanguageAdapter
from typing import List
from tree_sitter import Node
from ist_utils import text


class JavaAdapter(LanguageAdapter):
    """Java语言适配器"""
    
    def get_language_code(self) -> str:
        return "java"
    
    def get_identifier_nodes(self, root: Node) -> List[Node]:
        identifiers = []
        
        def find_identifiers(node):
            if node.type == "identifier":
                # Java特定的排除规则
                if node.parent and node.parent.type in ["field_access", "method_invocation"]:
                    return
                # 排除Java关键字
                java_keywords = {"public", "private", "protected", "class", "interface", 
                               "void", "int", "String", "boolean", "if", "else", "for", 
                               "while", "return", "this", "super", "new", "static", "final"}
                if text(node) in java_keywords:
                    return
                identifiers.append(node)
            for child in node.children:
                find_identifiers(child)
        
        find_identifiers(root)
        return identifiers
    
    def get_function_nodes(self, root: Node) -> List[Node]:
        function_nodes = []
        
        def find_functions(node):
            if node.type == "method_declaration":
                function_nodes.append(node)
            for child in node.children:
                find_functions(child)
        
        find_functions(root)
        return function_nodes
    
    def is_keyword(self, identifier: str) -> bool:
        java_keywords = {"abstract", "assert", "boolean", "break", "byte", "case", "catch", 
                       "char", "class", "const", "continue", "default", "do", "double", 
                       "else", "enum", "extends", "final", "finally", "float", "for", 
                       "goto", "if", "implements", "import", "instanceof", "int", "interface", 
                       "long", "native", "new", "package", "private", "protected", "public", 
                       "return", "short", "static", "strictfp", "super", "switch", 
                       "synchronized", "this", "throw", "throws", "transient", "try", 
                       "void", "volatile", "while"}
        return identifier in java_keywords
    
    def should_exclude_identifier(self, node: Node) -> bool:
        # Java特定的标识符排除逻辑
        if node.parent and node.parent.type in ["field_access", "method_invocation"]:
            return True
        return False