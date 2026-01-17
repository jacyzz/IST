from ist_utils import text
from transform.lang import get_lang


def match_augmented_assignment(root):
    """匹配增强赋值运算符 a += b"""
    res = []
    augmented_assignments = [
        "+=", "-=", "*=", "/=", "%=",
        "<<=", ">>=", "&=", "|=", "^=", "~="
    ]

    # Python特有的增强赋值运算符
    python_specific = ["//=", "**="]

    def check(u):
        lang = get_lang()

        if lang == "python":
            # Python的增强赋值有多种可能的AST结构
            if u.type in ["augmented_assignment", "expression_statement"]:
                if u.type == "expression_statement" and len(u.children) > 0:
                    # 检查是否是表达式语句中的增强赋值
                    child = u.children[0]
                    if child.type == "augmented_assignment" and len(child.children) >= 3:
                        op = text(child.children[1])
                        return op in augmented_assignments + python_specific
                elif u.type == "augmented_assignment" and len(u.children) >= 3:
                    op = text(u.children[1])
                    return op in augmented_assignments + python_specific
        else:
            # C/Java/C#逻辑
            if (u.type == "assignment_expression" and
                    len(u.children) >= 3 and
                    text(u.children[1]) in augmented_assignments):
                return True
        return False

    def match(u):
        if check(u):
            res.append(u)
        for v in u.children:
            match(v)

    match(root)
    return res


def match_non_augmented_assignment(root):
    """匹配可以转换为增强赋值的普通赋值 a = a + b"""
    res = []
    ops = ["+", "-", "*", "/", "%", "<<", ">>", "&", "|", "^", "~"]

    # Python特有运算符
    if get_lang() == "python":
        ops.extend(["//", "**"])  # 添加Python的整除和幂运算

    def check(u):
        lang = get_lang()

        if lang == "python":
            # Python的赋值语句结构分析
            main_var = None
            calc_expr = None

            if u.type == "expression_statement" and len(u.children) > 0:
                assign_node = u.children[0]
                if assign_node.type == "assignment" and len(assign_node.children) >= 3:
                    main_var = assign_node.children[0]
                    calc_expr = assign_node.children[2]
                else:
                    return False
            elif u.type == "assignment" and len(u.children) >= 3:
                main_var = u.children[0]
                calc_expr = u.children[2]
            else:
                return False

        else:
            # C/Java/C#逻辑
            if u.type != "assignment_expression" or len(u.children) < 3:
                return False
            main_var = u.children[0]
            calc_expr = u.children[2]

        if not main_var or not calc_expr:
            return False

        # 检查右侧是否是二元表达式
        calc_expr_type = "binary_expression" if lang != "python" else "binary_operator"
        if lang == "python":
            # Python可能使用不同的节点类型
            if calc_expr.type not in ["binary_operator", "binary_expression", "call"]:
                return False
        else:
            if calc_expr.type != "binary_expression" or len(calc_expr.children) < 3:
                return False

        # 获取运算符
        if lang == "python":
            # Python的二元运算符结构可能不同
            operator = None
            if len(calc_expr.children) >= 3:
                operator = text(calc_expr.children[1])
            elif len(calc_expr.children) >= 2:
                # 有些Python AST中运算符可能在不同位置
                for child in calc_expr.children:
                    if text(child) in ops:
                        operator = text(child)
                        break

            if not operator or operator not in ops:
                return False
        else:
            if len(calc_expr.children) < 3 or text(calc_expr.children[1]) not in ops:
                return False

        # 检查变量名是否匹配（a = a + b 模式）
        main_var_name = text(main_var)

        if lang == "python":
            # Python中检查左右操作数
            operands = [child for child in calc_expr.children if child.type == "identifier"]
            return any(text(operand) == main_var_name for operand in operands)
        else:
            return (text(calc_expr.children[0]) == main_var_name or
                    text(calc_expr.children[2]) == main_var_name)

    def match(u):
        if check(u):
            res.append(u)
        for v in u.children:
            match(v)

    match(root)
    return res


