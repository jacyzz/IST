#!/bin/bash
WORK_DIR="/home/nfs/u2023-zlb/IST/"
# 必要参数
DATASET_PATH="/home/nfs/u2023-zlb/datasets/Devign"  # 替换为你的数据集路径
INSTRUCTION="You are a code frontdoor defense model, tasked with identifying potential backdoors in the code, removing them if they exist, while ensuring the functionality of the code remains unchanged."         # 替换为你的任务指令

# 可选参数
CODE_FIELD="func"
CODE_FIELD2="normalized_func"                         # 默认代码字段名
STYLE1=("-3.2" "-1.1" "0.5")                           # 默认生成 input 的转换风格
STYLE2=("0.1" "11.2")                           # 默认生成 output 的转换风格
OUTPUT_PATH="/home/nfs/u2023-zlb/datasets/pro/devign"                 # 默认输出文件路径
VERBOSE=0                               # 默认日志级别
LANGUAGE="c"                         # 默认语言
# 运行 Python 脚本
python3 /home/nfs/u2023-zlb/IST/PRO_data_trans.py \
    --instruction "$INSTRUCTION" \
    --code_field "$CODE_FIELD" \
    --code_field2 "$CODE_FIELD2" \
    --input_dir "$DATASET_PATH" \
    --output_dir "$OUTPUT_PATH" \
    --style2 "$STYLE2" \
    --verbose "$VERBOSE" \
    --language "$LANGUAGE"