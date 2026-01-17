from ist_utils import text, print_children
from collections import defaultdict
from transform.lang import get_lang
import re

# 更新语言映射，添加Python支持
declaration_map = {
    "c": "declaration",
    "java": "local_variable_declaration",
    "c_sharp": "local_declaration_statement",
    "python": "assignment"  # Python使用assignment表示变量声明
}
block_map = {
    "c": "compound_statement",
    "java": "block",
    "c_sharp": "block",
    "python": "block"  # Python也使用block
}

# Python特有的循环模式识别
PYTHON_FOR_PATTERNS = {
    # 原有模式
    'range_simple': r'for\s+(\w+)\s+in\s+range\s*\(\s*(\d+)\s*\)',
    'range_start_end': r'for\s+(\w+)\s+in\s+range\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)',
    'range_step': r'for\s+(\w+)\s+in\s+range\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)',

    # 新增模式
    'list_iteration': r'for\s+(\w+)\s+in\s+(\w+)',  # for item in items
    'enumerate_simple': r'for\s+(\w+)\s*,\s*(\w+)\s+in\s+enumerate\s*\(\s*(\w+)\s*\)',
    # for i, item in enumerate(items)
    'enumerate_start': r'for\s+(\w+)\s*,\s*(\w+)\s+in\s+enumerate\s*\(\s*(\w+)\s*,\s*(\d+)\s*\)',
    # for i, item in enumerate(items, start)
    'dict_items': r'for\s+(\w+)\s*,\s*(\w+)\s+in\s+(\w+)\.items\s*\(\s*\)',  # for k, v in dict.items()
    'dict_keys': r'for\s+(\w+)\s+in\s+(\w+)\.keys\s*\(\s*\)',  # for k in dict.keys()
    'dict_values': r'for\s+(\w+)\s+in\s+(\w+)\.values\s*\(\s*\)',  # for v in dict.values()
    'zip_iteration': r'for\s+(\w+)\s*,\s*(\w+)\s+in\s+zip\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)',
    # for a, b in zip(list1, list2)
    'string_iteration': r'for\s+(\w+)\s+in\s+["\']([^"\']+)["\']',  # for char in "string"
}

PYTHON_WHILE_PATTERNS = {
    'simple_compare': r'while\s+(\w+)\s*([<>=!]+)\s*([^:]+)',  # while i < n
    'complex_condition': r'while\s+(.+?):'  # while complex_condition:
}


def get_for_info(node):
    """
    提取for循环的abc信息，支持Python语言
    """
    lang = get_lang()

    if lang == "python":
        # Python的for循环结构分析
        return analyze_python_for_structure(node)

    # 原有的C/Java/C#处理逻辑（修复版）
    i, abc = 0, [None, None, None, None]
    for child in node.children:
        if child.type in [";", ")", declaration_map.get(lang)]:
            if child.type == declaration_map.get(lang):
                abc[i] = child
            elif child.prev_sibling and child.prev_sibling.type not in ["(", ";"]:
                abc[i] = child.prev_sibling
            i += 1
        if child.prev_sibling and child.prev_sibling.type == ")" and i == 3:
            abc[3] = child
    return abc


def analyze_python_for_structure(node):
    """增强版Python for循环结构分析"""
    target = None
    iter_expr = None
    body = None

    # 获取完整的for循环文本
    for_text = text(node).strip()

    for child in node.children:
        if child.type == "identifier":
            if not target:  # 第一个identifier通常是循环变量
                target = child
        elif child.type in ["call", "attribute", "identifier", "string"]:
            if "in" in for_text:  # 确保是迭代表达式
                iter_expr = child
        elif child.type == "block":
            body = child

    return [target, iter_expr, None, body], for_text


def analyze_python_while_structure(node):
    """分析Python while循环的结构"""
    condition = None
    body = None

    for child in node.children:
        if child.type in ["comparison_operator", "binary_operator", "identifier"]:
            condition = child
        elif child.type == "block":
            body = child

    return condition, body


def get_indent(start_byte, code):
    indent = 0
    i = start_byte
    if len(code) <= i:
        return indent
    while i >= 0 and code[i] != '\n':
        if code[i] == ' ':
            indent += 1
        elif code[i] == '\t':
            indent += 4
        i -= 1
    return indent


