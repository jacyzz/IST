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
    verbose: int = 0,
    log_to_file: bool = True
) -> List[dict]:
    """
    批量对数据集中的代码片段进行等义转换

    Args:
        dataset_file: 输入JSONL数据集路径
        code_field: 代码字段名（如 'func' 或 'code'）
        styles: 转换风格列表（如 ['11.1', '9.1']）
        language: 编程语言（如 'c', 'java', 'python', 'c_sharp'）
        output_path: 输出文件路径（可选，默认为 dataset/result/<base_name>_<styles>.<format>）
        output_format: 输出格式（'jsonl' 或 'csv'）
        fields: 输出保留字段（如 ['func', 'target', 'idx']）
        verbose: 处理前n个样本并记录详细日志（0表示处理所有样本，无详细日志）
        log_to_file: 是否将日志保存到文件

    Returns:
        List of transformed code snippets
    """
    # Generate log file name matching output file
    base_dir = os.path.join(os.path.dirname(__file__), "dataset", "result")
    log_dir = os.path.join(os.path.dirname(__file__), "dataset", "log")
    os.makedirs(log_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(dataset_file))[0]
    style_str = "_".join(styles)
    log_file = os.path.join(log_dir, f"{base_name}_{style_str}.log")
    
    # Set up logging (file only unless verbose > 0)
    log_handlers = [logging.FileHandler(log_file, encoding="utf-8")] if log_to_file else []
    logging.basicConfig(
        level=logging.DEBUG if verbose > 0 else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=log_handlers
    )
    logger = logging.getLogger("BatchEquivalentTransform")

    # Initialize IST
    logger.info(f"Reading dataset from {dataset_file}")
    ist = IST(language)
    allowed_styles = list(ist.style_dict.keys())
    for style in styles:
        if style not in allowed_styles:
            logger.error(f"Invalid style {style}. Supported styles: {allowed_styles}")
            raise ValueError(f"Style {style} is not supported. Supported styles: {allowed_styles}")

    # Read dataset
    code_snippets = []
    with open(dataset_file, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if verbose > 0 and idx >= verbose:
                logger.info(f"Verbose mode: Stopping after {verbose} samples")
                break
            try:
                data = json.loads(line.strip())
                if code_field in data and data[code_field].strip():
                    code_snippets.append(data)
            except Exception as e:
                logger.warning(f"Skipping invalid line {idx}: {e}")

    logger.info(f"Loaded {len(code_snippets)} valid code snippets")

    # Process transformations
    transformed_snippets = []
    style_success_count = {style: 0 for style in styles}
    debug_results = []

    for idx, item in enumerate(tqdm(code_snippets, desc="Transforming", file=sys.stdout)):
        code = item[code_field]
        new_code = code
        success = False
        style_result = {}
        for style in styles:
            try:
                style_count = ist.get_style(code=new_code, styles=[style]).get(style, 0)
                new_code, style_success = ist.transfer(styles=[style], code=new_code)
                if style_success:
                    style_success_count[style] += 1
                    success = True
                style_result[style] = {"success": style_success, "style_count": style_count}
            except Exception as e:
                logger.error(f"Sample {idx} style {style} failed: {e}")
                style_result[style] = {"success": False, "error": str(e)}
        new_item = item.copy()
        new_item[code_field] = new_code
        if fields:
            new_item = {k: new_item[k] for k in fields if k in new_item}
        transformed_snippets.append(new_item)
        if verbose > 0:
            debug_results.append({
                "idx": idx,
                "original": code,
                "transformed": new_code,
                "style_result": style_result
            })

    # Generate output path if not specified
    if output_path is None:
        os.makedirs(base_dir, exist_ok=True)
        output_path = os.path.join(base_dir, f"{base_name}_{style_str}.{output_format}")
    else:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Save results
    logger.info(f"Saving results to {output_path}")
    if output_format == "jsonl":
        with open(output_path, "w", encoding="utf-8") as f:
            for item in transformed_snippets:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
    elif output_format == "csv":
        pd.DataFrame(transformed_snippets).to_csv(output_path, index=False)

    # Log summary
    logger.info("Transformation Summary")
    logger.info(f"Input dataset: {dataset_file}")
    logger.info(f"Styles applied: {', '.join(styles)}")
    logger.info(f"Total snippets processed: {len(code_snippets)}")
    logger.info(f"Output saved to: {output_path}")
    logger.info(f"Log file: {log_file}")
    for style in styles:
        logger.info(f"Style {style}: {style_success_count[style]} successful transformations")

    # Verbose mode: Log detailed per-sample results
    if verbose > 0:
        logger.debug("Verbose Mode: Detailed Transformation Results")
        for result in debug_results:
            logger.debug(f"Sample {result['idx']}:")
            logger.debug(f"  Original: {result['original'][:60]}...")
            logger.debug(f"  Transformed: {result['transformed'][:60]}...")
            logger.debug(f"  Style Results: {json.dumps(result['style_result'], indent=2)}")

    # Command-line output (minimal)
    print(f"Transformation completed for {dataset_file}")
    print(f"Styles applied: {', '.join(styles)}")
    print(f"Results saved to: {output_path}")
    print(f"Total snippets processed: {len(code_snippets)}")
    for style in styles:
        print(f"Style {style}: {style_success_count[style]} successful transformations")

    return transformed_snippets

def run_command_line():
    parser = argparse.ArgumentParser(
        description="Batch code equivalent transformation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python BatchSample_Generator.py --dpath test.jsonl --trans 11.1 9.1 --code_field func --lang c --output_format jsonl
  python BatchSample_Generator.py --dpath test.jsonl --trans -3.1 --code_field func --lang c --output_format jsonl --verbose 50
"""
    )
    parser.add_argument("--dpath", type=str, required=True, help="Input JSONL dataset path")
    parser.add_argument("--trans", type=str, nargs="+", required=True, help="Transformation styles (e.g., '11.1 9.1')")
    parser.add_argument("--opath", type=str, help="Output file path (optional, auto-generated if not specified)")
    parser.add_argument("--code_field", type=str, default="func", help="Code field name (e.g., 'func' or 'code')")
    parser.add_argument("--fields", type=str, nargs="+", help="Fields to retain in output (e.g., 'func target idx')")
    parser.add_argument("--lang", type=str, default="c", choices=["c", "java", "python", "c_sharp"], help="Programming language")
    parser.add_argument("--output_format", type=str, default="jsonl", choices=["jsonl", "csv"], help="Output format")
    parser.add_argument("--verbose", type=int, default=0, help="Process first n samples and log detailed results (0 for all samples, no detailed logs)")
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
        log_to_file=True
    )

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_command_line()