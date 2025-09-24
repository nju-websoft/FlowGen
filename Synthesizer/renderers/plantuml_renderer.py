import os
import subprocess
import traceback
import random
from interfaces import IGraphRenderer
from my_dictionary import _PRESET_COLORS
from shutil import copyfile
from graph_generator import apply_scanned_style

class PlantUMLRenderer(IGraphRenderer):

    def _map_shape(self, shape: str, node_type: str = None):
        if node_type == 'vnode':
            return 'circle'
        shape_mapping = {
            'box': 'rectangle',
            'diamond': 'folder',
            'artifact': 'artifact',
            'ellipse': 'cloud',
            'hexagon': 'component',
            'parallelogram': 'folder',
            'oval': 'node',
            'plaintext': 'usecase',
            'cylinder': 'database',
            'box3d': 'frame'
        }
        return shape_mapping.get(shape, 'rectangle')

    def _get_node_style_plantuml_string(self, node_data: dict):
        # This method mainly handles non-color styles; color is applied inline
        style_attrs = []
        if node_data.get("roundCorner") is not None:
            style_attrs.append(f"roundCorner {node_data['roundCorner']}")
        return " ".join(style_attrs)

    def _get_inline_color_string(self, data: dict, is_group: bool = False):
        # Return inline color string for PlantUML
        color_attrs = []
        color = data.get('color', {})

        if is_group:
            # For groups, pick random color if not explicitly set
            if not color.get("fill"):
                selected_color = random.choice(_PRESET_COLORS)
                color_attrs.append(f"{selected_color.lstrip('#')}")
            else:
                color_attrs.append(f"{color['fill'].lstrip('#')}")
        else:
            # For regular nodes, use explicit fill color only
            if color.get("fill"):
                color_attrs.append(f"{color['fill'].lstrip('#')}")
        
        return f"#{' '.join(color_attrs)}" if color_attrs else ""

    def _get_edge_style_attributes(self, edge_config: dict):
        style_def = edge_config.get("style", {})
        attributes_in_bracket = []

        # Extract color
        color = edge_config.get("color", {}).get("stroke", "")
        if color:
            attributes_in_bracket.append(color)

        # Extract stroke width
        if style_def.get("stroke-width") == "3px":
            attributes_in_bracket.append("bold")

        # Map line type (affects connector)
        line_type = style_def.get("style", "solid")
        if line_type == "dotted":
            line_char = "."
        elif line_type == "dashed":
            line_char = ".."
        else:
            line_char = "-"  # default solid line

        # Arrow style (supports '-->', '<-->', '--', etc.)
        arrow_style = style_def.get("arrow", "-->")
        
        # Replace '-' in arrow template with correct line type
        plantuml_arrow = arrow_style.replace("-", line_char)

        # Build bracketed style string
        style_bracket_str = f"[{','.join(set(attributes_in_bracket))}]" if attributes_in_bracket else ""

        # Insert style string into arrow
        insert_pos = int(len(plantuml_arrow) / 2)
        if insert_pos != -1 and style_bracket_str:
            plantuml_arrow = plantuml_arrow[:insert_pos] + style_bracket_str + plantuml_arrow[insert_pos:]

        return plantuml_arrow

    def _render_group(self, group, all_nodes, defined_stereotypes, lines, indent=0):
        # Render a group (subgraph) in PlantUML
        group_type = group.get("type", "rectangle")
        group_id = group.get("id")
        group_label = group.get("label", group_id)
        inner_nodes = group.get("nodes", [])
        indent_space = "    " * indent

        # Handle inline color for group (is_group=True)
        group_puml_line_parts = [f'{indent_space}{group_type} "{group_label}" as {group_id}']
        inline_color_string = self._get_inline_color_string(group, is_group=True)
        if inline_color_string:
            group_puml_line_parts.append(inline_color_string)
        group_puml_line_parts.append("{")

        lines.append(" ".join(group_puml_line_parts))

        for nid in inner_nodes:
            node_data = next((n for n in all_nodes if n["id"] == nid), None)
            if not node_data:
                continue
            label = node_data.get('label', nid)
            node_type = node_data.get('type')
            shape = node_data.get('shape', 'rectangle')
            plantuml_shape = self._map_shape(shape, node_type)

            node_puml_line_parts = []
            if node_type == 'vnode':
                node_puml_line_parts.append(f'{indent_space}    {plantuml_shape} "" as {nid}')
            else:
                node_puml_line_parts.append(f'{indent_space}    {plantuml_shape} "{label}" as {nid}')

            # Add inline color (non-group, is_group=False)
            inline_node_color_string = self._get_inline_color_string(node_data, is_group=False)
            if inline_node_color_string:
                node_puml_line_parts.append(inline_node_color_string)

            # Handle other styles with skinparam if needed
            style_string = self._get_node_style_plantuml_string(node_data)
            if style_string:
                lines.append(f"{indent_space}    skinparam {plantuml_shape} {{")
                lines.append(f"{indent_space}        {style_string}")
                lines.append(f"{indent_space}    }}")
            
            lines.append(" ".join(node_puml_line_parts))
        lines.append(f'{indent_space}}}')

    def render(self, config: dict, jar_path: str, backend_name):
        nodes_cfg = config['graph']['nodes']
        edges_cfg = config['graph']['edges']
        subgraphs_cfg = config['graph'].get('subgraphs', [])
        direction = config['graph'].get('direction', 'TD')

        plantuml_specific_cfg = config.get('plantuml', {})
        jar_path = plantuml_specific_cfg.get('jar_path', jar_path)
        title = config['graph'].get('title', '')
        description = config['graph'].get('description', '')
        if title:
            print(f"[PlantUMLRenderer] Title: {title}")
        if description:
            print(f"[PlantUMLRenderer] Description: {description}")  

        lines = ["@startuml"]
        
        # Random direction
        direction = random.choice(['LR', 'RL', 'TB', 'BT'])
        if direction in ['LR', 'RL']: 
            lines.append("left to right direction")
        else: 
            lines.append("top to bottom direction")
        
        lines.append("skinparam defaultTextAlignment center")
        lines.append("skinparam shadowing false")
        
        # Handwritten font setting
        if nodes_cfg[0].get('font') == "handwritten":
            lines.append("!option handwritten true")  # enable handwritten mode
            lines.append('skinparam defaultFontName "Comic Sans MS"') 

        defined_stereotypes = set()
        nodes_already_in_groups = set()
        for group in subgraphs_cfg:
            self._render_group(group, nodes_cfg, defined_stereotypes, lines)
            nodes_already_in_groups.update(group.get("nodes", []))

        # Render nodes not in groups
        for node_data in nodes_cfg:
            nid = node_data['id']
            if nid in nodes_already_in_groups:
                continue
            label = node_data.get('label', nid)
            node_type = node_data.get('type')
            shape = node_data.get('shape', 'rectangle')
            plantuml_shape = self._map_shape(shape, node_type)

            node_puml_line_parts = []
            if node_type == 'vnode':
                node_puml_line_parts.append(f'{plantuml_shape} " " as {nid}')
            else:
                node_puml_line_parts.append(f'{plantuml_shape} "{label}" as {nid}')

            # Add inline color
            inline_color_string = self._get_inline_color_string(node_data, is_group=False)
            if inline_color_string:
                node_puml_line_parts.append(inline_color_string)

            # Apply other styles with skinparam if present
            style_string = self._get_node_style_plantuml_string(node_data)
            if style_string:
                lines.append(f"skinparam {plantuml_shape} {{")
                lines.append(f"    {style_string}")
                lines.append("}")
            
            lines.append(" ".join(node_puml_line_parts))

        # Render edges
        for edge in edges_cfg:
            from_id = edge['from']
            to_id = edge['to']
            label = edge.get('label', '').strip()
            style_str = self._get_edge_style_attributes(edge)
            edge_puml = f"{from_id} {style_str} {to_id}"
            if label:
                edge_puml += f" : {label}"
            lines.append(edge_puml)

        lines.append("@enduml")
        plantuml_code = '\n'.join(lines)

        # Save PlantUML code
        out_path = config['output']['path']
        output_dir = os.path.dirname(out_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        puml_path = os.path.splitext(out_path)[0] + '.puml'
        with open(puml_path, 'w', encoding='utf-8') as f:
            f.write(plantuml_code)
        print(f"[PlantUMLRenderer] PlantUML code written to {puml_path}")

        # Render PlantUML diagram if requested
        if config['output'].get('render', False):
            output_format = os.path.splitext(out_path)[1][1:] or "svg"
            cmd = ['java', '-jar', jar_path] if jar_path else ['plantuml']
            cmd.extend([f'-t{output_format}', puml_path])
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"[PlantUMLRenderer] Diagram rendered to {os.path.splitext(out_path)[0]}.{output_format}")
                else:
                    print(f"[PlantUMLRenderer] Rendering failed: {result.stderr.strip()}")
            except Exception as e:
                print(f"[PlantUMLRenderer] Error during rendering: {e}")
                print(traceback.format_exc())
                return None
            
            # Apply scanned style if enabled
            if config['graph'].get('scanned', False):
                base, ext = os.path.splitext(out_path)
                scanned_path = base + "_scanned" + ext
                copyfile(out_path, scanned_path)
                apply_scanned_style(scanned_path, config['graph']['scanned'], backend_name)  
                        
        return plantuml_code
