import os
import sys
import argparse
import json
import logging
import gzip
import pandas as pd
from typing import List
from tqdm import tqdm
from transfer import IST

def batch_equivalent_transform(
    dataset_file: str,
    code_fields: List[str],
    styles: List[str],
    language: str = "python",
    output_path: str = None,
    output_format: str = "jsonl",
    fields: List[str] = None,
    verbose: int = 0,
    log_to_file: bool = True
) -> List[dict]:
    """
    批量对数据集中的多个代码字段进行等义转换

    Args:
        dataset_file: 输入JSONL或JSONL.GZ数据集路径
        code_fields: 代码字段名列表（如 ['func', 'code']）
        styles: 转换风格列表（如 ['subword_sh']）
        language: 编程语言（如 'python', 'c', 'java', 'c_sharp'）
        output_path: 输出文件路径或目录（可选，默认为 dataset/result/<base_name>_<styles>.<format>）
        output_format: 输出格式（'jsonl' 或 'csv'）
        fields: 输出保留字段（如 ['func', 'target', 'idx']）
        verbose: 处理前n个样本并记录详细日志（0表示处理所有样本，无详细日志）
        log_to_file: 是否将日志保存到文件

    Returns:
        List of transformed code snippets
    """
    # Generate output path
    base_name = os.path.splitext(os.path.basename(dataset_file))[0]
    if base_name.endswith('.jsonl'):
        base_name = base_name[:-6]  # Remove .jsonl extension if present
    style_str = "_".join(styles)
    output_filename = f"{base_name}_{style_str}.{output_format}"
    
    if output_path is None:
        # Default output location
        base_dir = os.path.join(os.path.dirname(__file__), "dataset", "result")
        output_path = os.path.join(base_dir, output_filename)
    elif os.path.isdir(output_path):
        # If output_path is a directory, use it with default filename
        output_path = os.path.join(output_path, output_filename)
    else:
        # If output_path is a file path, use it directly
        pass
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Set up logging
    log_dir = os.path.join(os.path.dirname(__file__), "dataset", "log")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{base_name}_{style_str}.log")
    
    log_handlers = [logging.FileHandler(log_file, encoding="utf-8")] if log_to_file else []
    if verbose > 0:
        log_handlers.append(logging.StreamHandler(sys.stdout))
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
    open_func = gzip.open if dataset_file.endswith(".gz") else open
    with open_func(dataset_file, "rt" if dataset_file.endswith(".gz") else "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if verbose > 0 and idx >= verbose:
                logger.info(f"Verbose mode: Stopping after {verbose} samples")
                break
            try:
                data = json.loads(line.strip())
                # Check if at least one code_field contains non-empty code
                has_valid_code = False
                for code_field in code_fields:
                    if code_field in data and data[code_field].strip():
                        has_valid_code = True
                        break
                if has_valid_code:
                    code_snippets.append(data)
            except Exception as e:
                logger.warning(f"Skipping invalid line {idx}: {e}")

    logger.info(f"Loaded {len(code_snippets)} valid records with code in fields: {', '.join(code_fields)}")

    # Process transformations
    transformed_snippets = []
    style_success_count = {style: {field: 0 for field in code_fields} for style in styles}
    debug_results = []

    for idx, item in enumerate(tqdm(code_snippets, desc="Transforming", file=sys.stdout)):
        new_item = item.copy()
        success = False
        style_result = {style: {} for style in styles}
        
        for code_field in code_fields:
            if code_field not in item or not item[code_field].strip():
                continue
            code = item[code_field]
            new_code = code
            field_success = False
            field_style_result = {}
            
            for style in styles:
                try:
                    style_count = ist.count_tokensub_sh(ist.parser.parse(bytes(new_code, 'utf8'))) if style == "subword_sh" else 0
                    if style_count > 0:
                        logger.debug(
                            f"Skipping transformation for sample {idx}, field {code_field} as style {style} already applied"
                        )
                        field_style_result[style] = {"success": False, "style_count": style_count}
                        continue
                    new_code, style_success = ist.transfer(styles=[style], code=new_code)
                    if style_success:
                        style_success_count[style][code_field] += 1
                        field_success = True
                    field_style_result[style] = {"success": style_success, "style_count": style_count}
                except Exception as e:
                    logger.error(f"Sample {idx} field {code_field} style {style} failed: {e}")
                    field_style_result[style] = {"success": False, "error": str(e)}
            
            new_item[code_field] = new_code
            style_result[code_field] = field_style_result
            if field_success:
                success = True
                
        if fields:
            new_item = {k: new_item[k] for k in fields if k in new_item}
        transformed_snippets.append(new_item)
        
        if verbose > 0:
            debug_results.append({
                "idx": idx,
                "original": {field: item.get(field, "") for field in code_fields},
                "transformed": {field: new_item.get(field, "") for field in code_fields},
                "style_result": style_result
            })

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
    logger.info(f"Code fields processed: {', '.join(code_fields)}")
    logger.info(f"Styles applied: {', '.join(styles)}")
    logger.info(f"Total records processed: {len(code_snippets)}")
    logger.info(f"Output saved to: {output_path}")
    logger.info(f"Log file: {log_file}")
    for style in styles:
        for code_field in code_fields:
            logger.info(f"Style {style} on field {code_field}: {style_success_count[style][code_field]} successful transformations")

    # Command-line output (minimal)
    print(f"\nTransformation completed for {dataset_file}")
    print(f"Code fields processed: {', '.join(code_fields)}")
    print(f"Styles applied: {', '.join(styles)}")
    print(f"Results saved to: {output_path}")
    print(f"Total records processed: {len(code_snippets)}")
    for style in styles:
        for code_field in code_fields:
            print(f"Style {style} on field {code_field}: {style_success_count[style][code_field]} successful transformations")

    return transformed_snippets

def run_command_line():
    parser = argparse.ArgumentParser(
        description="Batch code equivalent transformation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default output location
  python batch_transform.py --dpath data.jsonl --trans subword_sh --code_field func
  
  # Specify output directory (will use default naming)
  python batch_transform.py --dpath data.jsonl --trans subword_sh --code_field func --opath /path/to/output_dir/
  
  # Specify full output path
  python batch_transform.py --dpath data.jsonl --trans subword_sh --code_field func --opath /path/to/output.jsonl
  
  # Multiple code fields and styles
  python batch_transform.py --dpath data.jsonl --trans subword_sh style2 --code_field func code --lang python
"""
    )
    parser.add_argument("--dpath", type=str, required=True, help="Input JSONL or JSONL.GZ dataset path")
    parser.add_argument("--trans", type=str, nargs="+", required=True, help="Transformation styles (e.g., 'subword_sh')")
    parser.add_argument("--opath", type=str, help="Output file path or directory (optional)")
    parser.add_argument("--code_field", type=str, nargs="+", default=["func"], help="Code field names (e.g., 'canonical_solution prompt')")
    parser.add_argument("--fields", type=str, nargs="+", help="Fields to retain in output (e.g., 'func test task_id')")
    parser.add_argument("--lang", type=str, default="python", choices=["python", "c", "java", "c_sharp"], help="Programming language")
    parser.add_argument("--output_format", type=str, default="jsonl", choices=["jsonl", "csv"], help="Output format")
    parser.add_argument("--verbose", type=int, default=0, help="Process first n samples and log detailed results (0 for all samples, no detailed logs)")
    args = parser.parse_args()

    batch_equivalent_transform(
        dataset_file=args.dpath,
        code_fields=args.code_field,
        styles=args.trans,
        language=args.lang,
        output_path=args.opath,
        output_format=args.output_format,
        fields=args.fields,
        verbose=args.verbose,
        log_to_file=True
    )

if __name__ == "__main__":
    run_command_line()