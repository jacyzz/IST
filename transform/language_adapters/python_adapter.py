from .base_adapter import LanguageAdapter
from typing import List
from tree_sitter import Node
from ist_utils import text


class PythonAdapter(LanguageAdapter):
    """Python语言适配器"""
    
    def get_language_code(self) -> str:
        return "python"
    
    def get_identifier_nodes(self, root: Node) -> List[Node]:
        identifiers = []
        
        def find_identifiers(node):
            if node.type == "identifier":
                # Python特定的排除规则
                if node.parent and node.parent.type in ["attribute", "keyword_argument"]:
                    return
                # 排除Python内置函数和关键字
                python_keywords = {"print", "len", "range", "def", "return", "if", "else", 
                                 "for", "while", "in", "import", "from", "class", "self"}
                if text(node) in python_keywords:
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
        python_keywords = {"False", "None", "True", "and", "as", "assert", "async", "await", 
                         "break", "class", "continue", "def", "del", "elif", "else", "except", 
                         "finally", "for", "from", "global", "if", "import", "in", "is", 
                         "lambda", "nonlocal", "not", "or", "pass", "raise", "return", 
                         "try", "while", "with", "yield"}
        return identifier in python_keywords
    
    def should_exclude_identifier(self, node: Node) -> bool:
        # Python特定的标识符排除逻辑
        if node.parent and node.parent.type in ["attribute", "keyword_argument"]:
            return True
        return False