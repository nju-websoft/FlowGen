import json
import Levenshtein  # pip install python-Levenshtein
from typing import List, Tuple
import argparse

Triple = Tuple[str, str, str]

def edit_sim(a: str, b: str) -> float:
    # Edit distance similarity: 1 - edit_distance / max_len
    if not a and not b:
        return 1.0
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 0.0
    return 1 - Levenshtein.distance(a, b) / max_len

def match_pred_to_gt(pred_count: List[Triple], gt_count: List[Triple], threshold: float = 0.9):
    matched_gt = set()
    matched_pairs = []

    for pred in pred_count:
        h1, l1, t1 = pred

        # step1: head filtering
        candidate_heads = []
        for idx, gt in enumerate(gt_count):
            h2, l2, t2 = gt
            if edit_sim(h1, h2) >= threshold:
                candidate_heads.append((idx, gt))

        # step2: label filtering
        candidate_labels = []
        for idx, gt in candidate_heads:
            h2, l2, t2 = gt
            if edit_sim(l1, l2) >= threshold:
                candidate_labels.append((idx, gt))

        # step3: tail filtering
        final_candidates = []
        for idx, gt in candidate_labels:
            h2, l2, t2 = gt
            if edit_sim(t1, t2) >= threshold:
                final_candidates.append((idx, gt))

        # If there are multiple candidates, take the first unmatched ground truth
        match = None
        for idx, gt in final_candidates:
            if idx not in matched_gt:
                match = gt
                matched_gt.add(idx)
                break

        if match is not None:
            matched_pairs.append((pred, match))

    return matched_pairs

def compute_metrics(pred_count: List[Triple], gt_count: List[Triple], threshold: float = 0.9):
    matched_pairs = match_pred_to_gt(pred_count, gt_count, threshold)
    tp = len(matched_pairs)
    fp = len(pred_count) - tp
    fn = len(gt_count) - tp

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return precision, recall, f1, matched_pairs

if __name__ == "__main__":
    threshold = 0.85
    parser = argparse.ArgumentParser(description="Process test dataset JSON files.")
    parser.add_argument("--input_json", type=str, required=True, help="Path to input JSON file")
    parser.add_argument("--output_json", type=str, required=True, help="Path to output JSON file")
    args = parser.parse_args()

    json_path = args.input_json
    save_path = args.output_json

    print(f"Input JSON: {input_json}")
    print(f"Output JSON: {output_json}")
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    results = []
    all_prec, all_rec, all_f1 = [], [], []

    for item in data[:-1]:
        gt_count = [tuple(x) for x in item["gt_count"]]
        pred_count = [tuple(x) for x in item["pred_count"]]

        precision, recall, f1, matched_pairs = compute_metrics(pred_count, gt_count, threshold=threshold)

        results.append({
            "image": item["image"],
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "matched_pairs": [[list(p), list(g)] for p, g in matched_pairs]
        })

        all_prec.append(precision)
        all_rec.append(recall)
        all_f1.append(f1)
        
        calc_precision = round(precision, 4)
        calc_recall = round(recall, 4)
        calc_f1 = round(f1, 4)

        if calc_precision > item['precision'] or calc_recall > item['recall']:
            print(f"Image: {item['image']}")
            print(f" Precision: {calc_precision:.4f}, Recall: {calc_recall:.4f}, F1: {calc_f1:.4f}")
            print(f" Matched pairs: {matched_pairs}\n")


    # Overall average pred, recall and F1
    mean_prec = sum(all_prec) / len(all_prec) if all_prec else 0.0
    mean_rec = sum(all_rec) / len(all_rec) if all_rec else 0.0
    mean_f1 = sum(all_f1) / len(all_f1) if all_f1 else 0.0

    print("===== Overall Results =====")
    print(f"Mean Precision: {mean_prec}")
    print(f"Mean Recall: {mean_rec}")
    print(f"Mean F1: {mean_f1}")
    
    results.append({
        "image": "AVERAGE",
        "precision": mean_prec,
        "recall": mean_rec,
        "F1": mean_f1
    })
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"results saved at: {save_path}")
