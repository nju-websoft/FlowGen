import re
import os
import json
import argparse
from typing import List, Tuple, Dict, Set
from collections import defaultdict

Triple = Tuple[str, str, str]

def merge_s_m_nodes(triples: List[Triple]) -> List[Triple]:
    print(f"len triples: {len(triples)}")
    in_edges = defaultdict(list)   # key: target, value: list of (source, label)
    out_edges = defaultdict(list)  # key: source, value: list of (target, label)

    for h, r, t in triples:
        if r != "partOf":
            in_edges[t].append((h, r))
            out_edges[h].append((t, r))

    to_remove = set()
    to_add = []

    candidate_nodes = set(in_edges.keys()).union(set(out_edges.keys()))
    for node in candidate_nodes:
        if not re.fullmatch(r'[SM]\d+', node):
            continue

        in_es = in_edges.get(node, [])
        out_es = out_edges.get(node, [])

        if node.startswith("S") and len(in_es) == 1 and in_es[0][1] == "connectedTo" and len(out_es) >= 2:
            src = in_es[0][0]
            for tgt, lbl in out_es:
                to_add.append((src, lbl, tgt))
                to_remove.add((node, lbl, tgt))
            to_remove.add((src, "connectedTo", node))

        elif node.startswith("M") and len(out_es) == 1 and out_es[0][1] == "connectedTo" and len(in_es) >= 2:
            tgt = out_es[0][0]
            for src, lbl in in_es:
                to_add.append((src, lbl, tgt))
                to_remove.add((src, lbl, node))
            to_remove.add((node, "connectedTo", tgt))

    cleaned_triples = [t for t in triples if t not in to_remove]
    cleaned_triples.extend(to_add)
    print(f"after merge len triples: {len(cleaned_triples)}")
    return sorted(set(cleaned_triples))


def parse_mermaid(file_path: str) -> List[Triple]:
    triples: List[Triple] = []
    node_id_to_label: Dict[str, str] = {}
    group_stack: List[str] = []
    processed_contains: Set[Tuple[str, str]] = set()

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.encode('utf-8').decode('unicode_escape')
    lines = content.splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        subgraph_start_match = re.match(r'subgraph\s+(.+)', line)
        if subgraph_start_match:
            group_name = subgraph_start_match.group(1).strip().strip('"')
            group_stack.append(group_name)
            node_id_to_label[group_name] = group_name

            if len(group_stack) > 1:
                parent = group_stack[-2]
                child = group_stack[-1]
                if (child, parent) not in processed_contains:
                    triples.append((child, "partOf", parent))
                    processed_contains.add((child, parent))
            continue

        if line == "end" and group_stack:
            group_stack.pop()
            continue

        node_def_match = re.match(
            r'(\w+)\s*[\[{(]{1,2}[/\\"]?(.+?)[/\\"]?[\])}]{1,2}\s*$',
            line
        )
        if node_def_match:
            node_id = node_def_match.group(1)
            node_label = node_def_match.group(2).strip()

            # 去掉外围的 / 或 \
            node_label = re.sub(r'^[/\\]+|[/\\]+$', '', node_label).strip()
            if not node_label:
                node_label = node_id

            node_id_to_label[node_id] = node_label

            if group_stack:
                group = group_stack[-1]
                if (node_label, group) not in processed_contains:
                    triples.append((node_label, "partOf", group))
                    processed_contains.add((node_label, group))


    edge_pattern = re.compile(r'^(\w+)\s*([-=.><]+)\s*(?:\|\s*(.*?)\s*\|)?\s*(\w+)$')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        edge_match = edge_pattern.match(line)
        if edge_match:
            src_id, connector, label, tgt_id = edge_match.groups()
            label = label.strip() if label else ""
            predicate = label if label else "connectedTo"

            src_label = node_id_to_label.get(src_id, src_id)
            tgt_label = node_id_to_label.get(tgt_id, tgt_id)

            if connector in ['-->', '==>', '-.->']:
                triples.append((src_label, predicate, tgt_label))
            elif connector == '<--':
                triples.append((tgt_label, predicate, src_label))
            elif connector == '<-->':
                triples.append((src_label, predicate, tgt_label))
                triples.append((tgt_label, predicate, src_label))
            elif connector in ['---', '-.-'] or re.fullmatch(r'-+', connector) or re.fullmatch(r'\.?\-+\.', connector):
                triples.append((src_label, predicate, tgt_label))
                triples.append((tgt_label, predicate, src_label))
            else:
                triples.append((src_label, predicate, tgt_label))
    
    return merge_s_m_nodes(triples)


