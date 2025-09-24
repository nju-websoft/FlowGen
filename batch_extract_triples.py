import os
from triples_parser import parse_to_triples, detect_backend
from typing import List, Tuple

Triple = Tuple[str, str, str]

def save_triples_to_txt(triples: List[Triple], output_path: str):
    with open(output_path, 'w', encoding='utf-8') as f:
        for h, r, t in triples:
            f.write(f"<{h}, {r}, {t}>\n")

def process_dataset_inplace(root_dir: str):
    for split in ['train', 'test']:
        split_dir = os.path.join(root_dir, split)
        if not os.path.isdir(split_dir):
            split_dir = root_dir
            # continue

        for backend in ['mermaid', 'graphviz', 'plantuml', 'diagrams']:
            backend_dir = os.path.join(split_dir, backend)
            if not os.path.isdir(backend_dir):
                continue

            # for scan_style in os.listdir(backend_dir):  # e.g., scanned_easy
            #     scan_dir = os.path.join(backend_dir, scan_style)
            #     if not os.path.isdir(scan_dir):
            #         continue
            scan_dir = backend_dir
            for diff in os.listdir(scan_dir):  # e.g., easy, medium, hard
                diff_dir = os.path.join(scan_dir, diff)
                if not os.path.isdir(diff_dir):
                    continue

                for file in os.listdir(diff_dir):
                    if file.endswith(('.mmd', '.dot', '.puml')):
                        file_path = os.path.join(diff_dir, file)
                        try:
                            backend_type = detect_backend(file_path)
                            triples = parse_to_triples(file_path, backend_type)

                            output_file = os.path.splitext(file)[0] + ".txt"
                            output_path = os.path.join(diff_dir, output_file)

                            save_triples_to_txt(triples, output_path)
                            print(f"[✓] {file} → {output_file} ({len(triples)} triples)")
                        except Exception as e:
                            print(f"[✗] Failed to process {file_path}: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("root_dir", type=str, help="FlowGen 数据集的根目录")
    args = parser.parse_args()

    process_dataset_inplace(args.root_dir)
