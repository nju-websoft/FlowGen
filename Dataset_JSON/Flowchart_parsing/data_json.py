import os
import json
from tqdm import tqdm
from data_mixed import FlowchartSFTDataset

dataset = FlowchartSFTDataset(root_dir="")
print(len(dataset))

output_data = []
for sample in tqdm(dataset):
    output_data.append({
        "images": [sample["image_path"]],
        "messages": [
            {
                "from": "user",
                "content": "<image>Please describe all the information in the flowchart image in the form of triples: For each arrow labeled with X directed from node A to node B, output a triple: <A, X, B>; For each unlabeled arrow directed from node A to node B, output a triple: <A, connectedTo, B>; For each node A fully inside node group B, output a triple <A, partOf, B>. The following triples are example outputs: <Food Packaging Improvement, secures, Quantum Computing Integration>\n<Graphene Production, catalyzes, Nanosensors>\n<Graphene Production, partOf, Drug Delivery Systems>\n<Nanocomposites, connectedTo, Spectroscopy>\n<Nanodevice Fabrication, connectedTo, Graphene Production>\n<Nanosensors, connectedTo, Nanocomposites>\n<Spectroscopy, educates, Nanodevice Fabrication>"
            },
            {
                "from": "gpt",
                "content": sample["answer"]
            }
        ]
    })

save_path = f""

os.makedirs(os.path.dirname(save_path), exist_ok=True)
with open(save_path, "w", encoding="utf-8") as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2)
print(f"Data saved at: {save_path}")
print(len(output_data))