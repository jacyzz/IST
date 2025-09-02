"""
语言适配器模块
提供多语言支持的抽象层
"""

from .base_adapter import LanguageAdapter
from .python_adapter import PythonAdapter
from .java_adapter import JavaAdapter
from .c_adapter import CAdapter


def get_language_adapter(language: str) -> LanguageAdapter:
    """获取语言适配器工厂函数"""
    adapters = {
        "c": CAdapter,
        "python": PythonAdapter,
        "java": JavaAdapter,
        "c_sharp": JavaAdapter  # 暂时使用Java适配器
    }
    
    if language in adapters:
        return adapters[language]()
    else:
        raise ValueError(f"Unsupported language: {language}")