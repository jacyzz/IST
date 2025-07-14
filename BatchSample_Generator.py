import os
import sys
import argparse
import json
import logging
import pandas as pd
from typing import List
from tqdm import tqdm
from datetime import datetime
from transfer import IST

def batch_equivalent_transform(
    dataset_file: str,
    code_field: str,
    styles: List[str],
    language: str = "c",
    output_path: str = None,
    output_format: str = "jsonl",
    fields: List[str] = None,
    verbose: bool = False,
    debug: bool = False,
    log_to_file: bool = True
) -> List[dict]:
    """
    批量对数据集中的代码片段进行等义转换
    """
    # 日志配置，日志名为时间
    log_dir = os.path.join(os.path.dirname(__file__), "dataset", "log")
    os.makedirs(log_dir, exist_ok=True)
    log_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"transform_{log_time}.log")
    log_handlers = [logging.FileHandler(log_file, encoding="utf-8")]
    if verbose or debug:
        log_handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO if verbose or debug else logging.WARNING,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=log_handlers
    )
    logger = logging.getLogger("BatchEquivalentTransform")

    ist = IST(language)
    # 只允许选择 transfer.py 中定义的转换风格
    allowed_styles = list(ist.style_dict.keys())
    for style in styles:
        if style not in allowed_styles:
            logger.error(f"转换风格 {style} 不在 transfer.py 支持的风格列表中！")
            raise ValueError(f"转换风格 {style} 不支持。可选风格: {allowed_styles}")

    code_snippets = []
    with open(dataset_file, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if debug and idx >= 50:
                break
            try:
                data = json.loads(line.strip())
                if code_field in data and data[code_field].strip():
                    code_snippets.append(data)
            except Exception as e:
                logger.warning(f"跳过无效行: {e}")

    transformed_snippets = []
    style_success_count = {style: 0 for style in styles}
    debug_results = []

    for idx, item in enumerate(tqdm(code_snippets, desc="批量等义转换")):
        code = item[code_field]
        new_code = code
        success = False
        style_result = {}
        for style in styles:
            try:
                style_count = ist.get_style(code=new_code, styles=[style]).get(style, 0)
                if style_count > 0:
                    new_code, success = ist.transfer(styles=[style], code=new_code)
                    if success:
                        style_success_count[style] += 1
                style_result[style] = {"success": success, "style_count": style_count}
            except Exception as e:
                logger.error(f"样本 {idx} 风格 {style} 转换失败: {e}")
                style_result[style] = {"success": False, "error": str(e)}
        new_item = item.copy()
        new_item[code_field] = new_code
        if fields:
            new_item = {k: new_item[k] for k in fields if k in new_item}
        transformed_snippets.append(new_item)
        if debug:
            debug_results.append({
                "idx": idx,
                "original": code,
                "transformed": new_code,
                "style_result": style_result
            })

    # 自动生成 output_path（如果未指定），存放在 IST/dataset/result 路径下
    if output_path is None:
        base_dir = os.path.join(os.path.dirname(__file__), "dataset", "result")
        os.makedirs(base_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(dataset_file))[0]
        style_str = "_".join(styles)
        output_path = os.path.join(base_dir, f"{base_name}_{style_str}.{output_format}")
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 结果保存
    if output_format == "jsonl":
        with open(output_path, "w", encoding="utf-8") as f:
            for item in transformed_snippets:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
    elif output_format == "csv":
        pd.DataFrame(transformed_snippets).to_csv(output_path, index=False)

    # 日志输出转换统计
    logger.info(f"转换完成，结果保存至: {output_path}")
    logger.info(f"日志保存至: {log_file}")
    for style in styles:
        logger.info(f"风格 {style} 转换成功代码段数量: {style_success_count[style]} / {len(code_snippets)}")

    # debug模式下，详细记录每一份数据的转换结果
    if debug:
        logger.info("Debug模式：只处理前50份数据，详细转换结果如下：")
        for result in debug_results:
            logger.info(
                f"样本{result['idx']} | 原始: {result['original'][:60]}... | 转换后: {result['transformed'][:60]}... | 风格结果: {result['style_result']}"
            )
        logger.info(f"Debug模式总体转换统计: {style_success_count}")

    return transformed_snippets

def run_command_line():
    parser = argparse.ArgumentParser(
        description="批量代码等义转换工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python BatchSample_Generator.py --dpath test.json --trans 11.1 9.1 --code_field func --lang c --output_format jsonl --verbose
  python BatchSample_Generator.py --dpath test.json --trans 11.1 --code_field func --lang c --output_format jsonl --debug
"""
    )
    parser.add_argument("--dpath", type=str, required=True, help="输入JSONL数据集路径")
    parser.add_argument("--trans", type=str, nargs="+", required=True, help="转换风格列表 (如 '11.1 9.1')")
    parser.add_argument("--opath", type=str, help="输出文件路径（可选，默认自动生成）")
    parser.add_argument("--code_field", type=str, default="func", help="代码字段名 (如 'func' 或 'code')")
    parser.add_argument("--fields", type=str, nargs="+", help="输出保留字段 (如 'func target idx')")
    parser.add_argument("--lang", type=str, default="c", choices=["c", "java", "python", "c_sharp"], help="语言类型")
    parser.add_argument("--output_format", type=str, default="jsonl", choices=["jsonl", "csv"], help="输出格式")
    parser.add_argument("--verbose", action="store_true", help="命令行显示日志")
    parser.add_argument("--debug", action="store_true", help="Debug模式（只处理前50份数据并详细记录日志）")
    args = parser.parse_args()

    batch_equivalent_transform(
        dataset_file=args.dpath,
        code_field=args.code_field,
        styles=args.trans,
        language=args.lang,
        output_path=args.opath,
        output_format=args.output_format,
        fields=args.fields,
        verbose=args.verbose,
        debug=args.debug,
        log_to_file=True
    )

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_command_line()