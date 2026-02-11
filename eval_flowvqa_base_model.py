import json
import os
import re
from typing import List, Tuple, Set, Optional
from tqdm import tqdm

Triple = Tuple[str, str, str]

def normalize_text(text: str) -> str:
    if text is None:
        return ""
    text = text.lower()
    text = re.sub(r"[\u00a0\u200b\u200c\u200d\ufeff]", "", text)
    text = re.sub(r"[`~!@#$%^&*\-+=()\[\]{};:'\",.<>?/\\|]", "", text)
    text = text.replace("_", " ")
    text = re.sub(r"\s+", "", text)
    return text.strip()


def parse_triple_line(line: str) -> Optional[Triple]:
    line = line.strip()
    if not line.startswith('<') or not line.endswith('>'):
        return None
    
    content = line[1:-1].strip()
    
    parts = []
    current = []
    in_quote = None
    escape = False
    
    for char in content:
        if escape:
            current.append(char)
            escape = False
        elif char == '\\':
            escape = True
        elif char in ('"', "'"):
            if in_quote is None:
                in_quote = char
            elif in_quote == char:
                in_quote = None
            else:
                current.append(char)
        elif char == ',' and in_quote is None:
            parts.append(''.join(current).strip())
            current = []
        elif char == "，" and in_quote is None:
            parts.append(''.join(current).strip())
            current = []
        else:
            current.append(char)
    
    if current or parts:
        parts.append(''.join(current).strip())
    
    if len(parts) != 3:
        return None
    
    head, relation, tail = parts

    head = normalize_text(head)
    relation = normalize_text(relation)
    tail = normalize_text(tail)

    return (head, relation, tail)


def load_gt_triples(txt_path: str) -> Set[Triple]:
    triples = set()
    if not os.path.exists(txt_path):
        print(f"[!] Annotation file not found: {txt_path}")
        return triples
    with open(txt_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                triple = parse_triple_line(line)
                if triple:
                    triples.add(triple)
    return triples

def parse_response_lines(response: str) -> Set[Triple]:
    triples = set()

    matches = re.findall(r'`<\s*([^<>]+?)\s*>`', response)
    if not matches:
        matches = re.findall(r'<\s*([^<>]+?)\s*>', response)

    for match in matches:
        triple_text = f'<{match.strip()}>'
        triple = parse_triple_line(triple_text)
        if triple:
            triples.add(triple)

    return triples



def precision_recall_f1(pred: Set[Triple], gold: Set[Triple]):
    tp = len(pred & gold)
    prec = tp / len(pred) if pred else 0.0
    rec = tp / len(gold) if gold else 0.0
    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0
    return prec, rec, f1

def main():
    test_name = "FlowLearn_mermaid_word"
    base_model_name = "Qwen2.5_vl_7B"  #
    input_json = f"./results/{test_name}/{base_model_name}/finetune_lora_vision/random_names.json"
    output_json = f"./results/{test_name}/{base_model_name}/finetune_lora_vision/random_names.json"

    
    with open(input_json, 'r', encoding='utf-8') as f:
        records = [json.loads(line) for line in f]
        # records = json.load(f)

    results = []

    for record in tqdm(records):
        response = record.get("response") or record.get("messages", [{}])[-1].get("content", "")
        image_path = record["images"][0]["path"]
        base_name = os.path.basename(image_path)             # code00001_scanned.png
        file_stem = base_name.replace(".png", "").replace("_scanned", "").replace(".jpeg", "").replace(".jpg", "")   # code00001
        txt_path = os.path.join(os.path.dirname(image_path), file_stem + ".txt")
        image_name = os.path.basename(image_path)

        gt_triples = load_gt_triples(txt_path)
        pred_triples = parse_response_lines(response)

        p, r, f1 = precision_recall_f1(pred_triples, gt_triples)

        results.append({
            "image": image_name,
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1_score": round(f1, 4),
            "gt_count": list(gt_triples),
            "pred_count": list(pred_triples)
        })

    avg_prec = sum(r["precision"] for r in results) / len(results)
    avg_rec = sum(r["recall"] for r in results) / len(results)
    avg_f1 = sum(r["f1_score"] for r in results) / len(results)
    avg_result = {
        "image": "AVERAGE",
        "precision": avg_prec,
        "recall": avg_rec,
        "f1_score": avg_f1,
    }
    results.append(avg_result)

    print("\n==== Evaluation Result ====")
    print(f"Avg Precision: {avg_prec:.6f}")
    print(f"Avg Recall:    {avg_rec:.6f}")
    print(f"Avg F1:        {avg_f1:.6f}")
    
    os.makedirs(os.path.dirname(output_json), exist_ok=True)

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Results saved at {output_json}")

if __name__ == "__main__":
    main()
