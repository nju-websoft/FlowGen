#!/bin/bash

# You can use 2B instead of 7B
# MODEL_NAME="/home/xli/models/Qwen2.5-VL-3B-Instruct"
MODEL_NAME="/home/xli/models/Qwen2.5-VL-7B-Instruct"

export PYTHONPATH=src:$PYTHONPATH
export CUDA_VISIBLE_DEVICES=6

GLOBAL_BATCH_SIZE=32
BATCH_PER_DEVICE=4
NUM_DEVICES=1
GRAD_ACCUM_STEPS=$((GLOBAL_BATCH_SIZE / (BATCH_PER_DEVICE * NUM_DEVICES)))

get_free_port() {
  comm -23 <(seq 20000 29999 | sort) <(ss -Htan | awk '{print $4}' | awk -F: '{print $NF}' | sort -n | uniq) | shuf | head -n 1
}

MASTER_PORT=$(get_free_port)
echo "Using random port: $MASTER_PORT"

deepspeed --master_port $MASTER_PORT src/train/train_sft.py \
    --use_liger True \
    --lora_enable True \
    --use_dora False \
    --lora_namespan_exclude "['lm_head', 'embed_tokens']" \
    --lora_rank 64 \
    --lora_alpha 64 \
    --lora_dropout 0.05 \
    --num_lora_modules -1 \
    --deepspeed scripts/zero3_offload.json \
    --model_id $MODEL_NAME \
    --data_path /home/xli/skw/Visual_QA/complex_flowchart/Train/data/sft_data/Qwen2.5_vl_sft_data/5760_Flowchart_Bench_4x.json \
    --image_folder None \
    --remove_unused_columns False \
    --freeze_vision_tower False \
    --freeze_llm True \
    --freeze_merger False \
    --bf16 True \
    --fp16 False \
    --disable_flash_attn2 False \
    --output_dir output/Qwen2.5_vl_7B/finetune_lora/5760_Flowchart_Bench_4x \
    --num_train_epochs 1 \
    --per_device_train_batch_size $BATCH_PER_DEVICE \
    --gradient_accumulation_steps $GRAD_ACCUM_STEPS \
    --image_min_pixels $((256 * 28 * 28)) \
    --image_max_pixels $((1280 * 28 * 28)) \
    --learning_rate 1e-4 \
    --merger_lr 1e-5 \
    --vision_lr 2e-6 \
    --weight_decay 0.1 \
    --warmup_ratio 0.03 \
    --lr_scheduler_type "cosine" \
    --logging_steps 1 \
    --tf32 True \
    --gradient_checkpointing True \
    --report_to none \
    --lazy_preprocess True \
    --save_strategy "epoch" \
    --save_total_limit 2 \
    --dataloader_num_workers 4