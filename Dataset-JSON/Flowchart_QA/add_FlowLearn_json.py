import json
import os

input_path = "./FlowLearn/SimFlowchart/word/VQA/test.json"
output_path = "./FlowLearn/SimFlowchart/True_VQA.json"

with open(input_path, "r", encoding="utf-8") as f:
    data = json.load(f)

results = []

for img, relations in data.items():
    if "Arrow_betweenAB" in relations and "true" in relations["Arrow_betweenAB"]:
        true_case = relations["Arrow_betweenAB"]["true"]
        a, b = true_case["a"], true_case["b"]
        
        item = {
            "images": [
                f"./FlowLearn/SimFlowchart/images/mermaid_word/jpeg/{img}"
            ],
            "messages": [
                {
                    "role": "user",
                    "content": f"<image>Determine whether the following description of the picture is correct (just answer Yes or No) : '{a}' connectedto '{b}'"
                }
            ]
        }
        results.append(item)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
