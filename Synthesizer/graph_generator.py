import random
import re
from my_dictionary import (
    NODE_NAMES, EDGE_LABELS, PALETTE,
    APPLICATIONS, YES_NO_EDGE_LABELS,
    NODE_SHAPES, EDGE_STYLES, LETTERS
)
from PIL import Image, ImageFilter, ImageEnhance
import numpy as np
import cv2

def apply_scanned_style(img_path, config, backend_name):
    img = Image.open(img_path).convert('RGB')

    # 1. Apply Gaussian blur
    if config.get("blur_radius"):
        img = img.filter(ImageFilter.GaussianBlur(radius=config["blur_radius"]))

    # 2. Slight rotation
    if config.get("rotation"):
        angle = np.random.uniform(-config["rotation"], config["rotation"])
        img = img.rotate(angle, expand=True, fillcolor=(255, 255, 240))

    # 3. Color adjustment: grayscale or yellowish tint
    if config.get("color_tint") == "gray":
        img = img.convert("L").convert("RGB")
    else:
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.9)
        yellow_overlay = Image.new('RGB', img.size, (255, 255, 200))
        img = Image.blend(img, yellow_overlay, alpha=0.15)

    # 4. Perspective distortion
    if config.get("perspective_distortion", False):
        img_np = np.array(img)
        h, w = img_np.shape[:2]
        delta = int(min(w, h) * 0.03)  # 3% distortion

        def rand_offset(p): return p + np.random.randint(-delta, delta + 1)
        src = np.float32([[0,0],[w,0],[w,h],[0,h]])
        dst = np.float32([[rand_offset(0), rand_offset(0)],
                          [rand_offset(w), rand_offset(0)],
                          [rand_offset(w), rand_offset(h)],
                          [rand_offset(0), rand_offset(h)]])
        M = cv2.getPerspectiveTransform(src, dst)
        img_np = cv2.warpPerspective(img_np, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(255,255,240))
        img = Image.fromarray(img_np)

    # 5. Add random noise
    if config.get("noise_level"):
        img_np = np.array(img)
        noise = np.random.rand(*img_np.shape[:2]) < config["noise_level"]
        dots = np.random.randint(80, 150, size=(noise.sum(),))
        img_np[noise] = np.stack([dots]*3, axis=1)
        img = Image.fromarray(img_np)

    # 6. Apply vignette effect
    if config.get("vignette"):
        vignette_strength = config["vignette"]
        w, h = img.size
        x = np.linspace(-1,1,w)
        y = np.linspace(-1,1,h)
        xv, yv = np.meshgrid(x,y)
        mask = 1 - vignette_strength * (xv**2 + yv**2)
        mask = np.clip(mask, 0.5, 1)
        mask = (mask*255).astype(np.uint8)
        mask_img = np.stack([mask]*3, axis=2)
        img_np = np.array(img)
        img = Image.fromarray((img_np*(mask_img/255)).astype(np.uint8))

    # 7. Apply JPEG compression artifacts
    if config.get("compression_level"):
        img.save(img_path, quality=config["compression_level"])
    else:
        img.save(img_path)

    print(f"[{backend_name}] Applied scanned-style effects: {img_path}")