def contain_id(node, contain):
    """Returns all variable names in the subtree of node node"""
    if node.child_by_field_name("index"):  # index in a[i] < 2: i
        contain.add(text(node.child_by_field_name("index")))
    if node.type == "identifier" and node.parent.type not in [
        "subscript_expression", "call_expression", "call"  # 添加Python的call
    ]:  # a in a < 2
        contain.add(text(node))
    if not node.children:
        return
    for n in node.children:
        contain_id(n, contain)


"""=========================match========================"""


def match_for(root):
    def check(node):
        return node.type == "for_statement"

    res = []

    def match(u):
        if check(u):
            res.append(u)
        for v in u.children:
            match(v)

    match(root)
    return res


def match_while(root):
    def check(node):
        return node.type == "while_statement"

    res = []

    def match(u):
        if check(u):
            res.append(u)
        for v in u.children:
            match(v)

    match(root)
    return res


def match_do_while(root):
    def check(node):
        # Python没有do-while，但保留接口
        if get_lang() == "python":
            return False
        return node.type == "do_statement" and "while" in text(node)

    res = []

    def match(u):
        if check(u):
            res.append(u)
        for v in u.children:
            match(v)

    match(root)
    return res


def match_loop(root):
    return match_for(root) + match_while(root) + match_do_while(root)


"""=========================replace========================"""


def convert_for(node, code):
    """将while/do-while转换为for循环"""
    lang = get_lang()

    if lang == "python":
        return convert_for_python(node, code)

    # C/Java/C#的处理逻辑（修复版）
    if node.type == "while_statement":
        return convert_while_to_for_clike(node, code, lang)
    elif node.type == "do_statement":
        return convert_do_while_to_for_clike(node, code, lang)

    return None


def convert_while_to_for_clike(node, code, lang):
    """C/Java/C#的while转for逻辑"""
    # 提取while条件
    condition_node = None
    body_node = None

    if lang == "c_sharp":
        if len(node.children) > 4:
            condition_node = node.children[4].children[1] if len(node.children[4].children) > 1 else None
    else:
        if len(node.children) > 1:
            condition_node = node.children[1].children[1] if len(node.children[1].children) > 1 else None

    if len(node.children) > 2:
        body_node = node.children[2]

    if not condition_node or not body_node:
        return None

    # 分析变量
    id_set = set()
    contain_id(condition_node, id_set)
    if len(id_set) == 0:
        return None

    loop_var = list(id_set)[0]

    # 查找初始化语句
    init_stmt = None
    prev = node.prev_sibling
    if prev and (
            prev.type == declaration_map.get(lang) or
            (prev.type == "expression_statement" and
             prev.children[0].type in ["update_expression", "assignment_expression"])
    ):
        prev_ids = set()
        contain_id(prev, prev_ids)
        if loop_var in prev_ids:
            init_stmt = prev

    # 查找更新语句
    update_stmt = None
    if body_node.type == block_map.get(lang):
        for stmt in body_node.children[1:-1]:  # 跳过大括号
            if stmt.type == "expression_statement":
                if stmt.children[0].type in ["update_expression", "assignment_expression"]:
                    stmt_ids = set()
                    contain_id(stmt.children[0], stmt_ids)
                    if loop_var in stmt_ids:
                        update_stmt = stmt
                        break

    # 构建for循环
    res = []

    # 删除while关键字和条件括号
    res.append((node.children[1].end_byte, node.children[0].start_byte))

    # 处理初始化语句
    if init_stmt:
        res.append(
            (init_stmt.end_byte, init_stmt.prev_sibling.end_byte if init_stmt.prev_sibling else init_stmt.start_byte))

    # 处理更新语句
    if update_stmt:
        res.append((update_stmt.end_byte,
                    update_stmt.prev_sibling.end_byte if update_stmt.prev_sibling else update_stmt.start_byte))

    # 构建for语句
    init_text = text(init_stmt) if init_stmt else ""
    condition_text = text(condition_node)
    update_text = text(update_stmt).replace(';', '') if update_stmt else ""

    for_str = f"for({init_text}{'; ' if ';' not in init_text and init_text else ' '}{condition_text}; {update_text})"
    res.append((node.start_byte, for_str))

    return res


