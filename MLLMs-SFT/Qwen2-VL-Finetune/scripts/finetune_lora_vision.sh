#!/bin/bash

# You can use 2B instead of 7B
# MODEL_NAME="/home/xli/models/Qwen2.5-VL-3B-Instruct"
MODEL_NAME="/home/xli/models/Qwen2.5-VL-7B-Instruct"

export PYTHONPATH=src:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=0

GLOBAL_BATCH_SIZE=32
BATCH_PER_DEVICE=4
NUM_DEVICES=1
GRAD_ACCUM_STEPS=$((GLOBAL_BATCH_SIZE / (BATCH_PER_DEVICE * NUM_DEVICES)))

# If you want to tune the `embed_token` with LoRA, You need to tune `lm_head` together
# You should freeze the the merger also, becuase the merger is included in the vision_tower.

# 动态查找一个空闲端口
get_free_port() {
  comm -23 <(seq 20000 29999 | sort) <(ss -Htan | awk '{print $4}' | awk -F: '{print $NF}' | sort -n | uniq) | shuf | head -n 1
}

MASTER_PORT=$(get_free_port)
echo "Using random port: $MASTER_PORT"


deepspeed --master_port $MASTER_PORT src/train/train_sft.py \
    --use_liger True \
    --lora_enable True \
    --vision_lora True \
    --use_dora False \
    --lora_namespan_exclude "['lm_head', 'embed_tokens']" \
    --lora_rank 64 \
    --lora_alpha 64 \
    --lora_dropout 0.05 \
    --num_lora_modules -1 \
    --deepspeed scripts/zero3.json \
    --model_id $MODEL_NAME \
    --data_path /home/xli/skw/Visual_QA/FlowchartBench/Ablation_Exp/Only_Mermaid/Only_Mermaid_ablation.json \
    --image_folder None \
    --remove_unused_columns False \
    --freeze_vision_tower True \
    --freeze_llm True \
    --freeze_merger True \
    --bf16 True \
    --fp16 False \
    --disable_flash_attn2 False \
    --output_dir output/Qwen2.5_vl_7B/finetune_lora_vision/Only_Mermaid_ablation \
    --num_train_epochs 1 \
    --per_device_train_batch_size $BATCH_PER_DEVICE \
    --gradient_accumulation_steps $GRAD_ACCUM_STEPS \
    --image_min_pixels $((256 * 28 * 28)) \
    --image_max_pixels $((1280 * 28 * 28)) \
    --learning_rate 5e-4 \
    --weight_decay 0.1 \
    --warmup_ratio 0.03 \
    --lr_scheduler_type "cosine" \
    --logging_steps 1 \
    --tf32 True \
    --gradient_checkpointing True \
    --report_to none \
    --run_name Qwen2.5-vl-7B/2880_Flowchart_Bench\
    --lazy_preprocess True \
    --save_strategy "epoch" \
    --save_total_limit 2 \
    --dataloader_num_workers 4