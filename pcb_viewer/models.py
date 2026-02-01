from dataclasses import dataclass
from enum import Enum


class Side(str, Enum):
    TOP = "TopLayer"
    BOTTOM = "BottomLayer"


@dataclass(frozen=True)
class Component:
    designator: str
    comment: str
    side: Side
    footprint: str
    x_mm: float
    y_mm: float
    rotation_deg: float
    description: str


@dataclass
class BoundsMM:
    xmin: float = 0.0
    xmax: float = 100.0
    ymin: float = 0.0
    ymax: float = 100.0

    @property
    def width(self) -> float:
        return self.xmax - self.xmin

    @property
    def height(self) -> float:
        return self.ymax - self.ymin