def convert_do_while_to_for_clike(node, code, lang):
    """C/Java/C#的do-while转for逻辑"""
    condition_node = None
    body_node = None

    # 找到condition和body
    for child in node.children:
        if child.type == "parenthesized_expression":
            condition_node = child.children[1] if len(child.children) > 1 else None
        elif child.type == block_map.get(lang):
            body_node = child

    if not condition_node or not body_node:
        return None

    # 分析变量
    id_set = set()
    contain_id(condition_node, id_set)
    if len(id_set) == 0:
        return None

    loop_var = list(id_set)[0]

    # 查找初始化语句（在do-while之前）
    init_stmt = None
    prev = node.prev_sibling
    if prev and (
            prev.type == declaration_map.get(lang) or
            (prev.type == "expression_statement" and
             prev.children[0].type in ["update_expression", "assignment_expression"])
    ):
        prev_ids = set()
        contain_id(prev, prev_ids)
        if loop_var in prev_ids:
            init_stmt = prev

    # 查找更新语句（在body中）
    update_stmt = None
    if body_node.type == block_map.get(lang):
        for stmt in body_node.children[1:-1]:  # 跳过大括号
            if stmt.type == "expression_statement":
                if stmt.children[0].type in ["update_expression", "assignment_expression"]:
                    stmt_ids = set()
                    contain_id(stmt.children[0], stmt_ids)
                    if loop_var in stmt_ids:
                        update_stmt = stmt
                        break

    # 构建for循环
    res = []

    # 删除do关键字和while部分
    res.append((node.children[0].end_byte, node.children[0].start_byte))  # 删除do

    # 查找while部分并删除
    for i, child in enumerate(node.children):
        if child.type == "while" or "while" in text(child):
            res.append((node.children[-1].end_byte, child.start_byte))  # 删除while部分
            break

    # 处理初始化语句
    if init_stmt:
        res.append(
            (init_stmt.end_byte, init_stmt.prev_sibling.end_byte if init_stmt.prev_sibling else init_stmt.start_byte))

    # 处理更新语句
    if update_stmt:
        res.append((update_stmt.end_byte,
                    update_stmt.prev_sibling.end_byte if update_stmt.prev_sibling else update_stmt.start_byte))

    # 构建for语句
    init_text = text(init_stmt) if init_stmt else ""
    condition_text = text(condition_node)
    update_text = text(update_stmt).replace(';', '') if update_stmt else ""

    for_str = f"for({init_text}{'; ' if ';' not in init_text and init_text else ' '}{condition_text}; {update_text})"
    res.append((node.start_byte, for_str))

    return res


def convert_for_python(node, code):
    """增强版Python for转while逻辑"""
    if node.type != "for_statement":
        return None

    for_info, for_text = analyze_python_for_structure(node)
    target, iter_expr, _, body = for_info

    if not target or not iter_expr or not body:
        return None

    target_name = text(target)
    iter_text = text(iter_expr)
    indent = get_indent(node.start_byte, code)

    # 尝试匹配各种模式
    for pattern_name, pattern in PYTHON_FOR_PATTERNS.items():
        match = re.match(pattern, for_text.replace('\n', ' ').strip())
        if match:
            conversion = convert_pattern_to_while(pattern_name, match, target_name, iter_text, indent, body, node)
            if conversion:
                return conversion

    # 通用列表迭代转换
    return convert_generic_iteration(node, code, target_name, iter_text, indent, body)


