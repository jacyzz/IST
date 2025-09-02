import sys, os
import logging

sys.path.insert(0, os.path.dirname(__file__))
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

# 使用新的语言适配器位置
from transform.language_adapters import get_language_adapter

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
            "4.3": ("for_update", "augment"),
            "4.4": ("for_update", "assignment"),
            "5.1": ("array_definition", "dyn_mem"),
            "5.2": ("array_definition", "static_mem"),
            "6.1": ("array_access", "pointer"),
            "6.2": ("array_access", "array"),
            "7.1": ("declare_lines", "split"),
            "7.2": ("declare_lines", "merge"),
            "8.1": ("declare_position", "first"),
            "8.2": ("declare_position", "temp"),
            "9.1": ("declare_assign", "split"),
            "9.2": ("declare_assign", "merge"),
            "10.0": ("for_format", "abc"),
            "10.1": ("for_format", "obc"),
            "10.2": ("for_format", "aoc"),
            "10.3": ("for_format", "abo"),
            "10.4": ("for_format", "aoo"),
            "10.5": ("for_format", "obo"),
            "10.6": ("for_format", "ooc"),
            "10.7": ("for_format", "ooo"),
            "11.1": ("for_while", "for"),
            "11.2": ("for_while", "while"),
            "11.3": ("for_while", "do_while"),
            "11.4": ("loop_infinite", "infinite_while"),
            "12.1": ("loop_infinite", "finite_for"),
            "12.2": ("loop_infinite", "infinite_for"),
            "12.3": ("loop_infinite", "finite_while"),
            "12.4": ("loop_infinite", "infinite_while"),
            "13.1": ("break_goto", "goto"),
            "13.2": ("break_goto", "break"),
            "14.1": ("if_exclamation", "not_exclamation"),
            "14.2": ("if_exclamation", "exclamation"),
            "15.1": ("if_return", "not_return"),
            "15.2": ("if_return", "return"),
            "16.1": ("if_switch", "switch"),
            "16.2": ("if_switch", "if"),
            "17.1": ("if_nested", "not_nested"),
            "17.2": ("if_nested", "nested"),
            "18.1": ("if_else", "not_else"),
            "18.2": ("if_else", "else"),
            "19.1": ("ternary", "to_ternary"),
            "19.2": ("ternary", "to_if"),
            "20.1": ("func_nested", "nested"),
            "20.2": ("func_nested", "not_nested"),
            "21.1": ("recursive_iterative", "to_iterative"),
            "21.2": ("recursive_iterative", "to_recursive"),
        }

        self.need_bracket = ["10", "11", "12", "17"]
        self.exclude = {"java": ["5", "6"], "c": [], "c_sharp": [], "python": []}

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

    def get_style(self, code="", styles=[]):
        """保持原有的get_style方法用于兼容性"""
        if not isinstance(styles, list):
            styles = [styles]
        res = {}
        if len(styles) == 0:
            styles = list(self.style_dict.keys())
        
        # 使用新的统计方法
        for style in styles:
            transformation = self.get_transformation(style)
            if transformation:
                AST = self.parser.parse(bytes(code, encoding="utf-8"))
                count = transformation.count(AST.root_node)
                res[style] = count
            else:
                res[style] = 0
        return res

    def tokenize(self, code):
        tree = self.parser.parse(bytes(code, "utf8"))
        root_node = tree.root_node
        tokens = []
        tokenize_help(root_node, tokens)
        return tokens

    def check_syntax(self, code):
        AST = self.parser.parse(bytes(code, encoding="utf-8"))
        return not AST.root_node.has_error

    def see_tree(self, code):
        try:
            AST = self.parser.parse(bytes(code, encoding="utf-8"))
            root_node = AST.root_node
            node_list, edge_list = ast_bfs(root=root_node)
            dot = draw_tree("AST", node_list, edge_list)
            # 注释掉以下行，跳过渲染
            # dot.render("AST", format="png")
        except Exception as e:
            logging.error(f"An error occurred while rendering the AST tree: {str(e)}")

if __name__ == "__main__":
    test_code_url = "test_code/test.c"
    with open(test_code_url, "r") as f:
        code = f.read()

    ist = IST("c", insert_position="suffix")
    style = "0.1"

    ist.see_tree(code)

    pcode, succ = ist.transfer(code=code, styles=[style])
    print(f"succ = {succ}")
    print(pcode)

    print(
        f"{ist.get_style(code=code, styles=[style])[style]} -> {ist.get_style(code=pcode, styles=[style])[style]}"
    )

    exit(0)