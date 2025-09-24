# FlowGen

FlowGen is a controllable flowchart synthesizer that generates diagrams with tunable structural features and supports multiple rendering styles.



## 📂 FlowGen Dataset
The [FlowGen datasets](https://huggingface.co/datasets/Sorrystopper/FlowchartBench) is publicly available on Hugging Face. It contains:
- [`train`]: 11520 samples
- [`test`]: 8640 samples

---


## 👋 Flowchart Synthesizer
We provide an automated pipeline for synthesizing flowcharts with different structural configurations. The generator supports four rendering backends:
- Mermaid  
- Graphviz  
- PlantUML  
- Diagrams  

### Configuration
Flowchart synthesis is fully customizable via [`Synthesizer/examples.yaml`](Synthesizer/examples.yaml). The following parameters are supported:

- `count`: number of flowcharts to generate  
- `order`: number of nodes  
- `split_arrow`: number of split arrows  
- `merge_arrow`: number of merge arrows  
- `branch`: maximum branching or merging factor  
- `nest`: number of nested subgraphs  
- `density`: edge-to-node ratio  

Semantic domains, node/edge names, and style definitions can be specified in [`Synthesizer/my_dictionary.py`](Synthesizer/my_dictionary.py).  

Rendering implementations for all four backends are located in [`Synthesizer/renderers/`](Synthesizer/renderers/).  



---

## 🤖 Automatic Flowchart Construction
To generate flowcharts, first configure `examples.yaml`. Then run:
```bash
python main.py examples.yaml --backend mermaid --difficulty easy --start_index 201
```
Arguments:
- --backend: specify the renderer (e.g., mermaid, graphviz, plantuml, diagrams)

- --difficulty (optional): specify structural difficulty of the graph

- --start_index: starting index for naming generated flowcharts

---

## 🛠️ Code-to-Triple Parser
This repository provides a parser that extracts structured triples from rendered flowchart code.
The parser automatically detects the backend from the file suffix.

Run the following command, where `/path/to/dataset` is the root directory of generated flowcharts:
```
python batch_extract_triples.py /path/to/datset
```
## 🔥 MLLMs Training
Fine-tuning scripts are provided for multimodal large language models (MLLMs).
After configuring your model path and dataset JSON, run:
```
cd MLLMs-SFT
cd Qwen2-VL-Finetune
bash scripts/finetune_lora_vision.sh
```
## 🚀 Inference
You can evaluate both the **base model** and the **FlowGen-SFT model** (fine-tuned on the FlowGen train split) on public flowchart datasets using **Strict F1**:
```
cd FlowGen-Eval
python eval.py --/path/to/input.json --/path/to/output.json
```
We also provide evaluation with Relaxed F1:
```
cd FlowGen-Eval
python edit_sim.py --/path/to/input.json --/path/to/output.json
```