def convert_pattern_to_while(pattern_name, match, target_name, iter_text, indent, body, node):
    """根据模式转换为while循环"""

    if pattern_name == 'range_simple':
        limit = match.group(2)
        init_stmt = f"{target_name} = 0"
        while_stmt = f"while {target_name} < {limit}:"
        increment = f"{target_name} += 1"

    elif pattern_name == 'range_start_end':
        start, end = match.group(2), match.group(3)
        init_stmt = f"{target_name} = {start}"
        while_stmt = f"while {target_name} < {end}:"
        increment = f"{target_name} += 1"

    elif pattern_name == 'range_step':
        start, end, step = match.group(2), match.group(3), match.group(4)
        init_stmt = f"{target_name} = {start}"
        if step.startswith('-'):
            while_stmt = f"while {target_name} > {end}:"
        else:
            while_stmt = f"while {target_name} < {end}:"
        increment = f"{target_name} += {step}"

    elif pattern_name == 'list_iteration':
        var, lst = match.group(1), match.group(2)
        init_stmt = f"{var}_index = 0\n{' ' * indent}{lst}_list = {lst}"
        while_stmt = f"while {var}_index < len({lst}_list):"
        body_prefix = f"{var} = {lst}_list[{var}_index]"
        increment = f"{var}_index += 1"

    elif pattern_name == 'enumerate_simple':
        idx_var, item_var, lst = match.group(1), match.group(2), match.group(3)
        init_stmt = f"{idx_var} = 0\n{' ' * indent}{lst}_list = {lst}"
        while_stmt = f"while {idx_var} < len({lst}_list):"
        body_prefix = f"{item_var} = {lst}_list[{idx_var}]"
        increment = f"{idx_var} += 1"

    elif pattern_name == 'enumerate_start':
        idx_var, item_var, lst, start = match.group(1), match.group(2), match.group(3), match.group(4)
        init_stmt = f"{idx_var} = {start}\n{' ' * indent}{lst}_list = {lst}"
        while_stmt = f"while {idx_var} < len({lst}_list) + {start}:"
        body_prefix = f"{item_var} = {lst}_list[{idx_var} - {start}]"
        increment = f"{idx_var} += 1"

    elif pattern_name == 'dict_items':
        key_var, val_var, dict_name = match.group(1), match.group(2), match.group(3)
        init_stmt = f"{dict_name}_keys = list({dict_name}.keys())\n{' ' * indent}{key_var}_index = 0"
        while_stmt = f"while {key_var}_index < len({dict_name}_keys):"
        body_prefix = f"{key_var} = {dict_name}_keys[{key_var}_index]\n{' ' * (indent + 4)}{val_var} = {dict_name}[{key_var}]"
        increment = f"{key_var}_index += 1"

    elif pattern_name == 'dict_keys':
        key_var, dict_name = match.group(1), match.group(2)
        init_stmt = f"{dict_name}_keys = list({dict_name}.keys())\n{' ' * indent}{key_var}_index = 0"
        while_stmt = f"while {key_var}_index < len({dict_name}_keys):"
        body_prefix = f"{key_var} = {dict_name}_keys[{key_var}_index]"
        increment = f"{key_var}_index += 1"

    elif pattern_name == 'string_iteration':
        char_var, string_val = match.group(1), match.group(2)
        init_stmt = f"{char_var}_index = 0\n{' ' * indent}{char_var}_string = \"{string_val}\""
        while_stmt = f"while {char_var}_index < len({char_var}_string):"
        body_prefix = f"{char_var} = {char_var}_string[{char_var}_index]"
        increment = f"{char_var}_index += 1"

    else:
        return None

    # 构建完整的while循环
    body_text = text(body)
    body_lines = body_text.strip().split('\n')
    if body_lines and body_lines[0].strip() == ':':
        body_lines = body_lines[1:]

    # 添加body前缀（如果有）
    if 'body_prefix' in locals():
        new_body_lines = [f"{' ' * (indent + 4)}{body_prefix}"] + body_lines
    else:
        new_body_lines = body_lines

    # 添加increment到body末尾
    new_body_lines.append(f"{' ' * (indent + 4)}{increment}")
    new_body = ':\n' + '\n'.join(new_body_lines)

    return [
        (node.end_byte, node.start_byte),
        (node.start_byte, f"{' ' * indent}{init_stmt}\n{' ' * indent}{while_stmt}{new_body}")
    ]


def convert_generic_iteration(node, code, target_name, iter_text, indent, body):
    """通用迭代转换为while循环"""
    # 为复杂迭代创建通用转换
    init_stmt = f"{target_name}_list = list({iter_text})\n{' ' * indent}{target_name}_index = 0"
    while_stmt = f"while {target_name}_index < len({target_name}_list):"
    body_prefix = f"{target_name} = {target_name}_list[{target_name}_index]"
    increment = f"{target_name}_index += 1"

    body_text = text(body)
    body_lines = body_text.strip().split('\n')
    if body_lines and body_lines[0].strip() == ':':
        body_lines = body_lines[1:]

    new_body_lines = [f"{' ' * (indent + 4)}{body_prefix}"] + body_lines + [f"{' ' * (indent + 4)}{increment}"]
    new_body = ':\n' + '\n'.join(new_body_lines)

    return [
        (node.end_byte, node.start_byte),
        (node.start_byte, f"{' ' * indent}{init_stmt}\n{' ' * indent}{while_stmt}{new_body}")
    ]


def convert_simple_while_to_for(node, code, condition_text, body_text, indent):
    """原有的简单while转for逻辑"""
    # 保持原有的简单转换逻辑
    match = re.match(r'(\w+)\s*<\s*(.+)', condition_text)
    if match:
        var = match.group(1)
        limit = match.group(2).strip()

        prev = node.prev_sibling
        if prev and prev.type == "expression_statement":
            prev_text = text(prev).strip()
            if f"{var} = 0" in prev_text:
                for_str = f"for {var} in range({limit}):"
                body = analyze_python_while_structure(node)[1]

                return [
                    (prev.end_byte, prev.start_byte),
                    (body.start_byte, node.start_byte),
                    (node.start_byte, f"{' ' * indent}{for_str}")
                ]

    return None


