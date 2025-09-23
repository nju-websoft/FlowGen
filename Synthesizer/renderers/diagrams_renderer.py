import os
import random
import subprocess
from diagrams import Diagram, Cluster, Edge
from diagrams.programming.flowchart import (
    InputOutput, Action, PredefinedProcess,
    Database, MultipleDocuments, Preparation, Document,
    Decision,Display,Inspection,InternalStorage,
    LoopLimit,ManualLoop,ManualInput,StartEnd
)
from interfaces import IGraphRenderer
from shutil import copyfile
from graph_generator import apply_scanned_style

SHAPE_MAP = {
    "inputoutput": InputOutput,
    "action": Action,
    "predefinedprocess": PredefinedProcess,
    "database": Database,
    "multipledocuments": MultipleDocuments,
    "preparation": Preparation,
    "document": Document,
    "box": Decision,
    "rect": Display,
    "rectangle": InternalStorage,
    "ellipse": LoopLimit,
    "diamond": ManualLoop,
    "hexagon": ManualInput,
    "parallelogram": StartEnd,
    "circle": Inspection,
    "vnode_shape": Inspection
}
def generate_dot_source(config, direction):
    nodes_cfg = config['graph']['nodes']
    edges_cfg = config['graph']['edges']
    subgraphs_cfg = config['graph'].get('subgraphs', [])

    lines = [f'digraph {{', f'\trankdir={direction}']

    group_to_nodes = {}

    # 建立一个 id -> node_config 的索引字典
    id_to_node = {node['id']: node for node in nodes_cfg}

    # 记录每个 group 下的节点 ID
    for subgraph in subgraphs_cfg:
        group = subgraph.get('label')
        for node_id in subgraph['nodes']:
            group_to_nodes.setdefault(group, []).append(node_id)

    # 记录所有已处理节点 ID
    for node_id, node in id_to_node.items():
        if "nest" in node_id:
            continue
        label = node.get('label', node_id)
        color = node.get('color', {}).get('stroke', '#000000')
        fillcolor = node.get('color', {}).get('fill', '#FFFFFF')
        shape = node.get('shape', 'ellipse')

        fixedsize_attrs = ''
        if node.get("type") == "vnode":
            fixedsize_attrs = ' fixedsize=true height=0.1 width=0.1'
            label = ''
            shape = 'circle'

        line = f'\t{node_id} [label="{label}" color="{color}" fillcolor="{fillcolor}" shape={shape} style=filled{fixedsize_attrs}]'
        lines.append(line)
    

    # 输出子图结构
    for group, node_ids in group_to_nodes.items():
        if group:
            lines.append(f'\tsubgraph cluster_{group} {{')
            lines.append(f'\t\tstyle="rounded,filled,dashed"')
            lines.append(f'\t\tcolor=gray50')
            lines.append(f'\t\tlabel="{group}"')
        
        for node_id in node_ids:
            node = id_to_node.get(node_id)
            if not node:
                continue

            label = node.get('label', node_id)
            color = node.get('color', {}).get('stroke', '#000000')
            fillcolor = node.get('color', {}).get('fill', '#FFFFFF')
            shape = node.get('shape', 'ellipse')

            fixedsize_attrs = ''
            if node.get("type") == "vnode":  # 虚节点
                fixedsize_attrs = ' fixedsize=true height=0.1 width=0.1'
                label = ''
                shape = 'circle'

            line = f'\t\t{node_id} [label="{label}" color="{color}" fillcolor="{fillcolor}" shape={shape} style=filled{fixedsize_attrs}]'
            lines.append(line)

        if group:
            lines.append('\t}')

    # 处理边定义
    for edge in edges_cfg:
        src = edge['from']
        tgt = edge['to']
        label = edge.get('label', '')
        style = edge['style']
        color = edge.get('color', '#000000')['stroke']
        penwidth = style.get('penwidth', 1.5)
        style_val = style.get('style', 'solid')
        dir_val = style.get('dir', 'forward')

        edge_base = f'{src} -> {tgt} [color="{color}" penwidth={penwidth} style={style_val}'
        if label:
            edge_base += f' label="{label}"'
        edge_base += f' dir={dir_val}'
        edge_base += ']'

        lines.append(f'\t{edge_base}')

    lines.append('}')
    return '\n'.join(lines)



