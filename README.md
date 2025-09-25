# 🌟 FlowGen: FlowGen: Synthesizing Diverse Flowcharts to Enhance and Benchmark MLLM Reasoning

FlowGen is a controllable flowchart synthesizer that synthesizes diagrams with tunable structural features and supports multiple rendering styles.



## 📂 FlowGen Dataset
The [FlowGen datasets](https://huggingface.co/datasets/Sorrystopper/FlowGen) is publicly available on Hugging Face. It contains:
- [`train`]: 11520 samples with gold-standard triplet
- [`test`]: 8640 samples with gold-standard triplet

Each dataset sample includes:

- Rendered flowchart images (PNG)
- Flowchart render code in different renderers (Mermaid, Graphviz, PlantUML, Diagrams)

- Structured triplets <node, label, node> representing graph topology

This dataset is primarily designed for flowchart parsing and flowchart question answering (flowchart QA) research, while also supporting MLLMs training and test graph-based reasoning tasks.

### 📥 Download and Local Setup
1. Download the FlowGen dataset from Hugging Face: [FlowGen](https://huggingface.co/datasets/Sorrystopper/FlowGen).  
2. Place the downloaded dataset into a local folder named `Dataset`. In this folder, we provide six preprocessed open-source JSON datasets for flowchart parsing. You can process our FlowGen dataset in the same JSON format.
3. For convenience, pre-processing scripts are provided in [./Dataset-JSON](./Dataset-JSON/) to convert training and test samples into JSON format with specified task prompts.  
   - You can run these scripts to generate JSON files that ready for training or evaluation.

---


## 👋 Flowchart Synthesizer
We provide an automated pipeline for synthesizing flowcharts with different structural configurations. The synthesizer supports four rendering backends:
- [`Mermaid`](https://mermaid-js.github.io/), [`Graphviz`](https://graphviz.org/), [`PlantUML`](https://plantuml.com/), [`Diagrams`](https://diagrams.mingrammer.com/)

---

#### 💻 Local Renderer Installation

Install all required renderers for local flowchart rendering:

```bash
# Mermaid CLI (requires Node.js)
npm install -g @mermaid-js/mermaid-cli

# Graphviz
sudo apt install graphviz # Linux
brew install graphviz # macOS
# Windows: download installer from https://graphviz.org/download/

# PlantUML (requires Java)
brew install plantuml       # macOS
sudo apt install default-jre # Linux
# Or download PlantUML jar from https://plantuml.com/download

# Diagrams (Python package)
pip install diagrams
```
---

#### ⚙️ Configuration
Flowchart synthesis is fully customizable via [`Synthesizer/examples.yaml`](Synthesizer/examples.yaml). The following parameters are supported:

- `count`: number of flowcharts to synthesize  
- `order`: number of nodes  
- `split_arrow`: number of split arrows  
- `merge_arrow`: number of merge arrows  
- `branch`: maximum branching or merging factor  
- `nest`: number of nested subgraphs  
- `density`: edge-to-node ratio  

Semantic domains, node/edge names and shapes, and style/color definitions can be specified in [`Synthesizer/my_dictionary.py`](Synthesizer/my_dictionary.py).  

Rendering implementations for all four backends are located in [`Synthesizer/renderers/`](Synthesizer/renderers/).  



---

## 🤖 Automatic Flowchart Construction
To synthesize flowcharts, please first configure `examples.yaml`. Then run:
```bash
python main.py examples.yaml --backend mermaid --difficulty easy --scanned_style_difficulty easy --start_index 201
```
Arguments:
- --backend (optional): specify the renderer (e.g., mermaid, graphviz, plantuml, diagrams)

- --difficulty (optional): specify structural difficulty of the graph

- --scanned_style_difficulty (optional): specify scanned-style difficulty of the graph

- --start_index (optional): starting index for naming synthesized flowcharts



<!-- ###   -->
#### 🛠️ Code-to-Triplet Parser
This repository provides a parser that extracts structured triplet <node, label, node> from rendered flowchart code.
The parser automatically detects the backend from the file suffix.

Run the following command, where `/path/to/dataset` is the root directory of synthesized flowcharts:
```bash
python batch_extract_triples.py /path/to/datset
```
The extracted triplets can be used directly for model training and test.

---

## 🔥 MLLMs Training
Fine-tuning scripts are provided for multimodal large language models (MLLMs).
After configuring your model path and path to dataset in json format, run:
```bash
cd ./MLLMs-SFT/Qwen2-VL-Finetune
bash scripts/finetune_lora_vision.sh
```
## 🚀 MLLMs Testing
#### ⚡ Inference Framework
We conduct inference for MLLMs using [Swift](https://swift.readthedocs.io/en/v3.6/), with [vLLM](https://github.com/vllm-project/vllm) as the backend for efficient acceleration.  
For detailed usage and configuration, please refer to the official documentation.

You may also check the provided script for a practical example:  
[`FlowGen-Eval/inference.sh`](FlowGen-Eval/inference.sh)

---

You can evaluate both the **base model** and the **FlowGen-SFT model** (fine-tuned on the FlowGen train split) on public flowchart datasets using **Strict F1**:
```bash
cd FlowGen-Eval
python eval.py --/path/to/input.json --/path/to/output.json
```
We also provide evaluation with **Relaxed F1**:
```bash
cd FlowGen-Eval
python edit_sim.py --/path/to/input.json --/path/to/output.json
```