def convert_while(node, code):
    """将for循环转换为while循环"""
    lang = get_lang()

    if lang == "python":
        return convert_while_python(node, code)

    # C/Java/C#的处理逻辑
    return convert_for_to_while_clike(node, code, lang)


def convert_for_to_while_clike(node, code, lang):
    """C/Java/C#的for转while逻辑"""
    if node.type != "for_statement":
        return None

    abc = get_for_info(node)
    if not abc:
        return None

    res = []
    body_node = None

    # 找到body节点
    for child in node.children:
        if child.type == block_map.get(lang):
            body_node = child
            break

    if not body_node:
        return None

    # 删除for(a;b;c)部分
    res.append((body_node.start_byte - 1, node.start_byte))

    indent = get_indent(node.start_byte, code)

    # 添加初始化语句
    if abc[0] is not None:
        if abc[0].type != declaration_map.get(lang):
            res.append((node.start_byte, text(abc[0]) + f';\n{indent * " "}'))
        else:
            res.append((node.start_byte, text(abc[0]) + f'\n{indent * " "}'))

    # 在body末尾添加更新语句
    if abc[2] is not None:
        if body_node.type == block_map.get(lang):
            last_stmt = body_node.children[-2]  # 最后一个语句（不包括}）
        else:
            last_stmt = body_node

        stmt_indent = get_indent(last_stmt.start_byte, code)
        res.append((last_stmt.end_byte, f"\n{stmt_indent * ' '}{text(abc[2])};"))

    # 替换为while语句
    while_str = f"while({text(abc[1]) if abc[1] else 'true'})"
    res.append((node.children[0].start_byte, while_str))

    return res


def clean_while_body_for_list_iteration(body_text, index_var, list_var, item_var):
    """清理while循环体，移除索引相关代码"""
    lines = body_text.split('\n')
    cleaned_lines = []

    for line in lines:
        # 跳过索引赋值和递增
        if (f"{item_var} = {list_var}[{index_var}]" in line or
                f"{index_var} += 1" in line or
                f"{index_var} = {index_var} + 1" in line):
            continue
        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def clean_while_body_for_dict_iteration(body_text, index_var, dict_var, key_var):
    """清理while循环体，移除字典索引相关代码 - 修正：添加缺失的函数"""
    lines = body_text.split('\n')
    cleaned_lines = []

    for line in lines:
        # 跳过键值赋值和递增
        if (f"{key_var} = {dict_var}_keys[{index_var}]" in line or
                f"{index_var} += 1" in line or
                f"= {dict_var}[{key_var}]" in line):
            continue
        cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def convert_while_python(node, code):
    """增强版Python while转for逻辑"""
    if node.type != "while_statement":
        return None

    condition, body = analyze_python_while_structure(node)
    if not condition or not body:
        return None

    condition_text = text(condition).strip()
    body_text = text(body)
    indent = get_indent(node.start_byte, code)

    # 检测各种while模式并转换为for

    # 模式1: 简单索引循环 while i < len(lst):
    match = re.match(r'(\w+)\s*<\s*len\s*\(\s*(\w+)\s*\)', condition_text)
    if match:
        index_var, list_var = match.group(1), match.group(2)

        # 查找初始化和body中的使用
        prev = node.prev_sibling
        if prev and f"{index_var} = 0" in text(prev):
            # 检查body中是否有list访问
            if f"{list_var}[{index_var}]" in body_text:
                # 提取访问的变量名
                access_match = re.search(rf'(\w+)\s*=\s*{list_var}\[{index_var}\]', body_text)
                if access_match:
                    item_var = access_match.group(1)
                    for_str = f"for {item_var} in {list_var}:"

                    # 清理body，移除索引访问和递增
                    clean_body = clean_while_body_for_list_iteration(body_text, index_var, list_var, item_var)

                    return [
                        (prev.end_byte, prev.start_byte),  # 删除初始化
                        (body.start_byte, node.start_byte),  # 删除while部分
                        (node.start_byte, f"{' ' * indent}{for_str}{clean_body}")
                    ]

    # 模式2: 字典键迭代 while i < len(dict_keys):
    match = re.match(r'(\w+)\s*<\s*len\s*\(\s*(\w+)_keys\s*\)', condition_text)
    if match:
        index_var, dict_var = match.group(1), match.group(2)

        if f"{dict_var}_keys = list({dict_var}.keys())" in code:
            # 检查是否有键值访问
            if f"{dict_var}_keys[{index_var}]" in body_text:
                key_access_match = re.search(rf'(\w+)\s*=\s*{dict_var}_keys\[{index_var}\]', body_text)
                if key_access_match:
                    key_var = key_access_match.group(1)

                    # 检查是否还有值访问
                    val_access_match = re.search(rf'(\w+)\s*=\s*{dict_var}\[{key_var}\]', body_text)
                    if val_access_match:
                        val_var = val_access_match.group(1)
                        for_str = f"for {key_var}, {val_var} in {dict_var}.items():"
                    else:
                        for_str = f"for {key_var} in {dict_var}.keys():"

                    clean_body = clean_while_body_for_dict_iteration(body_text, index_var, dict_var, key_var)

                    return [
                        (body.start_byte, node.start_byte),
                        (node.start_byte, f"{' ' * indent}{for_str}{clean_body}")
                    ]

    # 原有的简单range转换逻辑
    return convert_simple_while_to_for(node, code, condition_text, body_text, indent)


