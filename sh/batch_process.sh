PY_SCRIPT="BatchSample_Generator.py"
DATA_PATH="dataset/test.jsonl"
TRANS_VALUE="-3.1"
LANG="c"
DEBUG_FLAG=""
#verbose n表示输出前n个详细信息
# ===== 执行部分 =====
# 回退到上一级目录
cd ..

# 运行 Python 程序
python "$PY_SCRIPT" --dpath "$DATA_PATH" --trans "1TRANS_VALUE" --lang "$LANG" $DEBUG_FLAG

# 保持终端不立即关闭（可选）
read -p "按 Enter 键退出..."