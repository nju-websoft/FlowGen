# mermaid_renderer.py
import os
from interfaces import IGraphRenderer  # 相对导入
import random
from shutil import copyfile
from graph_generator import apply_scanned_style

class MermaidRenderer(IGraphRenderer):
    def render(self, config: dict, backend_name):
        # 添加仿手写样式定义（仅对 class="handwritten" 的元素生效）
        handwritten_class_def = '    classDef handwritten font-family:Comic Sans MS,font-size:14px,color:#2b2b2b;'
        
        nodes_cfg = config['graph']['nodes']
        edges_cfg = config['graph']['edges']
        subgraphs_cfg = config['graph'].get('subgraphs', []) 
        # direction = config['graph'].get('direction', 'TD')
        direction = random.choice(['LR', 'RL', 'TD', 'BT'])  # 随机选择方向

        lines = [f"graph {direction}"]

        title = config['graph'].get('title', '')
        description = config['graph'].get('description', '')
        if title:
            print(f"[Mermaid] Title: {title}")
        if description:
            print(f"[Mermaid] Description: {description}")

        # Mermaid 形状映射
        shape_map = {
            'box': ('[', ']'),
            'round': ('(', ')'),
            'stadium': ('([', '])'),
            'subroutine': ('[[', ']]'),
            'cylindrical': ('[(', ')]'),
            'circle': ('((', '))'),
            'asymmetric': ('(', ')'), 
            'rhombus': ('{', '}'),
            'parallelogram': ('[/', '/]'),
            'reverse_parallemlogram': ("[\\","\\]")
        }

        style_defs = []
        link_style_defs = [] # 用于存储边的样式定义
        processed_nodes = set() 

        # 缓存所有节点，方便按ID查找
        node_lookup = {node['id']: node for node in nodes_cfg}
        
        # 获取最小和最大 node id（假设 id 格式为 N<number>）
        node_ids_sorted = sorted(nodes_cfg, key=lambda n: int(''.join(filter(str.isdigit, n['id']))))
        start_node_id = node_ids_sorted[0]['id']
        end_node_id = node_ids_sorted[-1]['id']

        rename_prob = 0.4  # 40% 概率改名
        remove_all_colors = random.random() < 0.3  # 30% 概率全局去掉颜色
        
        # Step 1: 处理主流程节点和虚节点
        for node in nodes_cfg:
            nid = node['id']

            is_nested_node = any(nid in sg['nodes'] for sg in subgraphs_cfg)
            if is_nested_node:
                continue

            # 虚节点（小圆圈无文字）
            if node.get('type') == 'vnode':
                lines.append(f"    {nid}(( ))")
                processed_nodes.add(nid)
                node_color = node.get('color')
                if node_color:
                    fill = node_color.get('fill')
                    stroke = node_color.get('stroke')
                    # 虚节点可能只有边框颜色，确保 fill 和 stroke 都有值
                    fill_str = f"fill:{fill}" if fill else ""
                    stroke_str = f"stroke:{stroke}" if stroke else ""
                    style_props = ','.join(filter(None, [fill_str, stroke_str]))
                    if style_props:
                        style_defs.append(f"    style {nid} {style_props}")
                continue
            
            if nid == start_node_id:
                node['shape'] = 'stadium'
                # 如果 remove_all_colors，强制是 start
                if remove_all_colors:
                    node['label'] = 'start'
                elif random.random() < rename_prob:
                    node['label'] = 'start'
            elif nid == end_node_id:
                node['shape'] = 'stadium'
                if remove_all_colors:
                    node['label'] = 'end'
                elif random.random() < rename_prob:
                    node['label'] = 'end'
            
            # 普通主节点
            label = node.get('label', nid)
            shape = node.get('shape', 'box') 
            shape_open, shape_close = shape_map.get(shape, ('[', ']'))
            
            lines.append(f"    {nid}{shape_open}{label}{shape_close}")
            if node.get('font') == 'handwritten':
                lines.append(f"    class {nid} handwritten")

            processed_nodes.add(nid)

            if not remove_all_colors:
                node_color = node.get('color')
            else:
                node_color = None
            if node_color:
                fill = node_color.get('fill')
                stroke = node_color.get('stroke')
                fill_str = f"fill:{fill}" if fill else ""
                stroke_str = f"stroke:{stroke}" if stroke else ""
                style_props = ','.join(filter(None, [fill_str, stroke_str]))
                if style_props:
                    style_defs.append(f"    style {nid} {style_props}")

        # Step 2: 处理嵌套子图
        for subgraph_data in subgraphs_cfg:
            subgraph_id = subgraph_data['id']
            subgraph_label = subgraph_data.get('label', f"子图_{subgraph_id}")
            subgraph_nodes = subgraph_data['nodes']
            
            lines.append(f"    subgraph {subgraph_label}")
            for nid in subgraph_nodes:
                node = node_lookup.get(nid)
                if not node:
                    print(f"[Mermaid] 警告: 子图 '{subgraph_id}' 中存在未找到的节点ID: {nid}")
                    continue
                
                label = node.get('label', nid)
                shape = node.get('shape', 'box')
                shape_open, shape_close = shape_map.get(shape, ('[', ']'))
                
                lines.append(f"        {nid}{shape_open}{label}{shape_close}")
                if node.get('font') == 'handwritten':
                    lines.append(f"    class {nid} handwritten")

                processed_nodes.add(nid) 

                if not remove_all_colors:
                    node_color = node.get('color')
                else:
                    node_color = None
                if node_color:
                    fill = node_color.get('fill')
                    stroke = node_color.get('stroke')
                    fill_str = f"fill:{fill}" if fill else ""
                    stroke_str = f"stroke:{stroke}" if stroke else ""
                    style_props = ','.join(filter(None, [fill_str, stroke_str]))
                    if style_props:
                        style_defs.append(f"    style {nid} {style_props}")
            lines.append("    end")

        # Step 3: 添加边连接和边样式
        for i, edge in enumerate(edges_cfg): # 遍历边时获取索引
            source = edge['from']
            target = edge['to']
            
            if source not in processed_nodes and source not in node_lookup:
                 print(f"[Mermaid] 警告: 边源节点 '{source}' 未被渲染或不存在于节点列表中。")
                 continue
            if target not in processed_nodes and target not in node_lookup:
                 print(f"[Mermaid] 警告: 边目标节点 '{target}' 未被渲染或不存在于节点列表中。")
                 continue
                 
            label = edge.get('label', '')
            
            if remove_all_colors and label != '':
                label = random.choice(["yes", "no"])                
                
            edge_color = edge.get('color', "")['stroke'] # 获取边的颜色

            # 根据边的样式选择 Mermaid 的连接符
            arrow_symbol = edge.get('style', {})['style']

            if label:
                lines.append(f"    {source} {arrow_symbol} |{label}| {target}")
            else:
                lines.append(f"    {source} {arrow_symbol} {target}")

            style_props = [
                f"stroke:{edge_color}",
                "stroke-width:2px",
                "fill:none"
            ]

            if edge.get('font') == 'handwritten':
                style_props.append("font-family:'Comic Sans MS'")
                style_props.append("font-size:12px")

            # ✅ 拼接时要注意加分号；结尾也要加上分号
            link_style_defs.append(f"    linkStyle {i} {','.join(style_props)};")



        style_defs.append(handwritten_class_def)
        # 添加节点样式定义
        lines.extend(style_defs)

        # 添加边样式定义
        lines.extend(link_style_defs)

        mermaid_code = '\n'.join(lines)
        out_path = config['output']['path']
        output_dir = os.path.dirname(out_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        mmd_path = os.path.splitext(out_path)[0] + '.mmd'
        with open(mmd_path, 'w', encoding='utf-8') as f:
            f.write(mermaid_code)

        print(f"[Mermaid] Mermaid code written to {mmd_path}")

        if config['output'].get('render', False):
            os.system(f'mmdc -i "{mmd_path}" -o "{out_path}" --scale 2.5 --width 2000')
            # os.system(f'mmdc -i "{mmd_path}" -o "{out_path}"')
            print(f"[Mermaid] Rendered image to {out_path}")
            
            # 如果启用了扫描风格
            if config['graph'].get('scanned', False):
                # 新建输出路径：原路径加 `_scanned` 后缀
                base, ext = os.path.splitext(out_path)
                scanned_path = base + "_scanned" + ext

                # 拷贝原图（因为我们不覆盖原图）
                copyfile(out_path, scanned_path)
                apply_scanned_style(scanned_path, config['graph']['scanned'], backend_name)