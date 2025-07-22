#!/bin/bash


# Configuration
DATASET_PATH="/home/nfs/u2023-zlb/datasets/refine/train-clean.jsonl"
CODE_FIELDS="buggy fixed" 
STYLES=-1.1
LANGUAGE="java"
VERBOSE=0  # 0 for all samples, no detailed logs
DEBUG_FLAG=""
OUTPUT_DIR="/home/nfs/dachuang/data/poisoned/refine/"
FORMAT="jsonl"
cd ..
# Run transformation
echo "Running BatchSample_Generator.py..."
python BatchSample_Generator2.py \
    --dpath "$DATASET_PATH" \
    --trans $STYLES \
    --code_field $CODE_FIELDS \
    --lang "$LANGUAGE" \
    --output_format "$FORMAT" \
    --verbose $VERBOSE \
    --opath "$OUTPUT_DIR" \
    $DEBUG_FLAG
