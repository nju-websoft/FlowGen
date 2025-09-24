import os
from graphviz import Digraph
import random
from interfaces import IGraphRenderer
from my_dictionary import _PRESET_COLORS
from shutil import copyfile
from graph_generator import apply_scanned_style

class GraphvizRenderer(IGraphRenderer):
    def render(self, config: dict, backend_name):
        if not isinstance(config, dict):
            raise TypeError(f"config should be of type dict, but got: {type(config)}")
        if not isinstance(config.get('graph'), dict):
            raise TypeError(f"config['graph'] should be of type dict, but got: {type(config.get('graph'))}")
        out_path = config['output']['path']
        file_root, file_ext = os.path.splitext(out_path)
        fmt = file_ext.lstrip('.') if file_ext else 'png'

        dot = Digraph(format=fmt)
        direction = random.choice(['LR', 'RL', 'TD', 'BT'])  # randomly select layout direction
        # direction = config['graph'].get('direction', 'TD')
        dot.attr(rankdir=direction)

        title = config['graph'].get('title', '')
        if title:
            print(f"[Graphviz] Title: {title}")
        description = config['graph'].get('description', '')
        if description:
            print(f"[Graphviz] Description: {description}")

        shape_map = {
            'box': 'box',
            'ellipse': 'ellipse',
            'diamond': 'diamond',
            'hexagon': 'hexagon',
            'parallelogram': 'parallelogram',
            'oval': 'oval',
            'plaintext': 'plaintext',
            'rect': 'box',
            'cylinder': 'cylinder',
            'hexagon': 'hexagon',
            'stored-data': 'box3d',
            'shield': 'Mdiamond',
            'qubit-sphere': 'oval',
            'neuron': 'octagon',
            'tensor': 'folder',
            'decision-tree': 'triangle',
            'start': 'ellipse',
            'end': 'ellipse',
            'vnode': 'box',
        }

        nodes = config['graph'].get('nodes', [])
        edges = config['graph'].get('edges', [])
        subgraphs = config['graph'].get('subgraphs', [])

        nested_node_ids = set()
        subgraph_ids = set()
        for subgraph in subgraphs:
            subgraph_ids.add(subgraph['id'])
            nested_node_ids.update(subgraph['nodes'])

        node_dict = {n['id']: n for n in nodes}

        # 1. add non-nested nodes in the main graph
        for node in nodes:
            if node['id'] not in nested_node_ids:
                self._add_node(dot, node, shape_map)

        # Predefined random color pool (hex codes, can be extended)
        subgraph_color_pool = ['#F5E8C7', '#DAF7A6', '#FFC300', '#FF5733', '#C70039', '#900C3F', '#581845',
                               '#4CAF50', '#2196F3', '#FFEB3B', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5',
                               '#00BCD4', '#009688', '#8BC34A', '#CDDC39', '#FFC107', '#FF9800', '#FF5722',
                               '#795548', '#9E9E9E', '#607D8B']

        # 2. add nested subgraphs and anchor nodes
        for subgraph_cfg in subgraphs:
            sg_id = subgraph_cfg['id']
            label = subgraph_cfg.get('label', sg_id)
            
            # randomly select a fill color
            fill_color = random.choice(_PRESET_COLORS)

            # add anchor virtual node: used to connect edges to the entire subgraph
            anchor_id = f'subgraph_anchor_{sg_id}'
            dot.node(anchor_id, label='', shape='point', width='0.01', height='0.01', style='invis')

            with dot.subgraph(name=f'cluster_{sg_id}') as sub:
                fontname = "Comic Sans MS" if subgraph_cfg.get('font') == 'handwritten' else "Helvetica"
                sub.attr(
                    label=label,
                    style='rounded,filled,dashed',  # add 'filled' style
                    color='gray50',
                    fontsize='10',
                    labelloc='t',
                    labeljust='l',
                    pencolor='gray50',
                    penwidth='1.5',
                    fillcolor=fill_color,  # set random fill color
                    fontname=fontname
                )
                for nid in subgraph_cfg['nodes']:
                    node = node_dict.get(nid)
                    if node:
                        self._add_node(sub, node, shape_map)

                for edge in edges:
                    if edge['from'] in subgraph_cfg['nodes'] and edge['to'] in subgraph_cfg['nodes']:
                        self._add_edge(sub, edge)

        # 3. add cross-subgraph edges (with anchor connections)
        for edge in edges:
            if edge['from'] in nested_node_ids and edge['to'] in nested_node_ids:
                continue  # already handled inside subgraph

            from_id = self._map_anchor(edge['from'], subgraph_ids)
            to_id = self._map_anchor(edge['to'], subgraph_ids)
            self._add_edge(dot, {**edge, 'from': from_id, 'to': to_id})

        output_dir = os.path.dirname(file_root)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        try:
            # ✅ save DOT source code on successful render
            dot_source_path = file_root + ".dot"
            with open(dot_source_path, 'w', encoding='utf-8') as f_dot:
                f_dot.write(dot.source)
            print(f"[Graphviz] DOT source saved to {dot_source_path}")
            
            if config['output'].get('render', False):
                dot.render(filename=file_root, cleanup=True, view=False)
                print(f"[Graphviz] Graph saved to {out_path}")
                
                # if scanned style is enabled
                if config['graph'].get('scanned', False):
                    # new output path: original + `_scanned` suffix
                    base, ext = os.path.splitext(out_path)
                    scanned_path = base + "_scanned" + ext

                    # copy original image (do not overwrite original)
                    copyfile(out_path, scanned_path)
                    apply_scanned_style(scanned_path, config['graph']['scanned'], backend_name)

        except Exception as e:
            print(f"[Graphviz] Error rendering graph: {e}")
            dot_source_path = file_root + ".dot"
            with open(dot_source_path, 'w', encoding='utf-8') as f_dot:
                f_dot.write(dot.source)
            print(f"[Graphviz] DOT source saved to {dot_source_path} for debugging.")


    def _map_anchor(self, node_id: str, subgraph_ids: set):
        if node_id in subgraph_ids:
            return f"subgraph_anchor_{node_id}"
        return node_id

    def _add_node(self, graph, node, shape_map):
        nid = node['id']
        label = node.get('label', nid)
        node_type = node.get('type')
        node_color = node.get('color', {})
        node_shape_cfg = node.get('shape')

        shape = shape_map.get(node_shape_cfg, 'box')
        if node_type in ['start', 'end']:
            shape = 'ellipse'

        node_attrs = {
            'label': label,
            'shape': shape,
            'style': 'filled',
        }

        if node_type in ['vnode']:
            # special tiny invisible node
            node_attrs['width'] = '0.1'
            node_attrs['height'] = '0.1'
            node_attrs['fixedsize'] = 'true'
            node_attrs['label'] = ''

        fill_color = node_color.get('fill')
        stroke_color = node_color.get('stroke')
        if fill_color:
            node_attrs['fillcolor'] = fill_color
        if stroke_color:
            node_attrs['color'] = stroke_color
            
        # ✅ set font style
        if node.get('font') == 'handwritten':
            node_attrs['fontname'] = "Comic Sans MS"  # or "Segoe Print", "Bradley Hand", "Pacifico"

        graph.node(nid, **node_attrs)

    def _add_edge(self, graph, edge):
        edge_label = edge.get('label', '')
        edge_style = edge.get('style', {})
        edge_attrs = {}

        if edge_label:
            edge_attrs['label'] = edge_label

        # extract color, width, dash style
        stroke_color = edge.get('color', {}).get('stroke', '#000000')  # default value to prevent errors
        stroke_width = edge_style.get('penwidth', '1.5px')

        # set color
        edge_attrs['color'] = stroke_color
        # set pen width (remove px unit)
        edge_attrs['penwidth'] = stroke_width.replace('px', '')
        # set edge style
        edge_attrs['style'] = edge_style.get('style', 'solid')

        # ✅ set arrow direction (default forward)
        edge_attrs['dir'] = edge_style.get('dir', 'forward')

        # ✅ set font style (optional)
        if edge.get('font') == 'handwritten':
            edge_attrs['fontname'] = "Comic Sans MS"

        # add edge
        graph.edge(edge['from'], edge['to'], **edge_attrs)
