import sys, os
import logging
import json
import random
import argparse
import subprocess
from ist_utils import *
from tqdm import tqdm
from tree_sitter import Parser, Language
from seeTree import *

# 导入新的架构组件
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "optimization_test"))
from refactored_transfer import RefactoredIST
from transformation_interface import TransformationInterface, BaseTransformation
from language_adapters import get_language_adapter


class IST(RefactoredIST):
    """
    兼容原有接口的IST类，继承自新的RefactoredIST
    保持向后兼容性，同时使用新的架构
    """
    
    def __init__(self, language, expand=0, insert_position="suffix"):
        # 调用父类构造函数
        super().__init__(language, expand, insert_position)
        
        # 保持原有属性用于兼容性
        self.expand = expand
        
        # 保持原有的样式字典和描述
        self.style_group = {"0": ["0.1", "0.2", "0.3", "0.4", "0.5", "0.6"]}
        
        self.style_desc = {
            "0.1": ("aabb", "aaBb"),
            "0.2": ("aabb", "AaBb"),
            "0.3": ("aabb", "aa_bb"),
            "0.4": ("aabb", "typeAabb"),
            "0.5": ("aabb", "_aabb"),
            "0.6": ("aabb", "$aabb"),
            "1.1": ("if/for/while {...}", "if/for/while ..."),
            "1.2": ("if/for/while ...", "if/for/while {...}"),
            "21.1": ("recursive function", "iterative function"),
            "21.2": ("iterative function", "recursive function"),
        }
        
        self.style_dict = {
            "-3.1": ("tokensub2", "sh"),
            "-3.2": ("tokensub", "sh"),
            "-2.1": ("invichar", "ZWSP"),
            "-2.2": ("invichar", "ZWNJ"),
            "-2.3": ("invichar", "LRO"),
            "-2.4": ("invichar", "BKSP"),
            "-1.1": ("deadcode", "deadcode1"),
            "-1.2": ("deadcode", "deadcode2"),
            "-1.3": ("deadcode", "deadcode_cs"),
            "0.0": ("clean", "clean"),
            "0.1": ("identifier_name", "camel"),
            "0.2": ("identifier_name", "pascal"),
            "0.3": ("identifier_name", "snake"),
            "0.4": ("identifier_name", "hungarian"),
            "0.5": ("identifier_name", "init_underscore"),
            "0.6": ("identifier_name", "init_dollar"),
            "1.1": ("bracket", "del_bracket"),
            "1.2": ("bracket", "add_bracket"),
            "2.1": ("augmented_assignment", "non_augmented"),
            "2.2": ("augmented_assignment", "augmented"),
            "3.1": ("cmp", "smaller"),
            "3.2": ("cmp", "bigger"),
            "3.3": ("cmp", "equal"),
            "3.4": ("cmp", "not_equal"),
            "4.1": ("for_update", "left"),
            "4.2": ("for_update", "right"),
        }
        
        self.need_bracket = ["10", "11", "12", "17"]
        self.exclude = {"java": ["5", "6"], "c": [], "c_sharp": [], "python": []}
        
        # 设置语言和扩展参数
        from transform.lang import set_lang, set_expand
        set_lang(language)
        set_expand(expand)
    
    def get_style(self, style):
        """保持原有的get_style方法用于兼容性"""
        if style in self.style_dict:
            return self.style_dict[style]
        return None
    
    def transfer(self, styles=[], code="", insert_position=None):
        """
        重写transfer方法，保持原有接口但使用新架构
        """
        # 使用insert_position参数（如果提供）
        current_insert_position = insert_position or self.insert_position
        
        # 创建上下文
        from context_manager import TransformContext
        context = TransformContext(
            language=self.language,
            insert_position=current_insert_position,
            parser=self.parser
        )
        
        # 调用父类的transfer方法
        return super().transfer(styles, code, context)


# 向后兼容的工厂函数
def create_ist(language, expand=0, insert_position="suffix"):
    """创建IST实例的工厂函数"""
    return IST(language, expand, insert_position)


# 保持全局变量兼容性
if __name__ == "__main__":
    # 原有的命令行接口保持兼容
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", type=str, default="c")
    parser.add_argument("--expand", type=int, default=0)
    parser.add_argument("--insert_position", type=str, default="suffix")
    parser.add_argument("--style", type=str, default="-3.2")
    parser.add_argument("--code", type=str, default="")
    parser.add_argument("--file", type=str, default="")
    
    args = parser.parse_args()
    
    if args.file:
        with open(args.file, "r") as f:
            code = f.read()
    else:
        code = args.code
    
    ist = IST(args.language, args.expand, args.insert_position)
    result, success = ist.transfer([args.style], code)
    
    print(f"转换结果 (成功: {success}):")
    print(result)