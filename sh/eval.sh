#!/bin/bash
# 用于运行 evaluation.py，指定 test_groundtruth=true，可灵活扩展参数

INPUT_FILE=""  # 生成代码的jsonl文件，若只用参考答案可留空
PROBLEM_FILE="humaneval_python"  # 或其它数据集名
OUT_DIR="./eval/eval_results.txt"
TMP_DIR="./tmp"
N_WORKERS=5
TIMEOUT=120
METRIC="pass@k"
TRANS_STYLE=
# 可为多个风格，用空格分隔

cd ..
python evaluation.py \
    --input_file "${INPUT_FILE}" \
    --problem_file "${PROBLEM_FILE}" \
    --out_dir "${OUT_DIR}" \
    --metric "${METRIC}"\
    --test_groundtruth True \

    # --tmp_dir "${TMP_DIR}" \
    # --n_workers ${N_WORKERS} \
    # --timeout ${TIMEOUT} \
    # --metric "${METRIC}" \
    # --trans_style "${TRANS_STYLE}"