def parse_graphviz(file_path: str) -> List[Triple]:
    triples: List[Triple] = []
    node_id_to_label: Dict[str, str] = {}
    processed_contains: Set[Tuple[str, str]] = set()

    current_group_id = None
    current_group_label = None

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    content = content.encode('utf-8').decode('unicode_escape')
    lines = content.splitlines()

    edge_pattern = re.compile(r'^("?[\w\d_]+"?)\s*->\s*("?[\w\d_]+"?)\s*(?:\[(.*?)\])?')
    node_pattern = re.compile(r'^("?[\w\d_]+"?)\s*\[(.*?)\]')
    subgraph_start_pattern = re.compile(r'subgraph\s+(cluster_\w+)\s*{')
    label_pattern = re.compile(r'label\s*=\s*(?:"([^"]+)"|(.+?))(?=\s+\w+\s*=|$)')

    for line in lines:
        line = line.strip()
        if not line or line.startswith('//'):
            continue

        # 进入子图
        match = subgraph_start_pattern.match(line)
        if match:
            current_group_id = match.group(1)
            current_group_label = None
            continue

        # 退出子图
        if line == "}":
            current_group_id = None
            current_group_label = None
            continue

        # 在子图范围内，持续尝试提取 label（保证即使在后几行也能获取到）
        if current_group_id:
            label_match = label_pattern.search(line)
            if label_match:
                current_group_label = label_match.group(1) or label_match.group(2)
                node_id_to_label[current_group_id] = current_group_label

        # 匹配节点
        node_match = node_pattern.match(line)
        if node_match:
            node_id, attr_str = node_match.groups()
            node_id = node_id.strip('"')

            label_match = label_pattern.search(attr_str)
            if label_match:
                label = label_match.group(1) or label_match.group(2)
                if label != '""':
                    node_id_to_label[node_id] = label
                else:
                    node_id_to_label[node_id] = node_id
            else:
                node_id_to_label[node_id] = node_id

            # 如果子图有 label，就添加 partOf 关系
            if current_group_label:
                node_label = node_id_to_label[node_id]
                if (node_label, current_group_label) not in processed_contains:
                    triples.append((node_label, "partOf", current_group_label))
                    processed_contains.add((node_label, current_group_label))
            continue

        # 匹配边
        edge_match = edge_pattern.match(line)
        if edge_match:
            src, tgt, attr_str = edge_match.groups()
            src = src.strip('"')
            tgt = tgt.strip('"')
            src_label = node_id_to_label.get(src, src)
            tgt_label = node_id_to_label.get(tgt, tgt)

            label = ""
            if attr_str:
                label_match = label_pattern.search(attr_str)
                if label_match:
                    label = label_match.group(1) or label_match.group(2)

            predicate = label if label else "connectedTo"
            triples.append((src_label, predicate, tgt_label))
            continue

    return merge_s_m_nodes(triples)



