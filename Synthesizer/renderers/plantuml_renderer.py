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
        # 此方法现在主要用于处理非颜色样式，颜色将直接内联
        style_attrs = []
        if node_data.get("roundCorner") is not None:
            style_attrs.append(f"roundCorner {node_data['roundCorner']}")
        return " ".join(style_attrs)

    def _get_inline_color_string(self, data: dict, is_group: bool = False): # 增加 is_group 参数
        color_attrs = []
        color = data.get('color', {})

        if is_group:
            # 如果是组，且没有显式指定颜色，则随机选择
            if not color.get("fill"):
                selected_color = random.choice(_PRESET_COLORS)
                color_attrs.append(f"{selected_color.lstrip('#')}") # PlantUML 内联颜色不需要 #
            else:
                color_attrs.append(f"{color['fill'].lstrip('#')}") # 使用显式指定的颜色
        else:
            # 对于非组（普通节点），只使用显式指定的颜色
            if color.get("fill"):
                color_attrs.append(f"{color['fill'].lstrip('#')}")
        
        # PlantUML 内联颜色不需要 # 前缀，但为了与之前的实现保持一致，这里仍然保留，
        # 实际 PlantUML 通常是 `object #COLOR`，而不是 `object "#COLOR"`
        return f"#{' '.join(color_attrs)}" if color_attrs else ""


    def _get_edge_style_attributes(self, edge_config: dict):
        style_def = edge_config.get("style", {})
        attributes_in_bracket = []

        # 提取颜色
        color = edge_config.get("color", {}).get("stroke", "")
        if color:
            attributes_in_bracket.append(color)

        # 提取线宽
        if style_def.get("stroke-width") == "3px":
            attributes_in_bracket.append("bold")

        # 线条类型映射（决定连接符）
        line_type = style_def.get("style", "solid")
        if line_type == "dotted":
            line_char = "."
        elif line_type == "dashed":
            line_char = ".."
        else:
            line_char = "-"  # 默认实线

        # 箭头方向符号（支持 '-->', '<-->', '--' 等）
        arrow_style = style_def.get("arrow", "-->")
        
        # 将箭头模板中的 '-' 替换成对应线型字符（如 '.' 或 '..'）
        # 例如 '<-->' 变成 '<....>'
        plantuml_arrow = arrow_style.replace("-", line_char)

        # 拼接括号属性
        style_bracket_str = f"[{','.join(set(attributes_in_bracket))}]" if attributes_in_bracket else ""

        # 在箭头中插入样式括号（例如 '--[red]-->'）
        # 找到中间插入位置（第一个箭头符号位置）
        # insert_pos = plantuml_arrow.find(line_char, 1)  # 避免开头 < 的位置
        # if plantuml_arrow[0] == "<":
        insert_pos = int(len(plantuml_arrow) / 2 )
        if insert_pos != -1 and style_bracket_str:
            plantuml_arrow = plantuml_arrow[:insert_pos] + style_bracket_str + plantuml_arrow[insert_pos:]

        return plantuml_arrow


    def _render_group(self, group, all_nodes, defined_stereotypes, lines, indent=0):
        group_type = group.get("type", "rectangle")
        group_id = group.get("id")
        group_label = group.get("label", group_id)
        inner_nodes = group.get("nodes", [])
        indent_space = "    " * indent

        # 处理组的内联颜色，调用时传入 is_group=True
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

            # 添加节点内联颜色（非组，所以 is_group=False）
            inline_node_color_string = self._get_inline_color_string(node_data, is_group=False)
            if inline_node_color_string:
                node_puml_line_parts.append(inline_node_color_string)

            # 处理其他样式，可能需要 skinparam
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
            print(f"[Mermaid] Title: {title}")
        if description:
            print(f"[Mermaid] Description: {description}")  
        lines = ["@startuml"]
        
        direction = random.choice(['LR', 'RL', 'TB', 'BT'])  # 随机选择方向
        if direction in ['LR', 'RL']: lines.append("left to right direction")
        else: lines.append("top to bottom direction")
        # lines.append("top to bottom direction")
        
        # lines.append("skinparam dpi 120")
        lines.append("skinparam defaultTextAlignment center")
        lines.append("skinparam shadowing false")
        # lines.append("scale max 3000 width")

        
        if nodes_cfg[0].get('font') =="handwritten":
            # ✅ 设置手写字体
            lines.append("!option handwritten true") # 启用手写模式
            # 设置默认字体为手写字体。请确保此字体在你的系统上可用。
            # 常见的手写字体包括 "Comic Sans MS", "Architects Daughter", "Kristen ITC" 等
            lines.append('skinparam defaultFontName "Comic Sans MS"') 

        defined_stereotypes = set()
        nodes_already_in_groups = set()
        for group in subgraphs_cfg:
            # 渲染组时，会根据 _get_inline_color_string 里的逻辑随机分配颜色
            self._render_group(group, nodes_cfg, defined_stereotypes, lines)
            nodes_already_in_groups.update(group.get("nodes", []))

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

            # 添加内联颜色（非组，所以 is_group=False）
            inline_color_string = self._get_inline_color_string(node_data, is_group=False)
            if inline_color_string:
                node_puml_line_parts.append(inline_color_string)

            # 处理其他样式（非颜色），如果存在则依然使用 skinparam
            style_string = self._get_node_style_plantuml_string(node_data)
            if style_string:
                lines.append(f"skinparam {plantuml_shape} {{")
                lines.append(f"    {style_string}")
                lines.append("}")
            
            lines.append(" ".join(node_puml_line_parts))

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

        out_path = config['output']['path']
        output_dir = os.path.dirname(out_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        puml_path = os.path.splitext(out_path)[0] + '.puml'
        with open(puml_path, 'w', encoding='utf-8') as f:
            f.write(plantuml_code)
        print(f"[PlantUMLRenderer] PlantUML 代码已写入 {puml_path}")

        if config['output'].get('render', False):
            output_format = os.path.splitext(out_path)[1][1:] or "svg"
            cmd = ['java', '-jar', jar_path] if jar_path else ['plantuml']
            cmd.extend([f'-t{output_format}', puml_path])
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"[PlantUMLRenderer] 图像已渲染到 {os.path.splitext(out_path)[0]}.{output_format}")
                else:
                    print(f"[PlantUMLRenderer] 渲染失败：{result.stderr.strip()}")
            except Exception as e:
                print(f"[PlantUMLRenderer] 渲染过程中发生错误: {e}")
                print(traceback.format_exc()) # 这将打印完整的堆栈信息，包括行号
                return None # 或者 re-raise 异常，取决于您的错误处理策略
            
            # 如果启用了扫描风格
            if config['graph'].get('scanned', False):
                # 新建输出路径：原路径加 `_scanned` 后缀
                base, ext = os.path.splitext(out_path)
                scanned_path = base + "_scanned" + ext

                # 拷贝原图（因为我们不覆盖原图）
                copyfile(out_path, scanned_path)
                apply_scanned_style(scanned_path, config['graph']['scanned'], backend_name)  
                        
        return plantuml_code