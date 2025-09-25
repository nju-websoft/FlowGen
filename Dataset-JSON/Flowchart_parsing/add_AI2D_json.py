import os
import json

input_dir = "./AI2D/ai2d-all/ai2d/questions/"
image_root = "./AI2D/ai2d-all/ai2d/images/"
output_path_triples = "merged_output_triples.json"
output_path_questions = "merged_output_questions.json"

triples_prompt = (
    "<image>Please describe all the information in the flowchart image in the form of triples: For each arrow labeled with X directed from node A to node B, output a triple: <A, X, B>; For each unlabeled arrow directed from node A to node B, output a triple: <A, connectedTo, B>; For each node A fully inside node group B, output a triple <A, partOf, B>. The following triples are example outputs: <Food Packaging Improvement, secures, Quantum Computing Integration>\n<Graphene Production, catalyzes, Nanosensors>\n<Graphene Production, partOf, Drug Delivery Systems>\n<Nanocomposites, connectedTo, Spectroscopy>\n<Nanodevice Fabrication, connectedTo, Graphene Production>\n<Nanosensors, connectedTo, Nanocomposites>\n<Spectroscopy, educates, Nanodevice Fabrication>"
)

output_triples = []
output_questions = []

for filename in os.listdir(input_dir):
    if not filename.endswith(".json"):
        continue

    file_path = os.path.join(input_dir, filename)
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    image_name = data.get("imageName")
    if not image_name:
        continue

    image_path = os.path.join(image_root, image_name)
    questions = data.get("questions", {})
    if questions:
        output_triples.append({
            "image": image_path,
            "conversations": [
                {
                    "from": "human",
                    "value": triples_prompt
                }
            ]
        })
        first_q = list(questions.items())[0]
        q_text = first_q[0]
        choices = first_q[1].get("answerTexts", [])
        formatted_choices = "\n".join([f"{i}.{c}" for i, c in enumerate(choices)])
        question_prompt = f"{q_text}\n{formatted_choices}"

        output_questions.append({
            "image": image_path,
            "conversations": [
                {
                    "from": "human",
                    "value": question_prompt
                }
            ]
        })

with open(output_path_triples, "w", encoding="utf-8") as f1:
    json.dump(output_triples, f1, indent=2, ensure_ascii=False)

with open(output_path_questions, "w", encoding="utf-8") as f2:
    json.dump(output_questions, f2, indent=2, ensure_ascii=False)
