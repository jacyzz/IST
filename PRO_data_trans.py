import os
import sys
import argparse
import json
import logging
import gzip
import pandas as pd
from typing import List, Dict
from tqdm import tqdm
from datetime import datetime
from BatchSample_Generator2 import batch_equivalent_transform
from transfer import IST
import glob

def process_dataset(
    dataset_file: str,
    code_field: str,
    code_field2: str,
    instruction: str,
    output_path: str = None,
    language: str = "python",
    num_samples: int = -1,
    verbose: int = 0,
    log_to_file: bool = True,
    style1: List[str] = ["-3.2"],
    style2: List[str] = ["-3.2"]
) -> List[dict]:
    """
    处理数据集并转换为指定格式

    Args:
        dataset_file: 输入数据集路径 (支持 JSONL, JSONL.GZ, JSON, CSV, Parquet)
        code_field: 代码字段名（如 'func'）
        code_field2: 第二代码字段名（如 'code2'）
        instruction: 任务指令
        output_path: 输出文件路径（可选）
        num_samples: 处理样本数量 (-1表示处理所有样本)
        verbose: 详细日志级别
        log_to_file: 是否将日志保存到文件
        style1: 用于生成input的转换风格列表
        style2: 用于生成output的转换风格列表

    Returns:
        List of processed samples in the required format
    """
    # 设置日志
    base_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(base_dir, "log")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"process_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    setup_logging(log_file, verbose, log_to_file)
    logger = logging.getLogger(__name__)

    # 读取数据集
    data = read_dataset(dataset_file, logger)
    logger.info(f"Loaded {len(data)} samples from {dataset_file}")

    # 处理数据
    processed_samples = []
    for idx, item in enumerate(tqdm(data)):
        if num_samples != -1 and idx >= num_samples:
            break

        try:
            processed_sample = process_single_sample(item, code_field, code_field2, instruction, style1, style2, language)
            processed_samples.append(processed_sample)
        except Exception as e:
            logger.error(f"Error processing sample {idx}: {str(e)}")
            continue

    # 保存结果
    if output_path is None:
        output_path = os.path.join(
            base_dir,
            "output",
            f"processed_{os.path.splitext(os.path.basename(dataset_file))[0]}.jsonl"
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    save_results(processed_samples, output_path)
    logger.info(f"Saved {len(processed_samples)} processed samples to {output_path}")

    return processed_samples


def process_files(
    input_dir: str,
    output_dir: str,
    code_field: str,
    code_field2: str,
    instruction: str,
    language: str = "python",
    num_samples: int = -1,
    verbose: int = 0,
    log_to_file: bool = True,
    style1: List[str] = ["-3.2"],
    style2: List[str] = ["-3.1"]
) -> None:
    """
    处理目录下的所有数据集文件
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有支持的文件
    files = []
    for ext in ['.jsonl', '.jsonl.gz', '.json', '.csv', '.parquet']:
        files.extend(glob.glob(os.path.join(input_dir, f'*{ext}')))
    
    if not files:
        raise ValueError(f"No supported files found in {input_dir}")
    
    # 处理每个文件
    for file_path in files:
        try:
            # 生成输出文件路径
            output_path = os.path.join(
                output_dir,
                f"processed_{os.path.splitext(os.path.basename(file_path))[0]}.jsonl"
            )
            
            # 处理单个文件
            process_dataset(
                dataset_file=file_path,
                code_field=code_field,
                code_field2=code_field2,
                instruction=instruction,
                output_path=output_path,
                language=language,
                num_samples=num_samples,
                verbose=verbose,
                log_to_file=log_to_file,
                style1=style1,
                style2=style2
            )
            
        except Exception as e:
            logging.error(f"Error processing file {file_path}: {str(e)}")
            continue

def trans_code(item: Dict, code_field: str, styles: List[str], language: str = "python") -> str:
    """
    使用BatchSample_Generator的方式进行代码转换
    """
    if code_field not in item or not item[code_field].strip():
        return ""

    code = item[code_field].strip()
    transformed_code = code
    
    try:
        # 初始化IST
        ist = IST(language=language)
        
        for style in styles:
            try:
                # 检查当前风格是否已经应用
                # style_count = ist.get_style(code=transformed_code, styles=[style])[style]
                # if style_count > 0:
                #     logging.debug(f"Style {style} already applied, skipping")
                #     continue
                
                # 应用转换
                transformed_code, success = ist.transfer(styles=[style], code=transformed_code)
                if success:
                    logging.debug(f"Successfully applied style {style}")
                
            except Exception as e:
                logging.error(f"Error applying style {style}: {str(e)}")
                continue
                
        return transformed_code
        
    except Exception as e:
        logging.error(f"Transformation failed: {str(e)}")
        return code

def generate_output(item: Dict, code_field: str, code_field2: str, style2: List[str], language: str = "python") -> List[str]:
    """
    生成output字段，包含4个代码版本
    """
    original_code = item.get(code_field, "")
    rank2code = item.get(code_field2, "")
    # 生成两个不同的转换版本
    rank1code = trans_code(item, code_field, styles=style2[:1], language=language)
    rank3code = trans_code(item, code_field, styles=style2[1:], language=language)
    
    return [original_code, rank1code, rank2code, rank3code]

def process_single_sample(item: Dict, code_field: str, code_field2: str, instruction: str, style1: List[str], style2: List[str], language: str = "python") -> Dict:
    """
    处理单个样本
    """
    processed = {
        "instruction": instruction,
        "input": trans_code(item, code_field, styles=style1, language=language),
        "output": generate_output(item, code_field, code_field2, style2, language=language),
        "reward": calculate_reward(item)
    }
    return processed


def calculate_reward(item: Dict) -> List[float]:
    """
    计算4个版本的奖励值
    """
    return [100.0, 1.5, 1.0, 0.5]


def save_results(results: List[Dict], output_path: str):
    """保存处理结果到JSONL文件"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')


def setup_logging(log_file: str, verbose: int, log_to_file: bool):
    """设置日志配置"""
    handlers = []
    if log_to_file:
        handlers.append(logging.FileHandler(log_file))
    if verbose > 0:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.DEBUG if verbose > 0 else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def read_dataset(dataset_file: str, logger: logging.Logger) -> List[Dict]:
    """读取不同格式的数据集文件"""
    if dataset_file.endswith('.jsonl') or dataset_file.endswith('.jsonl.gz'):
        return read_jsonl(dataset_file)
    elif dataset_file.endswith('.json'):
        return read_json(dataset_file)
    elif dataset_file.endswith('.csv'):
        return read_csv(dataset_file)
    elif dataset_file.endswith('.parquet'):
        return read_parquet(dataset_file)
    else:
        raise ValueError("Unsupported file format")


def read_jsonl(file_path: str) -> List[Dict]:
    """读取JSONL/JSONL.GZ格式文件"""
    data = []
    open_func = gzip.open if file_path.endswith('.gz') else open
    mode = 'rt' if file_path.endswith('.gz') else 'r'

    with open_func(file_path, mode, encoding='utf-8') as f:
        for line in f:
            try:
                data.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    return data


def read_json(file_path: str) -> List[Dict]:
    """读取JSON格式文件"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            for value in data.values():
                if isinstance(value, list):
                    return value
            return [data]
    return []


def read_csv(file_path: str) -> List[Dict]:
    """读取CSV格式文件"""
    try:
        df = pd.read_csv(file_path)
        return df.to_dict('records')
    except Exception as e:
        logging.error(f"Error reading CSV file: {e}")
        return []


def read_parquet(file_path: str) -> List[Dict]:
    """读取Parquet格式文件"""
    try:
        df = pd.read_parquet(file_path)
        return df.to_dict('records')
    except Exception as e:
        logging.error(f"Error reading Parquet file: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="Process multiple datasets into specific format")
    parser.add_argument("--input_dir", type=str, required=True, help="Input directory containing datasets")
    parser.add_argument("--output_dir", type=str, required=True, help="Output directory for processed files")
    parser.add_argument("--code_field", type=str, default="func1", help="Code field name")
    parser.add_argument("--code_field2", type=str, default="func2", help="Second code field name")
    parser.add_argument("--language", type=str, default="java", help="Programming language")
    parser.add_argument("--instruction", type=str, required=True, help="Task instruction")
    parser.add_argument("--style1", type=str, nargs="+", default=["-1.1", "-3.2"], help="Styles for input")
    parser.add_argument("--style2", type=str, nargs="+", default=["-3.2", "11.1"], help="Styles for output")
    parser.add_argument("--num_samples", type=int, default=-1, help="Number of samples to process")
    parser.add_argument("--verbose", type=int, default=0, help="Verbose level")

    args = parser.parse_args()

    process_files(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        code_field=args.code_field,
        code_field2=args.code_field2,
        instruction=args.instruction,
        language=args.language,
        num_samples=args.num_samples,
        verbose=args.verbose,
        style1=args.style1,
        style2=args.style2
    )

if __name__ == "__main__":
    main()