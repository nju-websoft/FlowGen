# flowchart_generator/interfaces.py
from abc import ABC, abstractmethod

class IGraphRenderer(ABC):
    @abstractmethod
    def render(self, config: dict):
        pass