class DiagramsRenderer(IGraphRenderer):
    def render(self, config: dict, backend_name):
        out_path = config['output']['path']
        file_root_no_ext = os.path.splitext(out_path)[0]

        # svg 渲染有问题，强制渲染成png
        # fmt = file_ext.lstrip('.') if file_ext else 'svg'
        fmt = 'png'
        out_path = out_path.split(".")[0] + f".{fmt}"
        
        output_dir = os.path.dirname(file_root_no_ext)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        nodes_cfg = config['graph']['nodes']
        edges_cfg = config['graph']['edges']
        subgraphs_cfg = config['graph'].get('subgraphs', [])

        title = config['graph'].get('title', '')
        description = config['graph'].get('description', '')
        if title:
            print(f"[Diagrams] Title: {title}")
        if description:
            print(f"[Diagrams] Description: {description}")
            
        fontname = "Comic Sans MS" if nodes_cfg[0].get('font') == 'handwritten' else "Helvetica"

        graph_attrs = {
            "splines": "polyline",
            "fontname": fontname,
            "fontsize": "10",
            "fontcolor": "black",
            "labelloc": "t",
            "label": "",
            "dpi": "120",
        }
        node_attr = {"style": "solid", "fontsize": "10", "labelloc": "c", 'fontname': fontname,}

        direction = random.choice(['LR', 'RL', 'TB', 'BT'])  # 随机选择方向
        graph_attrs['rankdir'] = direction

        try:
            original_cwd = os.getcwd()
            # if output_dir:
            #     os.chdir(output_dir)
            #     diagram_filename = os.path.basename(file_root_no_ext)
            # else:
            #     diagram_filename = file_root_no_ext

            dot_path = os.path.join(output_dir, os.path.basename(file_root_no_ext))
            with Diagram(outformat=fmt, filename=dot_path, show=False,
                         graph_attr=graph_attrs, node_attr=node_attr, direction=direction,) as diag:

                node_refs = {}
                node_to_subgraph_map = {}
                for subgraph in subgraphs_cfg:
                    for node_id in subgraph['nodes']:
                        node_to_subgraph_map[node_id] = subgraph['id']

                cluster_instances = {}
                for subgraph in subgraphs_cfg:
                    cluster_instances[subgraph['id']] = Cluster(subgraph['label'])

                # 创建所有节点
                for node_data in nodes_cfg:
                    node_id = node_data['id']
                    label = node_data.get('label', node_id)
                    node_type = node_data.get('type')
                    color = node_data.get('color', {})
                    fillcolor = color.get('fill', '#FFFFFF')
                    strokecolor = color.get('stroke', '#000000')

                    if node_type == 'vnode':
                        shape_cls = SHAPE_MAP.get('vnode_shape')
                        node_style_attrs = {
                            "fillcolor": "#FFFFFF",
                            "style": "dashed",
                            "shape": "point",
                            # "style": "invis",  # 完全不显示
                            "color": "#888888",
                            "height": "0.1",
                            "width": "0.1",
                            "fixedsize": "true",
                        }
                        node_label_for_diagrams = ''
                    else:
                        shape = node_data.get('shape', 'action').lower()
                        shape_cls = SHAPE_MAP.get(shape, Action)
                        node_style_attrs = {
                            "fillcolor": fillcolor,
                            "color": strokecolor,
                        }
                        node_label_for_diagrams = label

                        if node_type == 'start':
                            node_style_attrs["fillcolor"] = "#D4EDDA"
                            node_style_attrs["color"] = "#28A745"
                        elif node_type == 'end':
                            node_style_attrs["fillcolor"] = "#F8D7DA"
                            node_style_attrs["color"] = "#DC3545"

                    if nodes_cfg[0].get('font') == 'handwritten':
                        node_style_attrs["fontname"] = fontname 
                    if node_id in node_to_subgraph_map:
                        subgraph_id = node_to_subgraph_map[node_id]
                        with cluster_instances[subgraph_id]:
                            node_refs[node_id] = shape_cls(
                                node_label_for_diagrams,
                                **node_style_attrs
                            )
                    else:
                        node_refs[node_id] = shape_cls(
                            node_label_for_diagrams,
                            **node_style_attrs
                        )

        
                # 添加边
                for edge in edges_cfg:
                    src_id = edge['from']
                    tgt_id = edge['to']
                    label = edge.get('label', '')
                    edge_style = edge['style']  # 此处应是一个字典，如 {'style': 'dotted', 'penwidth': '1.5', 'dir': 'both'}
                    
                    edge_attrs_for_edge_obj = {
                        "fontsize": "10",
                        "fontname": fontname,
                        "color": edge['color']['stroke'],  # 默认颜色
                        "style": edge_style.get('style', 'solid'),
                        "penwidth": edge_style.get('penwidth', '1.5'),
                    }

                    # 特殊样式处理：highlight
                    if edge_style.get('style') == 'highlight':
                        edge_attrs_for_edge_obj['color'] = '#FF4081'
                        edge_attrs_for_edge_obj['penwidth'] = '2'

                    if label:
                        edge_attrs_for_edge_obj['label'] = label

                    if src_id in node_refs and tgt_id in node_refs:
                        # 处理箭头方向
                        dir_type = edge_style.get('dir', 'forward')

                        if dir_type == 'both' or dir_type == 'none':
                            # 双向连接，用两条边模拟
                            node_refs[src_id] >> Edge(**edge_attrs_for_edge_obj) >> node_refs[tgt_id]
                            node_refs[tgt_id] >> Edge(**edge_attrs_for_edge_obj) >> node_refs[src_id]
                        else:  # forward 或默认
                            node_refs[src_id] >> Edge(**edge_attrs_for_edge_obj) >> node_refs[tgt_id]
                    else:
                        print(f"[Warning] 无法连接边：{src_id} -> {tgt_id} (节点未找到)")

                                    
            dot_source = generate_dot_source(config, direction=direction)
            with open(f"{dot_path}.dot", "w") as f:
                f.write(dot_source)
            print(f"[Diagrams] Custom DOT source saved to: {dot_path}.dot")
            
            print(f"[Diagrams] Graph saved to: {out_path}")
            
            # 如果启用了扫描风格
            if config['graph'].get('scanned', False):
                # 新建输出路径：原路径加 `_scanned` 后缀
                base, ext = os.path.splitext(out_path)
                scanned_path = base + "_scanned" + ext

                # 拷贝原图（因为我们不覆盖原图）
                copyfile(out_path, scanned_path)
                apply_scanned_style(scanned_path, config['graph']['scanned'], backend_name)

        except Exception as e:
            print(f"[Diagrams] Error rendering graph: {e}")
            if output_dir:
                os.chdir(original_cwd)
                

