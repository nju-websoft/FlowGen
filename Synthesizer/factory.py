# flowchart_generator/factory.py
from interfaces import IGraphRenderer
from renderers import MermaidRenderer, GraphvizRenderer, PlantUMLRenderer, DiagramsRenderer

RENDERER_REGISTRY = {
    'mermaid': MermaidRenderer,
    'graphviz': GraphvizRenderer,
    'plantuml': PlantUMLRenderer,
    'diagrams': DiagramsRenderer,
}

def get_renderer(name: str) -> IGraphRenderer:
    renderer_cls = RENDERER_REGISTRY.get(name.lower())
    if not renderer_cls:
        raise ValueError(f"Unsupported backend: {name}. Supported backends are: {list(RENDERER_REGISTRY.keys())}")
    return renderer_cls()