def parse_plantuml(file_path: str) -> List[Triple]:
    triples: List[Triple] = []
    edge_list: List[Tuple[str, str, str]] = []
    processed_contains: Set[Tuple[str, str]] = set()
    id_to_label: Dict[str, str] = {}
    current_group: str = None

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith('@') or line.startswith("'") or line.startswith('!') or \
           line.startswith('skinparam') or line.startswith('hide') or 'direction' in line:
            continue

        group_match = re.match(
            r'(rectangle|folder|artifact|cloud|component|frame|node|package|namespace|usecase|database)\s+"([^"]+)"\s+as\s+(\w+)', line)
        if group_match and '{' in line:
            display_name = group_match.group(2).strip()
            node_id = group_match.group(3).strip()
            current_group = display_name
            id_to_label[node_id] = display_name
            continue

        if line == "}":
            current_group = None
            continue

        node_match = re.match(
            r'(rectangle|folder|artifact|cloud|component|frame|node|package|namespace|usecase|database|circle)\s+"([^"]+)"\s+as\s+(\w+)',
            line)
        if node_match:
            display_name = node_match.group(2).strip()
            node_id = node_match.group(3).strip()
            if display_name == '':
                id_to_label[node_id] = node_id
            else:
                id_to_label[node_id] = display_name

            if current_group:
                if (display_name, current_group) not in processed_contains:
                    triples.append((display_name, "partOf", current_group))
                    processed_contains.add((display_name, current_group))
            continue

        edge_match = re.match(r'("?[\w\d_]+"?)\s*([.<\-]+)?\s*(\[#.*?\])?\s*([.\-><]+)?\s*("?[\w\d_]+"?)\s*(?::\s*(.+))?', line)
        if edge_match:
            src_raw = edge_match.group(1).strip('"')
            connector1 = edge_match.group(2) or ""
            connector2 = edge_match.group(4) or ""
            connector = connector1 + connector2
            tgt_raw = edge_match.group(5).strip('"')
            label_raw = edge_match.group(6)
            label = label_raw.strip() if label_raw else ""
            predicate = label if label else "connectedTo"

            if connector in ['-->', '....>', '..>']:
                edge_list.append((src_raw, tgt_raw, predicate))
            elif connector in ['--', '..', '<-->', '<..>', '<....>', '----', '....']:
                edge_list.append((src_raw, tgt_raw, predicate))
                edge_list.append((tgt_raw, src_raw, predicate))
            else:
                edge_list.append((src_raw, tgt_raw, predicate))
            continue

    for src, tgt, lbl in edge_list:
        src_label = id_to_label.get(src, src)
        tgt_label = id_to_label.get(tgt, tgt)
        triples.append((src_label, lbl, tgt_label))

    return merge_s_m_nodes(triples)


def parse_to_triples(file_path: str, backend: str) -> List[Triple]:
    if backend == "mermaid":
        return parse_mermaid(file_path)
    elif backend in ["graphviz", "diagrams"]:
        return parse_graphviz(file_path)
    elif backend == "plantuml":
        return parse_plantuml(file_path)
    else:
        raise ValueError(f"Unsupported backend: {backend}")


def export_triples_to_json(triples: List[Triple], output_path: str):
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump([list(t) for t in triples], f, indent=2, ensure_ascii=False)


def detect_backend(file_path: str) -> str:
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".mmd":
        return "mermaid"
    elif ext == ".dot":
        return "graphviz"
    elif ext == ".puml":
        return "plantuml"
    else:
        raise ValueError(f"Cannot detect backend from file extension: {ext}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Parse rendered code to triples")
    parser.add_argument("input_file", type=str, help="Path to input .mmd/.dot/.puml file")
    parser.add_argument("output_json", type=str, help="Path to output triples JSON file")
    parser.add_argument("--backend", type=str, choices=["mermaid", "graphviz", "plantuml", "diagrams"], help="Optional: specify backend manually")
    args = parser.parse_args()

    backend = args.backend if args.backend else detect_backend(args.input_file)
    triples = parse_to_triples(args.input_file, backend)
    export_triples_to_json(triples, args.output_json)
    print(f"[Done] Parsed {len(triples)} triples and saved at {args.output_json}")
