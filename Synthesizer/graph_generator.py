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

    # 1. 模糊处理
    if config.get("blur_radius"):
        img = img.filter(ImageFilter.GaussianBlur(radius=config["blur_radius"]))

    # 2. 旋转（轻微倾斜）
    if config.get("rotation"):
        angle = np.random.uniform(-config["rotation"], config["rotation"])
        img = img.rotate(angle, expand=True, fillcolor=(255, 255, 240))

    # 3. 颜色调节 - 转为灰度 or 偏黄
    if config.get("color_tint") == "gray":
        img = img.convert("L").convert("RGB")  # 转为灰度后再转回 RGB，便于继续处理
    else:
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(0.9)  # 降低色彩饱和度
        yellow_overlay = Image.new('RGB', img.size, (255, 255, 200))
        img = Image.blend(img, yellow_overlay, alpha=0.15)
        
    # 透视扭曲
    if config.get("perspective_distortion", False):
        img_np = np.array(img)
        h, w = img_np.shape[:2]
        delta = int(min(w, h) * 0.03)  # 控制变形强度（3%以内）

        def rand_offset(p): return p + np.random.randint(-delta, delta + 1)

        # 原始坐标
        src = np.float32([
            [0, 0],
            [w, 0],
            [w, h],
            [0, h]
        ])
        # 扰动后的坐标
        dst = np.float32([
            [rand_offset(0), rand_offset(0)],
            [rand_offset(w), rand_offset(0)],
            [rand_offset(w), rand_offset(h)],
            [rand_offset(0), rand_offset(h)]
        ])

        M = cv2.getPerspectiveTransform(src, dst)
        img_np = cv2.warpPerspective(img_np, M, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 240))
        img = Image.fromarray(img_np)

    # 4. 噪声（黑点或斑点）
    if config.get("noise_level"):
        img_np = np.array(img)
        noise = np.random.rand(*img_np.shape[:2]) < config["noise_level"]
        dots = np.random.randint(80, 150, size=(noise.sum(),))  # 随机灰度斑点
        img_np[noise] = np.stack([dots]*3, axis=1)
        img = Image.fromarray(img_np)

    # 5. 晕影（需自定义生成遮罩）
    if config.get("vignette"):
        vignette_strength = config["vignette"]
        w, h = img.size
        x = np.linspace(-1, 1, w)
        y = np.linspace(-1, 1, h)
        xv, yv = np.meshgrid(x, y)
        mask = 1 - vignette_strength * (xv**2 + yv**2)
        mask = np.clip(mask, 0.5, 1)
        mask = (mask * 255).astype(np.uint8)
        mask_img = np.stack([mask]*3, axis=2)
        img_np = np.array(img)
        img = Image.fromarray((img_np * (mask_img / 255)).astype(np.uint8))

    # 6. 压缩伪影（JPEG压缩）
    if config.get("compression_level"):
        # temp_path = img_path.replace(".png", "_compressed.jpg")
        img.save(img_path, quality=config["compression_level"])
    else:
        img.save(img_path)

    print(f"[{backend_name}] 应用了扫描件风格效果: {img_path}")

