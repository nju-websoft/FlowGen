# flowchart_generator/main.py
import yaml
import argparse
import traceback
import os
import sys
from factory import get_renderer
from graph_generator import generate_flow_config
import random
from difficulty import difficulty_ranges, scanned_style_difficulty
from my_dictionary import APPLICATIONS

def sample_difficulty_params(difficulty: str):
    ranges = difficulty_ranges[difficulty]
    params = {}

    params["order"] = ranges["order"]
    params["split_arrow"] = random.randint(*ranges["split_arrow"])
    params["merge_arrow"] = random.randint(*ranges["merge_arrow"])
    params["branch"] = random.randint(*ranges["branch"])
    params["nest"] = ranges["nest"]
    params["density"] = round(random.uniform(*ranges["density"]), 2)
    params["no_edge_label"] = round(random.uniform(*ranges["no_edge_label"]), 2)
    
    return params

def update_config_with_difficulty(config, difficulty):
    if difficulty not in difficulty_ranges:
        raise ValueError(f"未知难度等级：{difficulty}")
    
    overrides = sample_difficulty_params(difficulty)
    config['generation'].update(overrides)
    
    return config


def load_config(path: str) -> dict:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML configuration file: {e}")
        sys.exit(1)

def main(config_path: str):
    parser = argparse.ArgumentParser()
    parser.add_argument("config_path", type=str, help="YAML 配置文件路径")
    parser.add_argument("--difficulty", type=str, choices=["easy", "medium", "hard"], help="测试集难度等级")
    parser.add_argument("--scanned_style_difficulty", type=str, choices=["easy", "medium", "hard"], help="扫描风格难度等级")
    parser.add_argument("--backend", type=str, choices=["mermaid", "graphviz", "plantuml", "diagrams"], help="渲染器名称")
    parser.add_argument("--start_index", type=int, default=1, help="编号起始值（默认从1开始）")
    args = parser.parse_args()
    with open(args.config_path, 'r') as f:
        config = yaml.safe_load(f)
        
    # 渲染器加载
    backend_name = args.backend if args.backend else config.get('backend', 'mermaid')
    config['backend'] = backend_name  # 确保 config 中保持一致
    count = config.get('generation', {}).get('count', 1)
    
    # 输出配置
    output_config = config.get('output', {})
    if 'path' not in output_config:
        print("Error: 'output.path' is a required field in the configuration.")
        sys.exit(1)

    config['output']['path'] = config['output']['path'].format(backend=config['backend'])
    base_path = output_config['path']
    base_name, ext = os.path.splitext(base_path)
    render_image = output_config.get('render', False)

    
    try:
        renderer = get_renderer(backend_name)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    start_index = args.start_index
    for i, domain in enumerate(APPLICATIONS):
        for j in range(8):  # 每个领域生成4个图
            current_index = start_index + i * 8 + j

            print(f"\n[Main] Generating flowchart {i + 1}/{len(APPLICATIONS)} using backend: {backend_name} for domain: {domain}")
            
            if args.difficulty:
                config = update_config_with_difficulty(config, args.difficulty)
            # 根据指定的扫描风格难度覆盖配置
            if args.scanned_style_difficulty:
                if args.scanned_style_difficulty in scanned_style_difficulty:
                    config["Scanned_style"] = scanned_style_difficulty[args.scanned_style_difficulty]
                else:
                    print(f"未知的扫描风格难度：{args.scanned_style_difficulty}")
                    sys.exit(1)

            # 从主配置中提取生成参数
            generation_params = config.get('generation', {})
            scale = generation_params.get('order', 'medium')
            branch = generation_params.get('branch', 0)
            nest = int(generation_params.get('nest', 0))
            density = generation_params.get('density', 'normal')
            split_arrow = generation_params.get("split_arrow", 0)
            merge_arrow = generation_params.get("merge_arrow", 0)
            no_edge_label_ratio = generation_params.get("no_edge_label", 0.0)
            # 扰动项加载
            handwritten_style = config.get("Disturbance", {}).get('handwritten_style', False)
            if config.get("Scanned_style", {}).get('enable', False) == True:
                scanned_style = config.get("Scanned_style", {})
            else:
                scanned_style = {}
            # 图的通用属性
            graph_common_config = config.get('graph', {})
            default_title_template = graph_common_config.get(
                'title', "自动生成流程图-{backend_name}-{scale}"
            )
            default_description_template = graph_common_config.get(
                'description',
                "节点数: {num_nodes}, 分支: {branch}, 嵌套子图数: {nest}, 密度: {density}，无标签边比例: {no_edge_label_ratio}。"
            )
            print(f"\n[Main] Generating flowchart {i + 1}/{len(APPLICATIONS)} using backend: {backend_name}")

            flow_specific_graph_data = generate_flow_config(backend_name, scale, branch, nest, density, split_arrow, merge_arrow,
                                                            no_edge_label_ratio, handwritten_style, scanned_style, domain=domain)

            # 获取节点数量（主图 + 子图）用于描述模板
            num_nodes_generated = len(flow_specific_graph_data['graph']['nodes'])

            # 格式化标题与描述
            current_title = default_title_template.format(
                scale=scale,
                backend_name=backend_name,
                count=current_index,
                num_nodes=num_nodes_generated,
                branch=branch,
                nest=nest,
                density=density
            )
            current_description = default_description_template.format(
                scale=scale,
                count=current_index,
                num_nodes=num_nodes_generated,
                split_arrow=split_arrow,
                merge_arrow=merge_arrow,
                branch=branch,
                nest=nest,
                density=density,
                no_edge_label_ratio=no_edge_label_ratio,
            )

            # 更新 graph 数据
            flow_specific_graph_data['graph']['title'] = current_title
            flow_specific_graph_data['graph']['description'] = current_description

            # 构建当前运行配置
            current_run_config = {
                'graph': flow_specific_graph_data['graph'],
                'output': {
                    'path': f"{base_name}_{current_index}{ext}",
                    'render': render_image
                }
            }

            # 附加其他自定义配置
            for key, value in config.items():
                if key not in ['generation', 'output', 'backend', 'graph']:
                    current_run_config[key] = value

            try:
                if backend_name == "plantuml":
                    renderer.render(current_run_config, config.get('plantuml', {})['jar_path'], backend_name)
                else:
                    renderer.render(current_run_config, backend_name)
            except Exception as e:
                print(f"[Main] Error during rendering with {backend_name} for flowchart {i+1}: {e}")
                traceback.print_exc() 
                
            break
        break

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python main.py <config.yaml>")
        example_config = {
            "backend": "mermaid",
            "generation": {
                "count": 1,
                "scale": "small",
                "branch": True,
                "nest": 2,
                "density": "normal"
            },
            "graph": {
                "direction": "TD",
                "title": "嵌套流程图 - {scale} #{count}",
                "description": "总节点数: {num_nodes}, 分支: {branch}, 嵌套子图数: {nest}, 密度: {density}"
            },
            "output": {
                "path": "output/flowchart.mmd",
                "render": True
            }
        }
        with open("config_example.yaml", 'w', encoding='utf-8') as f_ex:
            yaml.dump(example_config, f_ex, allow_unicode=True, sort_keys=False)
        print("An example configuration file has been created at: config_example.yaml")
        sys.exit(1)

    config_file_path = sys.argv[1]
    main(config_file_path)
