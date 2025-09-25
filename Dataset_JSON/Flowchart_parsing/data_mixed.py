import os
import random
from torch.utils.data import Dataset

class FlowchartSFTDataset(Dataset):
    def __init__(self, root_dir):
        self.samples = []
        render_name = {"mermaid": "mmd", "graphviz": "dot", "plantuml": "puml", "diagrams": "dot"}

        for renderer in os.listdir(root_dir):
            # if "mermaid" not in renderer:
            #     continue
            renderer_path = os.path.join(root_dir, renderer)
            if not os.path.isdir(renderer_path):
                continue
            scan_path = renderer_path

            for diff in os.listdir(scan_path):
                # if "medium" not in diff:
                #     continue

                base = os.path.join(scan_path, diff)
                if not os.path.isdir(base):
                    continue

                non_scanned_samples = []

                for fname in os.listdir(base):
                    if not fname.endswith(".png"):
                        continue

                    base_name = fname[:-4]
                    code_file = os.path.join(base, base_name + ".txt")
                    if not os.path.exists(code_file):
                        continue

                    with open(code_file, "r", encoding="utf-8") as f:
                        code = f.read()

                    # not scanned image
                    non_scanned_samples.append({
                        "image_path": os.path.join(base, fname),
                        "answer": code
                    })

                selected_non_scanned = non_scanned_samples

                self.samples.extend(selected_non_scanned)
                print(f"{renderer} - {diff}: non-scanned={len(selected_non_scanned)}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]