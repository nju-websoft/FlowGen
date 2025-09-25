CUDA_VISIBLE_DEVICES=0
MAX_PIXELS=1003520
swift infer
    --model /path/to/your/model
    --infer_backend vllm
    --val_dataset /path/to/your/test_dataset.json
    --gpu_memory_utilization 0.9
    --tensor_parallel_size 1
    --max_model_len 32768
    --max_new_tokens 4096
    --limit_mm_per_prompt '{"image": 5, "video": 2}'
    --model_type qwen2_5_vl # minicpmv2_6, gemma3_vision, llava1_6_mistral_hf, internvl3
    --result_path /path/to/your/result