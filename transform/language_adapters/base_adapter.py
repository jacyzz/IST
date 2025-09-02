from abc import ABC, abstractmethod
from typing import List, Set
from tree_sitter import Node
from ist_utils import text


class LanguageAdapter(ABC):
    """语言抽象层适配器接口"""
    
    @abstractmethod
    def get_language_code(self) -> str:
        """获取语言代码"""
        pass
    
    @abstractmethod
    def get_identifier_nodes(self, root: Node) -> List[Node]:
        """获取所有标识符节点"""
        pass
    
    @abstractmethod
    def get_function_nodes(self, root: Node) -> List[Node]:
        """获取所有函数节点"""
        pass
    
    @abstractmethod
    def is_keyword(self, identifier: str) -> bool:
        """判断是否为关键字"""
        pass
    
    @abstractmethod
    def should_exclude_identifier(self, node: Node) -> bool:
        """判断是否应该排除该标识符"""
        pass
    
    def get_identifier_text(self, node: Node) -> str:
        """获取标识符文本"""
        return text(node)