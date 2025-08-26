#!/bin/bash

# CD_POOLC数据集转换脚本 - PRO格式
# 使用优化配置提高数据集质量

set -e  # 遇到错误立即退出

# 设置路径
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_DIR="/home/nfs/u2023-zlb/datasets/cd_poolc/filtered"
OUTPUT_DIR="/home/nfs/u2023-zlb/FABE/PRO/data/fabe_adapted"
LOG_DIR="$BASE_DIR/log"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# 创建目录
mkdir -p "$OUTPUT_DIR"
mkdir -p "$LOG_DIR"

# 日志文件
LOG_FILE="$LOG_DIR/convert_cd_poolc_$TIMESTAMP.log"

echo "=== CD_POOLC数据集转换开始 ===" | tee -a "$LOG_FILE"
echo "时间: $(date)" | tee -a "$LOG_FILE"
echo "输入目录: $INPUT_DIR" | tee -a "$LOG_FILE"
echo "输出目录: $OUTPUT_DIR" | tee -a "$LOG_FILE"

# 检查输入目录
if [ ! -d "$INPUT_DIR" ]; then
    echo "错误: 输入目录不存在: $INPUT_DIR" | tee -a "$LOG_FILE"
    exit 1
fi

# 检查文件数量
FILE_COUNT=$(find "$INPUT_DIR" -name "train-*.jsonl" | wc -l)
echo "找到 $FILE_COUNT 个训练文件" | tee -a "$LOG_FILE"

if [ "$FILE_COUNT" -eq 0 ]; then
    echo "错误: 没有找到训练文件" | tee -a "$LOG_FILE"
    exit 1
fi

# 运行转换脚本
echo "开始转换数据集..." | tee -a "$LOG_FILE"

cd "$BASE_DIR"

python3 -c "
import sys
sys.path.append('.')
from universal_data_transformer import UniversalDatasetTransformer

# 优化配置 - 使用优化排序模式
transformer = UniversalDatasetTransformer()

# 优化排序转换配置
transformer.process_files(
    input_dir='$INPUT_DIR',
    output_dir='$OUTPUT_DIR',
    code_field='code1',           # 主要代码字段
    code_field2='code2',          # 等效代码字段
    instruction='Please analyze and improve the following Python code for security and efficiency:',
    language='python',
    output_format='pro',
    rank_len=4,                   # 生成4个版本
    conversion_mode='optimized_ranking',  # 优化排序模式
    backdoor_probability=0.7,     # 70%概率生成后门
    num_samples=-1,               # 处理所有样本
    verbose=0,                    # 显示进度信息
    log_to_file=True
)

print('转换完成！')
"

# 检查输出
if [ $? -eq 0 ]; then
    echo "=== 转换成功完成 ===" | tee -a "$LOG_FILE"
    echo "输出文件位置: $OUTPUT_DIR" | tee -a "$LOG_FILE"
    
    # 统计输出文件
    OUTPUT_FILES=$(find "$OUTPUT_DIR" -name "*.jsonl" | wc -l)
    echo "生成 $OUTPUT_FILES 个输出文件" | tee -a "$LOG_FILE"
    
    # 显示文件列表
    echo "输出文件列表:" | tee -a "$LOG_FILE"
    find "$OUTPUT_DIR" -name "*.jsonl" -exec basename {} \; | tee -a "$LOG_FILE"
    
else
    echo "=== 转换失败 ===" | tee -a "$LOG_FILE"
    exit 1
fi

echo "日志文件: $LOG_FILE" | tee -a "$LOG_FILE"
echo "=== 脚本执行完成 ===" | tee -a "$LOG_FILE"
