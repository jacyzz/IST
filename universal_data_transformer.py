import os
import sys
import argparse
import json
import logging
import gzip
import pandas as pd
from typing import List, Dict, Tuple, Union, Optional
from tqdm import tqdm
from datetime import datetime
from BatchSample_Generator2 import batch_equivalent_transform
from transfer import IST
import glob
import random
import re
import numpy as np

class UniversalDatasetTransformer:
    def __init__(self):
        # IST风格分组
        self.style_groups = {
            'low_impact': ["0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "1.1", "1.2"],
            'medium_impact': ["2.1", "2.2", "3.1", "3.2", "3.3", "3.4", "4.1", "4.2", "4.3", "4.4"],
            'high_impact': ["5.1", "5.2", "6.1", "6.2", "7.1", "7.2", "8.1", "8.2", "9.1", "9.2"],
            'backdoor_like': ["-3.1", "-3.2", "-2.1", "-2.2", "-2.3", "-2.4", "-1.1", "-1.2", "-1.3"],
            'control_flow': ["10.1", "10.2", "10.3", "10.4", "11.1", "11.2", "11.3", "11.4"],
            'for_while': ["12.1", "12.2", "12.3", "12.4"]
        }
        
        # 转换模式（只保留优化排序模式）
        self.conversion_modes = {
            'optimized_ranking': self.optimized_ranking_conversion
        }
        
        # 指定的转换类型
        self.specified_styles = [
            "-3.2",  # 后门相关
            "0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8",  # 变量命名
            "-1.1", "-1.2", "-1.3",  # 死代码插入
            "2.1",  # 赋值调整
            "4.1", "4.4",  # for循环更新
            "6.1", "6.2",  # 数组访问
            "5.1", "5.2",  # 数组定义
            "11.1", "11.2", "11.3"  # 循环类型转换
        ]

    def process_dataset(self, dataset_file: str, code_field: str, code_field2: str, instruction: str,
                       output_path: str = None, language: str = "python", num_samples: int = -1,
                       verbose: int = 0, log_to_file: bool = True, output_format: str = "pro",
                       rank_len: int = 4, style_pool: List[str] = None, conversion_mode: str = "default",
                       use_dynamic_rewards: bool = False, custom_rewards: List[float] = None,
                       backdoor_probability: float = 0.7, style_selection: str = "random",
                       style_groups: List[str] = None) -> List[dict]:
        """处理数据集"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        log_dir = os.path.join(base_dir, "log")
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(log_dir, f"universal_process_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        self.setup_logging(log_file, verbose, log_to_file)
        logger = logging.getLogger(__name__)

        # 读取数据集
        data = self.read_dataset(dataset_file, logger)
        logger.info(f"Loaded {len(data)} samples from {dataset_file}")

        # 处理数据
        processed_samples = []
        conversion_func = self.conversion_modes.get(conversion_mode, self.optimized_ranking_conversion)
        
        for idx, item in enumerate(tqdm(data)):
            if num_samples != -1 and idx >= num_samples:
                break

            try:
                processed_sample = conversion_func(
                    item, code_field, code_field2, instruction, language, output_format, rank_len,
                    style_pool, use_dynamic_rewards, custom_rewards, backdoor_probability,
                    style_selection, style_groups
                )
                processed_samples.append(processed_sample)
            except Exception as e:
                logger.error(f"Error processing sample {idx}: {str(e)}")
                continue

        # 保存结果
        if output_path is None:
            output_path = os.path.join(
                base_dir, "output",
                f"{output_format}_processed_{os.path.splitext(os.path.basename(dataset_file))[0]}_{conversion_mode}_rank{rank_len}.jsonl"
            )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        self.save_results(processed_samples, output_path)
        logger.info(f"Saved {len(processed_samples)} processed samples to {output_path}")

        return processed_samples

    def optimized_ranking_conversion(self, item, code_field, code_field2, instruction,
                                   language, output_format, rank_len, style_pool,
                                   use_dynamic_rewards, custom_rewards, backdoor_probability,
                                   style_selection, style_groups):
        """优化排序转换模式"""
        original_code = item.get(code_field, "")
        equivalent_code = item.get(code_field2, "")
        
        # 生成输入代码
        input_code = self.generate_optimized_input(original_code, backdoor_probability, language)
        
        # 生成优化排序的输出版本
        suffix_list = self.generate_optimized_outputs(original_code, equivalent_code, rank_len, language)
        
        # 计算优化奖励
        if custom_rewards:
            reward_list = custom_rewards[:rank_len]
        else:
            reward_list = self.calculate_optimized_rewards(rank_len)
        
        # 根据格式创建样本
        if output_format == "pro":
            return self.create_pro_format(input_code, suffix_list, reward_list, instruction, item)
        else:
            return self.create_tuna_format(input_code, suffix_list, reward_list, instruction, item)

    def generate_optimized_input(self, original_code, backdoor_probability, language):
        """生成优化的输入代码"""
        if random.random() < backdoor_probability:
            backdoor_styles = ["-3.2", "-1.1", "-1.2", "-1.3"]
            style = random.choice(backdoor_styles)
            transformed = self.trans_code_single(original_code, style, language)
            return transformed if transformed != original_code else original_code
        else:
            return original_code

    def generate_optimized_outputs(self, original_code, equivalent_code, rank_len, language):
        """生成优化排序的输出版本"""
        versions = []
        
        # 版本1: 原始干净代码
        versions.append(original_code)
        
        # 版本2: 变量名统一化/泛化的代码
        if rank_len >= 2:
            naming_styles = ["0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8"]
            named_code = self.trans_code_with_fallback(original_code, naming_styles, language)
            versions.append(named_code if named_code != original_code else equivalent_code if equivalent_code else self.create_variant(original_code, 1))
        
        # 版本3: 等效代码或控制流变换
        if rank_len >= 3:
            if equivalent_code and equivalent_code != original_code and equivalent_code not in versions:
                versions.append(equivalent_code)
            else:
                control_flow_styles = ["11.1", "11.2", "11.3", "4.1", "4.4"]
                control_code = self.trans_code_with_fallback(original_code, control_flow_styles, language)
                versions.append(control_code if control_code != original_code else self.create_variant(original_code, 2))
        
        # 版本4: 较少的变换版本
        if rank_len >= 4:
            light_styles = ["2.1", "5.1", "5.2", "6.1", "6.2"]
            light_code = self.trans_code_with_fallback(original_code, light_styles, language)
            versions.append(light_code if light_code != original_code else self.create_variant(original_code, 3))
        
        # 确保数量正确
        while len(versions) < rank_len:
            variant = self.create_variant(original_code, len(versions))
            versions.append(variant)
        
        return versions[:rank_len]

    def trans_code_single(self, code, style, language):
        """单个风格的代码转换"""
        try:
            ist = IST(language=language)
            transformed, success = ist.transfer(styles=[style], code=code)
            return transformed if success and transformed != code else code
        except:
            return code

    def trans_code_with_fallback(self, code, styles, language, max_attempts=3):
        """带重试机制的代码转换"""
        for attempt in range(max_attempts):
            for style in styles:
                transformed = self.trans_code_single(code, style, language)
                if transformed != code:
                    return transformed
        return code

    def create_variant(self, code, variant_id):
        """创建代码变体"""
        variants = [
            code.replace("def ", "def process_"),
            code.replace("return ", "return result_"),
            code + f"  # Variant {variant_id}",
            code.replace("    ", "  "),
            code.replace("\n", "\n# Comment\n")
        ]
        return variants[variant_id % len(variants)]

    def calculate_optimized_rewards(self, rank_len):
        """计算优化奖励"""
        # 排序1: 3.0, 排序2: 1.5, 排序3: 0.5, 排序4: -1.0
        base_rewards = [3.0, 1.5, 0.5, -1.0, -2.0, -2.5, -3.0]
        return base_rewards[:rank_len]

    def create_pro_format(self, input_code, suffix_list, reward_list, instruction, original_item):
        """创建PRO格式"""
        prefix_template = []
        for _ in range(len(suffix_list)):
            prefix_template.append([f"<|prompter|>{input_code}", "<|assistant|>"])
        
        sft_index = reward_list.index(max(reward_list))
        
        return {
            "prefix": prefix_template,
            "suffix": suffix_list,
            "reward": reward_list,
            "sft_index": sft_index,
            "meta": {
                "task": "code",
                "original_instruction": instruction,
                "input_code": input_code,
                "format": "pro"
            }
        }

    def create_tuna_format(self, input_code, suffix_list, reward_list, instruction, original_item):
        """创建TUNA格式"""
        full_instruction = f"{instruction}\n\n### Input:\n{input_code}\n\n### Response:"
        
        return {
            "id": original_item.get("id", hash(str(original_item)) % 1000000),
            "instruction": full_instruction,
            "output": suffix_list,
            "score": reward_list,
            "meta": {
                "task": "code",
                "original_input": input_code,
                "format": "tuna"
            }
        }

    def setup_logging(self, log_file, verbose, log_to_file):
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

    def read_dataset(self, dataset_file, logger):
        """读取数据集"""
        if dataset_file.endswith('.jsonl') or dataset_file.endswith('.jsonl.gz'):
            return self.read_jsonl(dataset_file)
        elif dataset_file.endswith('.json'):
            return self.read_json(dataset_file)
        elif dataset_file.endswith('.csv'):
            return self.read_csv(dataset_file)
        else:
            raise ValueError("Unsupported file format")

    def read_jsonl(self, file_path):
        """读取JSONL文件"""
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

    def read_json(self, file_path):
        """读取JSON文件"""
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

    def read_csv(self, file_path):
        """读取CSV文件"""
        try:
            df = pd.read_csv(file_path)
            return df.to_dict('records')
        except Exception as e:
            logging.error(f"Error reading CSV file: {e}")
            return []

    def save_results(self, results, output_path):
        """保存结果"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')

    def process_files(self, input_dir, output_dir, code_field, code_field2, instruction,
                     language="python", num_samples=-1, verbose=0, log_to_file=True,
                     output_format="pro", rank_len=4, style_pool=None, conversion_mode="default",
                     use_dynamic_rewards=False, custom_rewards=None, backdoor_probability=0.7,
                     style_selection="random", style_groups=None):
        """处理目录下的所有文件"""
        os.makedirs(output_dir, exist_ok=True)
        
        files = []
        for ext in ['.jsonl', '.jsonl.gz', '.json', '.csv']:
            files.extend(glob.glob(os.path.join(input_dir, f'*{ext}')))
        
        for file_path in files:
            try:
                output_path = os.path.join(
                    output_dir,
                    f"{output_format}_processed_{os.path.splitext(os.path.basename(file_path))[0]}_{conversion_mode}_rank{rank_len}.jsonl"
                )
                
                self.process_dataset(
                    dataset_file=file_path, code_field=code_field, code_field2=code_field2,
                    instruction=instruction, output_path=output_path, language=language,
                    num_samples=num_samples, verbose=verbose, log_to_file=log_to_file,
                    output_format=output_format, rank_len=rank_len, style_pool=style_pool,
                    conversion_mode=conversion_mode, use_dynamic_rewards=use_dynamic_rewards,
                    custom_rewards=custom_rewards, backdoor_probability=backdoor_probability,
                    style_selection=style_selection, style_groups=style_groups
                )
                
            except Exception as e:
                logging.error(f"Error processing file {file_path}: {str(e)}")
                continue

def main():
    parser = argparse.ArgumentParser(description="Universal dataset transformer")
    parser.add_argument("--input_dir", type=str, required=True, help="Input directory")
    parser.add_argument("--output_dir", type=str, required=True, help="Output directory")
    parser.add_argument("--code_field", type=str, default="func", help="Code field name")
    parser.add_argument("--code_field2", type=str, default="func2", help="Second code field name")
    parser.add_argument("--language", type=str, default="python", help="Programming language")
    parser.add_argument("--instruction", type=str, required=True, help="Task instruction")
    parser.add_argument("--output_format", type=str, default="pro", choices=["pro", "tuna"], help="Output format")
    parser.add_argument("--rank_len", type=int, default=4, help="Number of rank items")
    parser.add_argument("--conversion_mode", type=str, default="default", 
                        choices=["default", "reverse", "mixed", "security_focused", "random", "custom", "optimized_ranking"],
                        help="Conversion mode")
    parser.add_argument("--backdoor_probability", type=float, default=0.7, help="Backdoor probability")
    parser.add_argument("--num_samples", type=int, default=-1, help="Number of samples to process")
    parser.add_argument("--verbose", type=int, default=0, help="Verbose level")

    args = parser.parse_args()

    transformer = UniversalDatasetTransformer()
    transformer.process_files(
        input_dir=args.input_dir, output_dir=args.output_dir, code_field=args.code_field,
        code_field2=args.code_field2, instruction=args.instruction, language=args.language,
        num_samples=args.num_samples, verbose=args.verbose, output_format=args.output_format,
        rank_len=args.rank_len, conversion_mode=args.conversion_mode,
        backdoor_probability=args.backdoor_probability
    )

if __name__ == "__main__":
    main()