def generate_letter_labels(n):
    base = LETTERS
    result = []
    for i in range(n):
        if i < len(base):
            result.append(base[i])
        else:
            result.append(base[(i // len(base)) - 1] + base[i % len(base)])
    return result


def generate_flow_config(backend_name: str, scale: str, branch: int, nest: int, density: float, split_arrow: int, merge_arrow: int, 
                         no_edge_label_ratio: float = 0.0, handwritten_style: bool = False, Scanned_style: dict = {}, domain: str = None):
    # ✅ Step 0: 随机选取一个应用领域
    if domain is None:
        domain = random.choice(APPLICATIONS)
    raw_node_names = NODE_NAMES[domain][:]
    raw_edge_labels = EDGE_LABELS[domain][:]
    # raw_edge_labels = YES_NO_EDGE_LABELS[:]
    
    arrow_edges = [
        EDGE_STYLES[backend_name]['solid_arrow'],
        # EDGE_STYLES[backend_name]['dotted_arrow'],
        EDGE_STYLES[backend_name]['dashed_arrow'],
    ]

    node_name_pool = raw_node_names[:]
    edge_label_pool = raw_edge_labels[:]
    # 改为使用逻辑动词，不影响流程图的语义信息
    # edge_label_pool = LOGIC_EDGE_LABELS[:]

    # 新增：为该领域随机选取五组颜色
    selected_palette = random.sample(PALETTE, min(3, len(PALETTE)))# 确保PALETTE中至少有5组颜色，否则取全部
    edge_palette = selected_palette + [{"fill":"#000000", "stroke":"#000000"}]
    # edge_palette = [{"fill":"#000000", "stroke":"#000000"}]

    

    
    def get_unique_label(pool: list, fallback: list) -> str:
        if not pool:
            pool.extend(fallback)
        return pool.pop(random.randint(0, len(pool) - 1))
    
    def disturb_edge_labels(edges, ratio: float):
        """扰动：从已有边中按比例移除标签"""
        if ratio <= 0 or not edges:
            return
        num_to_drop = round(ratio * len(edges))
        indices_to_drop = random.sample(range(len(edges)), num_to_drop)
        for idx in indices_to_drop:
            edges[idx]['label'] = ""

    # Step 1: 根据 scale 决定总节点数量
    total_nodes = {
        'small': random.randint(8, 12),
        'medium': random.randint(13, 20),
        'large': random.randint(20, 30)
    }.get(scale.lower(), random.randint(9, 15))

    if total_nodes < 2:
        raise ValueError("节点数过少，无法生成流程图。")

    # Step 2: 分配节点到主流程和嵌套流程
    available_nodes = total_nodes - split_arrow - merge_arrow
    nested_nodes = []
    for _ in range(nest):
        if available_nodes <= 2:
            break
        max_nest_size = min(4, available_nodes - 2)  # 预留2个主流程节点
        if max_nest_size < 2:
            break
        nest_size = random.randint(2, max_nest_size)
        nested_nodes.append(nest_size)
        available_nodes -= nest_size

    main_nodes = available_nodes
    if main_nodes < 2:
        main_nodes = 2
        while sum(nested_nodes) + main_nodes > total_nodes - split_arrow - merge_arrow and nested_nodes:
            nested_nodes.pop()

    main_node_ids = [f'N{i}' for i in range(main_nodes)]
    nested_node_groups = []
    for i, size in enumerate(nested_nodes):
        nested_node_groups.append([f'nest{i}_{j}' for j in range(size)])

    nodes = []
    edges = []

    # Step 3: 创建主流程节点
    for i, nid in enumerate(main_node_ids):
        node_type = 'start' if i == 0 else 'end' if i == len(main_node_ids) - 1 else None

        label = get_unique_label(node_name_pool, raw_node_names)
        
        # 节点名称为char
        # label = letter_labels[label_cursor]
        # label_cursor += 1   
        
        shape = random.choice(NODE_SHAPES[backend_name]['standard'])

        nodes.append({
            'id': nid,
            'label': label,
            'type': node_type,
            'color': random.choice(selected_palette), # 使用选定的颜色组
            'shape': shape,
            'font': 'handwritten' if handwritten_style else ""
        })

    # Step 4: 链式连接主流程
    for i in range(len(main_node_ids) - 1):
        edges.append({
            'from': main_node_ids[i],
            'to': main_node_ids[i+1],
            'label': get_unique_label(edge_label_pool, raw_edge_labels),
            # 'style': random.choice(list(EDGE_STYLES[backend_name].values())),
            'style': random.choice(arrow_edges),
            'color': random.choice(edge_palette),
            'font': 'handwritten' if handwritten_style else ""
        })

    # Step 5: 创建嵌套节点并连接
    for i, group in enumerate(nested_node_groups):
        for nid in group:
            label = get_unique_label(node_name_pool, raw_node_names)
            # label = letter_labels[label_cursor]
            # label_cursor += 1

            shape = random.choice(NODE_SHAPES[backend_name]['standard'])

            nodes.append({
                'id': nid,
                'label': label,
                'type': None,
                'color': random.choice(selected_palette), # 使用选定的颜色组
                'shape': shape,
                'font': 'handwritten' if handwritten_style else ""
            })

        for j in range(len(group) - 1):
            edges.append({
                'from': group[j],
                'to': group[j+1],
                'label': get_unique_label(edge_label_pool, raw_edge_labels),
                'style': random.choice(arrow_edges),
                'color': random.choice(edge_palette),
                'font': 'handwritten' if handwritten_style else ""
            })

        valid_attach = main_node_ids[1:-1] if len(main_node_ids) > 2 else main_node_ids
        valid_out = main_node_ids[1:] if len(main_node_ids) > 1 else main_node_ids

        attach_point = random.choice(valid_attach)
        out_point = random.choice(valid_out)

        edges.append({
            'from': attach_point,
            'to': group[0],
            'label': get_unique_label(edge_label_pool, raw_edge_labels),
            'style': random.choice(arrow_edges),
            'color': random.choice(edge_palette),
            'font': 'handwritten' if handwritten_style else ""
        })
        edges.append({
            'from': group[-1],
            'to': out_point,
            'label': get_unique_label(edge_label_pool, raw_edge_labels),
            'style': random.choice(arrow_edges),
            'color': random.choice(edge_palette),
            'font': 'handwritten' if handwritten_style else ""
        })

    # Step 5.5: 嵌套子图 label
    nested_groups = []
    for i, group in enumerate(nested_node_groups):
        # label = letter_labels[label_cursor]
        # label_cursor += 1

        label = get_unique_label(node_name_pool, raw_node_names)
        nested_groups.append({
            'id': f'Group{i}',
            'label': label,
            'nodes': group,
            'font': 'handwritten' if handwritten_style else ""
        })

    # Step 6: 分叉箭头节点
    for i in range(split_arrow):
        if len(main_node_ids) <= 2:
            print(f"[{backend_name}] 嵌套过多，主流程节点不足，无法连接分叉虚节点")
            break

        valid_from_ids = main_node_ids[:-2]
        if not valid_from_ids:
            break
        
        # vid = f'S{i}'
        # from_id = random.choice(main_node_ids[:-2])
        # available_targets = main_node_ids[main_node_ids.index(from_id) + 1:]
        # max_targets = len(available_targets)
        
        # target_count = random.randint(2, min(branch, max_targets))
        # v_targets = random.sample(available_targets, target_count)
        vid = f'S{i}'
        from_id = random.choice(valid_from_ids)
        from_idx = main_node_ids.index(from_id)

        # 过滤掉紧邻的下一个节点
        available_targets = [
            n for n in main_node_ids[from_idx + 1:]
            if abs(main_node_ids.index(n) - from_idx) > 1
        ]
        if len(available_targets) < 2:
            continue  # 没有足够的目标节点，跳过

        target_count = random.randint(2, min(branch, len(available_targets)))
        v_targets = random.sample(available_targets, target_count)
        
        nodes.append({
            'id': vid,
            'label': "",
            'type': 'vnode',
            # 使用选定的调色板中的颜色
            'color': random.choice(selected_palette),
            'shape': 'circle'
        })

        edges.append({
            'from': from_id,
            'to': vid,
            'label': "",
            'style': random.choice(arrow_edges),
            'color': random.choice(edge_palette),
            'font': 'handwritten' if handwritten_style else ""
        })
        for tgt in v_targets:
            edges.append({
                'from': vid,
                'to': tgt,
                'label': get_unique_label(edge_label_pool, raw_edge_labels),
                'style': random.choice(arrow_edges),
                'color': random.choice(edge_palette),
                'font': 'handwritten' if handwritten_style else ""
            })
            
    # Step 6.5: 汇聚箭头节点
    for i in range(merge_arrow):
        if len(main_node_ids) <= 2:
            print(f"[{backend_name}] 嵌套过多，主流程节点不足，无法连接汇聚虚节点")
            break

        valid_to_ids = main_node_ids[:]
        if not valid_to_ids:
            break

        # vid = f'M{i}'
        # to_id = random.choice(valid_to_ids[2:]) # 确保至少需要两个来源点
        # max_sources = main_node_ids.index(to_id)

        # source_candidates = main_node_ids[:max_sources]
        # source_count = random.randint(2, min(branch, len(source_candidates)))
        # m_sources = random.sample(source_candidates, source_count)

        vid = f'M{i}'
        to_id = random.choice(valid_to_ids)
        to_idx = main_node_ids.index(to_id)

        # 过滤掉紧邻的上一个节点
        source_candidates = [
            n for n in main_node_ids[:to_idx]
            if abs(main_node_ids.index(n) - to_idx) > 1
        ]
        if len(source_candidates) < 2:
            continue  # 至少需要两个来源点

        source_count = random.randint(2, min(branch, len(source_candidates)))
        m_sources = random.sample(source_candidates, source_count)
        
        nodes.append({
            'id': vid,
            'label': "",
            'type': 'vnode',
            # 使用选定的调色板中的颜色
            'color': random.choice(selected_palette),
            'shape': 'circle'
        })

        for src in m_sources:
            edges.append({
                'from': src,
                'to': vid,
                'label': get_unique_label(edge_label_pool, raw_edge_labels),
                'style': random.choice(arrow_edges),
                'color': random.choice(edge_palette),
                'font': 'handwritten' if handwritten_style else ""
            })

        edges.append({
            'from': vid,
            'to': to_id,
            'label': "",
            'style': random.choice(arrow_edges),
            'color': random.choice(edge_palette),
            'font': 'handwritten' if handwritten_style else ""
        })

    # Step 7: density 添加额外边
    # 排除虚节点
    real_node_ids = [node['id'] for node in nodes if node.get('type') != 'vnode']
    max_possible_edges = round(density * total_nodes)
    existing_edges_set = set((e['from'], e['to']) for e in edges)

    # 添加额外边（限制 src 和 dst 都是非虚节点，不重复，不指向 Group）
    while len(edges) < max_possible_edges:
        src = random.choice(real_node_ids)
        dst = random.choice(real_node_ids)

        # 不能自连接，不能重复
        if src != dst and (src, dst) not in existing_edges_set:
            edges.append({
                'from': src,
                'to': dst,
                'label': get_unique_label(edge_label_pool, raw_edge_labels),
                'style': random.choice(arrow_edges),
                'color': random.choice(edge_palette),
                'font': 'handwritten' if handwritten_style else ""
            })
            existing_edges_set.add((src, dst))
        
    # 边没有标签的扰动项
    disturb_edge_labels(edges, no_edge_label_ratio)

    return {
        'graph': {
            'title': f"{domain}",
            'description': f"生成了 {total_nodes} 个节点（主流程 {main_nodes}，嵌套 {len(nested_node_groups)} 个共 {sum(nested_nodes)} 节点，分叉箭头节点 {split_arrow} 个，汇聚箭头节点 {merge_arrow} 个），密度: {density}，无标签边比例: {no_edge_label_ratio}。",
            'nodes': nodes,
            'edges': edges,
            'subgraphs': nested_groups,
            'scanned': Scanned_style
        }
    }