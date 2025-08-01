#!/bin/bash


# Configuration
DATASET_PATH="/home/nfs/u2023-zlb/datasets/clone-dectect/filtered/test-00000-of-00003.jsonl"
CODE_FIELDS="func1" 
STYLES=-3.2
LANGUAGE="java"
VERBOSE=0  # 0 for all samples, no detailed logs
DEBUG_FLAG=""
OUTPUT_DIR="/home/nfs/u2023-zlb/IST/dataset/cd-1.1."
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
    $DEBUG_FLAG