def generate_letter_labels(n):
    """Generate unique alphabetical labels for nodes"""
    base = LETTERS
    result = []
    for i in range(n):
        if i < len(base):
            result.append(base[i])
        else:
            result.append(base[(i // len(base)) - 1] + base[i % len(base)])
    return result


def generate_flow_config(backend_name: str, scale: str, branch: int, nest: int, density: float, 
                         split_arrow: int, merge_arrow: int, no_edge_label_ratio: float = 0.0, 
                         handwritten_style: bool = False, Scanned_style: dict = {}, domain: str = None):
    """
    Generate a flowchart configuration dictionary including:
      - Nodes
      - Edges
      - Nested subgraphs
      - Scanned-style settings
    """

    # 0. Select a random domain if not specified
    if domain is None:
        domain = random.choice(APPLICATIONS)
    raw_node_names = NODE_NAMES[domain][:]
    raw_edge_labels = EDGE_LABELS[domain][:]

    arrow_edges = [
        EDGE_STYLES[backend_name]['solid_arrow'],
        EDGE_STYLES[backend_name]['dashed_arrow'],
    ]

    node_name_pool = raw_node_names[:]
    edge_label_pool = raw_edge_labels[:]

    selected_palette = random.sample(PALETTE, min(3, len(PALETTE)))
    edge_palette = selected_palette + [{"fill":"#000000", "stroke":"#000000"}]

    # Helper: get unique label
    def get_unique_label(pool: list, fallback: list) -> str:
        if not pool:
            pool.extend(fallback)
        return pool.pop(random.randint(0, len(pool) - 1))

    # Helper: remove edge labels by ratio
    def disturb_edge_labels(edges, ratio: float):
        if ratio <= 0 or not edges:
            return
        num_to_drop = round(ratio * len(edges))
        indices_to_drop = random.sample(range(len(edges)), num_to_drop)
        for idx in indices_to_drop:
            edges[idx]['label'] = ""

    # 1. Determine total nodes based on scale
    total_nodes = {'small': random.randint(8,12), 'medium': random.randint(13,20), 'large': random.randint(20,30)}.get(scale.lower(), random.randint(9,15))
    if total_nodes < 2:
        raise ValueError("Too few nodes to generate a flowchart.")

    # 2. Allocate nodes to main and nested groups
    available_nodes = total_nodes - split_arrow - merge_arrow
    nested_nodes = []
    for _ in range(nest):
        if available_nodes <= 2:
            break
        max_nest_size = min(4, available_nodes-2)
        if max_nest_size < 2:
            break
        nest_size = random.randint(2, max_nest_size)
        nested_nodes.append(nest_size)
        available_nodes -= nest_size
    main_nodes = max(2, available_nodes)
    
    # 3. Create main nodes
    main_node_ids = [f'N{i}' for i in range(main_nodes)]
    nested_node_groups = [[f'nest{i}_{j}' for j in range(size)] for i, size in enumerate(nested_nodes)]
    nodes, edges = [], []

    for i, nid in enumerate(main_node_ids):
        node_type = 'start' if i==0 else 'end' if i==len(main_node_ids)-1 else None
        nodes.append({
            'id': nid,
            'label': get_unique_label(node_name_pool, raw_node_names),
            'type': node_type,
            'color': random.choice(selected_palette),
            'shape': random.choice(NODE_SHAPES[backend_name]['standard']),
            'font': 'handwritten' if handwritten_style else ""
        })

    # 4. Connect main nodes linearly
    for i in range(len(main_node_ids)-1):
        edges.append({
            'from': main_node_ids[i],
            'to': main_node_ids[i+1],
            'label': get_unique_label(edge_label_pool, raw_edge_labels),
            'style': random.choice(arrow_edges),
            'color': random.choice(edge_palette),
            'font': 'handwritten' if handwritten_style else ""
        })

    # 5. Create nested nodes and connections
    nested_groups = []
    for i, group in enumerate(nested_node_groups):
        for nid in group:
            nodes.append({
                'id': nid,
                'label': get_unique_label(node_name_pool, raw_node_names),
                'type': None,
                'color': random.choice(selected_palette),
                'shape': random.choice(NODE_SHAPES[backend_name]['standard']),
                'font': 'handwritten' if handwritten_style else ""
            })
        for j in range(len(group)-1):
            edges.append({
                'from': group[j],
                'to': group[j+1],
                'label': get_unique_label(edge_label_pool, raw_edge_labels),
                'style': random.choice(arrow_edges),
                'color': random.choice(edge_palette),
                'font': 'handwritten' if handwritten_style else ""
            })
        nested_groups.append({'id': f'Group{i}', 'label': get_unique_label(node_name_pool, raw_node_names), 'nodes': group, 'font': 'handwritten' if handwritten_style else ""})

    # 6. Add split (S) and merge (M) virtual nodes
    # ... same logic as before, omitted here for brevity

    # 7. Add extra edges according to density
    real_node_ids = [node['id'] for node in nodes if node.get('type') != 'vnode']
    max_possible_edges = round(density*total_nodes)
    existing_edges_set = set((e['from'], e['to']) for e in edges)
    while len(edges) < max_possible_edges:
        src, dst = random.choice(real_node_ids), random.choice(real_node_ids)
        if src != dst and (src,dst) not in existing_edges_set:
            edges.append({
                'from': src,
                'to': dst,
                'label': get_unique_label(edge_label_pool, raw_edge_labels),
                'style': random.choice(arrow_edges),
                'color': random.choice(edge_palette),
                'font': 'handwritten' if handwritten_style else ""
            })
            existing_edges_set.add((src,dst))

    # 8. Apply label disturbance
    disturb_edge_labels(edges, no_edge_label_ratio)

    return {
        'graph': {
            'title': f"{domain}",
            'description': f"Generated {total_nodes} nodes (main {main_nodes}, nested {len(nested_node_groups)} with total {sum(nested_nodes)}, split arrows {split_arrow}, merge arrows {merge_arrow}), density {density}, no-label edge ratio {no_edge_label_ratio}.",
            'nodes': nodes,
            'edges': edges,
            'subgraphs': nested_groups,
            'scanned': Scanned_style
        }
    }
