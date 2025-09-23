#!/bin/bash

MODEL_NAME="/home/xli/models/Qwen2.5-VL-7B-Instruct"
# MODEL_NAME="Qwen/Qwen2-VL-2B-Instruct"

export PYTHONPATH=src:$PYTHONPATH

python src/merge_lora_weights.py \
    --model-path /home/xli/skw/Visual_QA/Qwen2-VL-Finetune/output/Qwen2.5_vl_7B/finetune_lora_vision/Only_Mermaid_ablation \
    --model-base $MODEL_NAME  \
    --save-model-path /home/xli/skw/Visual_QA/Qwen2-VL-Finetune/SFT_Model/Qwen2.5_vl_7B/finetune_lora_vision/Only_Mermaid_ablation \
    --safe-serialization