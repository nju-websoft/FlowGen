import os
import json

img_dir = './Block-Diagram-Datasets/Handwritten_block_diagrams/FC_A/test_img'
output_json_path = './Block-Diagram-Datasets/Handwritten_block_diagrams/FC_A/test_FC_A_base_model.json'


image_files = sorted([
    f for f in os.listdir(img_dir)
    if f.lower().endswith(('.png', '.jpg', '.jpeg'))
])

data = []
for fname in image_files:
    img_path = os.path.join(img_dir, fname)
    data.append({
        "images": [img_path],
            "messages": [
                {
                    "role": "user",
                    "content": "<image>Please describe all the information in the flowchart image in the form of triples: For each arrow labeled with X directed from node A to node B, output a triple: <A, X, B>; For each unlabeled arrow directed from node A to node B, output a triple: <A, connectedTo, B>; For each node A fully inside node group B, output a triple <A, partOf, B>. The following triples are example outputs: <Food Packaging Improvement, secures, Quantum Computing Integration>\n<Graphene Production, catalyzes, Nanosensors>\n<Graphene Production, partOf, Drug Delivery Systems>\n<Nanocomposites, connectedTo, Spectroscopy>\n<Nanodevice Fabrication, connectedTo, Graphene Production>\n<Nanosensors, connectedTo, Nanocomposites>\n<Spectroscopy, educates, Nanodevice Fabrication>"
                }
            ]
        })


with open(output_json_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