def convert_non_augmented_assignment(node):
    """将增强赋值转换为普通赋值 a += b -> a = a + b"""
    lang = get_lang()

    if lang == "python":
        # Python特定处理
        var = None
        op = None
        value = None

        if node.type == "expression_statement" and len(node.children) > 0:
            child = node.children[0]
            if child.type == "augmented_assignment" and len(child.children) >= 3:
                var = text(child.children[0])
                op = text(child.children[1])[:-1]  # 去掉=
                value = text(child.children[2])
        elif node.type == "augmented_assignment" and len(node.children) >= 3:
            var = text(node.children[0])
            op = text(node.children[1])[:-1]  # 去掉=
            value = text(node.children[2])
        else:
            return None

    else:
        # C/Java/C#逻辑
        if len(node.children) < 3:
            return None
        var = text(node.children[0])
        op = text(node.children[1])[:-1]  # 去掉=
        value = text(node.children[2])

    if not var or not op or not value:
        return None

    new_str = f"{var} = {var} {op} {value}"
    return [(node.end_byte, node.start_byte), (node.start_byte, new_str)]


def convert_augmented_assignment(node):
    """将普通赋值转换为增强赋值 a = a + b -> a += b"""
    lang = get_lang()

    main_var = None
    calc_expr = None

    if lang == "python":
        # Python特定处理
        if node.type == "expression_statement" and len(node.children) > 0:
            assign_node = node.children[0]
            if assign_node.type == "assignment" and len(assign_node.children) >= 3:
                main_var = assign_node.children[0]
                calc_expr = assign_node.children[2]
            else:
                return None
        elif node.type == "assignment" and len(node.children) >= 3:
            main_var = node.children[0]
            calc_expr = node.children[2]
        else:
            return None
    else:
        # C/Java/C#逻辑
        if len(node.children) < 3:
            return None
        main_var = node.children[0]
        calc_expr = node.children[2]

    if not main_var or not calc_expr:
        return None

    # 获取运算符和操作数
    if lang == "python":
        # Python的处理
        operator = None
        other_operand = None
        main_var_name = text(main_var)

        if len(calc_expr.children) >= 3:
            operator = text(calc_expr.children[1])
            # 确定哪个操作数是变量，哪个是其他值
            if text(calc_expr.children[0]) == main_var_name:
                other_operand = text(calc_expr.children[2])
            elif text(calc_expr.children[2]) == main_var_name:
                other_operand = text(calc_expr.children[0])
            else:
                return None
        else:
            return None
    else:
        # C/Java/C#的处理
        if len(calc_expr.children) < 3:
            return None

        operator = text(calc_expr.children[1])
        main_var_name = text(main_var)

        # 确定操作数的顺序
        if text(calc_expr.children[0]) == main_var_name:
            other_operand = text(calc_expr.children[2])
        elif text(calc_expr.children[2]) == main_var_name:
            other_operand = text(calc_expr.children[0])
        else:
            return None

    if not operator or not other_operand:
        return None

    new_str = f"{main_var_name} {operator}= {other_operand}"
    return [(node.end_byte, node.start_byte), (node.start_byte, new_str)]


def count_non_augmented_assignment(root):
    """计算普通赋值的数量"""
    nodes = match_non_augmented_assignment(root)
    return len(nodes)


def count_augmented_assignment(root):
    """计算增强赋值的数量"""
    nodes = match_augmented_assignment(root)
    return len(nodes)


# 添加辅助函数用于调试
def debug_assignment_structure(node):
    """调试函数：打印赋值语句的AST结构"""
    lang = get_lang()
    print(f"Language: {lang}")
    print(f"Node type: {node.type}")
    print(f"Node text: {text(node)}")
    print(f"Children count: {len(node.children)}")
    for i, child in enumerate(node.children):
        print(f"  Child {i}: type={child.type}, text='{text(child)}'")