def detect_list_comprehensions(root):
    """检测列表推导式"""
    comprehensions = []

    def find_comprehensions(node):
        if node.type == "list_comprehension":
            comprehensions.append(node)
        for child in node.children:
            find_comprehensions(child)

    find_comprehensions(root)
    return comprehensions


def convert_list_comprehension_to_loop(node, code):
    """将列表推导式转换为普通循环"""
    comp_text = text(node)

    # 简单的列表推导式模式 [expr for var in iterable]
    match = re.match(r'\[\s*(.+?)\s+for\s+(\w+)\s+in\s+(.+?)\s*\]', comp_text)
    if match:
        expr, var, iterable = match.group(1), match.group(2), match.group(3)

        indent = get_indent(node.start_byte, code)
        result_var = f"{var}_result"

        loop_code = f"""{result_var} = []
{' ' * indent}for {var} in {iterable}:
{' ' * (indent + 4)}{result_var}.append({expr})"""

        return [(node.end_byte, node.start_byte), (node.start_byte, loop_code)]

    return None


def convert_do_while(node, code):
    """do-while转换(Python不支持)"""
    if get_lang() == "python":
        return None  # Python没有do-while

    # C/Java/C#的do-while处理
    return convert_for_to_do_while_clike(node, code, get_lang())


def convert_for_to_do_while_clike(node, code, lang):
    """C/Java/C#的for转do-while逻辑"""
    if node.type != "for_statement":
        return None

    abc = get_for_info(node)
    if not abc:
        return None

    res = []
    body_node = None

    for child in node.children:
        if child.type == block_map.get(lang):
            body_node = child
            break

    if not body_node:
        return None

    indent = get_indent(node.start_byte, code)

    # 添加初始化语句
    if abc[0] is not None:
        if abc[0].type != declaration_map.get(lang):
            res.append((node.start_byte, text(abc[0]) + f';\n{indent * " "}'))
        else:
            res.append((node.start_byte, text(abc[0]) + f'\n{indent * " "}'))

    # 在body末尾添加更新语句
    if abc[2] is not None:
        if body_node.type == block_map.get(lang):
            last_stmt = body_node.children[-2]
        else:
            last_stmt = body_node

        stmt_indent = get_indent(last_stmt.start_byte, code)
        res.append((last_stmt.end_byte, f"\n{stmt_indent * ' '}{text(abc[2])};"))

    # 替换为do-while
    res.append((body_node.start_byte, node.start_byte))
    res.append((node.children[0].start_byte, "do"))
    res.append((node.end_byte, f"while({text(abc[1]) if abc[1] else 'true'});"))

    return res


"""=========================count========================"""


def count_for(root):
    nodes = match_for(root)
    return len(nodes)


def count_while(root):
    nodes = match_while(root)
    return len(nodes)


def count_do_while(root):
    nodes = match_do_while(root)
    return len(nodes)


def count_total_loops(root):
    """统计所有类型的循环"""
    return {
        'for_loops': count_for(root),
        'while_loops': count_while(root),
        'list_comprehensions': len(detect_list_comprehensions(root)),
        'total': count_for(root) + count_while(root) + len(detect_list_comprehensions(root))
    }
