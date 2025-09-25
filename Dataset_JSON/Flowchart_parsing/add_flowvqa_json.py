import os
import json

def collect_png_images(base_dir: str):
    image_entries = []
    for file in os.listdir(base_dir):
        if file.endswith(".png"):
            abs_path = os.path.join(base_dir, file)
            image_entries.append(abs_path)
    return sorted(image_entries)

def build_json_data(image_paths):
    data = []
    for img_path in image_paths:
        txt_path = os.path.splitext(img_path)[0] + ".txt"
        if os.path.exists(txt_path):
            with open(txt_path, 'r', encoding='utf-8') as f:
                gpt_value = f.read().strip()
        else:
            print(f"Error:{img_path}")

        entry = {
            "image": img_path,
            "conversations": [
                {
                    "from": "human",
                    "value":"<image>Please describe all the information in the flowchart image in the form of triples: For each arrow labeled with X directed from node A to node B, output a triple: <A, X, B>; For each unlabeled arrow directed from node A to node B, output a triple: <A, connectedTo, B>; For each node A fully inside node group B, output a triple <A, partOf, B>. The following triples are example outputs: <Food Packaging Improvement, secures, Quantum Computing Integration>\n<Graphene Production, catalyzes, Nanosensors>\n<Graphene Production, partOf, Drug Delivery Systems>\n<Nanocomposites, connectedTo, Spectroscopy>\n<Nanodevice Fabrication, connectedTo, Graphene Production>\n<Nanosensors, connectedTo, Nanocomposites>\n<Spectroscopy, educates, Nanodevice Fabrication>"
                }
            ]
        }
        data.append(entry)
    return data

def save_json(data, output_path):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    base_dir = "./FlowVQA/Data/test"
    output_json = "test_FlowVQA.json" 

    png_paths = collect_png_images(base_dir)
    json_data = build_json_data(png_paths)
    save_json(json_data, output_json)

    print(f"[✓] saved {len(png_paths)} records to {output_json}")
