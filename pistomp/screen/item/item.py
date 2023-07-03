from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class Item(ABC):
    name: str
    text: Optional[str]
    action: Optional[Callable]
    highlightable: bool
