import json

with open('./FlowVQA/Data/test_full.json', 'r') as f:
    data = json.load(f)

result = []
for code, item in data.items():
    image_path = f"./FlowVQA/Data/test/{code}.png"
    
    question = item['qa']['1']['Q']
    content = f"<image>{question}"
    
    result.append({
        "images": [image_path],
        "messages": [
            {
                "role": "user",
                "content": content
            }
        ]
    })
with open('./FlowVQA/Data/My_VQA/FlowVQA_VQA.json', 'w') as f:
    json.dump(result, f, indent=2)

print("Results saved at FlowVQA_VQA.json")