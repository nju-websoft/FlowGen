# mermaid_renderer.py
import os
from interfaces import IGraphRenderer  # relative import
import random
from shutil import copyfile
from graph_generator import apply_scanned_style

class MermaidRenderer(IGraphRenderer):
    def render(self, config: dict, backend_name):
        # Add handwritten style definition (only works for elements with class="handwritten")
        handwritten_class_def = '    classDef handwritten font-family:Comic Sans MS,font-size:14px,color:#2b2b2b;'
        
        nodes_cfg = config['graph']['nodes']
        edges_cfg = config['graph']['edges']
        subgraphs_cfg = config['graph'].get('subgraphs', []) 
        # direction = config['graph'].get('direction', 'TD')
        direction = random.choice(['LR', 'RL', 'TD', 'BT'])  # randomly choose direction

        lines = [f"graph {direction}"]

        title = config['graph'].get('title', '')
        description = config['graph'].get('description', '')
        if title:
            print(f"[Mermaid] Title: {title}")
        if description:
            print(f"[Mermaid] Description: {description}")

        # Mermaid shape mapping
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
        link_style_defs = []  # used to store edge style definitions
        processed_nodes = set() 

        # cache all nodes for quick lookup by ID
        node_lookup = {node['id']: node for node in nodes_cfg}
        
        # get smallest and largest node id (assuming id format is N<number>)
        node_ids_sorted = sorted(nodes_cfg, key=lambda n: int(''.join(filter(str.isdigit, n['id']))))
        start_node_id = node_ids_sorted[0]['id']
        end_node_id = node_ids_sorted[-1]['id']

        rename_prob = 0.4  # 40% chance to rename
        remove_all_colors = random.random() < 0.3  # 30% chance to remove all colors
        
        # Step 1: process main nodes and virtual nodes
        for node in nodes_cfg:
            nid = node['id']

            is_nested_node = any(nid in sg['nodes'] for sg in subgraphs_cfg)
            if is_nested_node:
                continue

            # virtual node (small circle without text)
            if node.get('type') == 'vnode':
                lines.append(f"    {nid}(( ))")
                processed_nodes.add(nid)
                node_color = node.get('color')
                if node_color:
                    fill = node_color.get('fill')
                    stroke = node_color.get('stroke')
                    # ensure both fill and stroke are handled
                    fill_str = f"fill:{fill}" if fill else ""
                    stroke_str = f"stroke:{stroke}" if stroke else ""
                    style_props = ','.join(filter(None, [fill_str, stroke_str]))
                    if style_props:
                        style_defs.append(f"    style {nid} {style_props}")
                continue
            
            if nid == start_node_id:
                node['shape'] = 'stadium'
                # if remove_all_colors, force label to "start"
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
            
            # normal node
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

        # Step 2: process nested subgraphs
        for subgraph_data in subgraphs_cfg:
            subgraph_id = subgraph_data['id']
            subgraph_label = subgraph_data.get('label', f"Subgraph_{subgraph_id}")
            subgraph_nodes = subgraph_data['nodes']
            
            lines.append(f"    subgraph {subgraph_label}")
            for nid in subgraph_nodes:
                node = node_lookup.get(nid)
                if not node:
                    print(f"[Mermaid] Warning: Node ID '{nid}' not found in subgraph '{subgraph_id}'.")
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

        # Step 3: add edges and edge styles
        for i, edge in enumerate(edges_cfg):  # get index when iterating edges
            source = edge['from']
            target = edge['to']
            
            if source not in processed_nodes and source not in node_lookup:
                 print(f"[Mermaid] Warning: Edge source '{source}' not rendered or missing in node list.")
                 continue
            if target not in processed_nodes and target not in node_lookup:
                 print(f"[Mermaid] Warning: Edge target '{target}' not rendered or missing in node list.")
                 continue
                 
            label = edge.get('label', '')
            
            if remove_all_colors and label != '':
                label = random.choice(["yes", "no"])                
                
            edge_color = edge.get('color', "")['stroke']  # get edge color

            # choose Mermaid arrow symbols based on edge style
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

            # ✅ make sure to append semicolon
            link_style_defs.append(f"    linkStyle {i} {','.join(style_props)};")

        style_defs.append(handwritten_class_def)
        # add node style definitions
        lines.extend(style_defs)

        # add edge style definitions
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
            
            # apply scanned style if enabled
            if config['graph'].get('scanned', False):
                # create new output path: add `_scanned` suffix
                base, ext = os.path.splitext(out_path)
                scanned_path = base + "_scanned" + ext

                # copy original image (do not overwrite original)
                copyfile(out_path, scanned_path)
                apply_scanned_style(scanned_path, config['graph']['scanned'], backend_name)
