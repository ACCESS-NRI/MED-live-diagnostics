from dataclasses import dataclass


class PlotType:
    value: str


@dataclass
class Line(PlotType):
    value = "Line"


@dataclass
class Heatmap(PlotType):
    value = "Heatmap"


class MultiplotHeatmap(PlotType):
    value = "Heatmap (grid)"


@dataclass
class Animation(PlotType):
    value = "Animation"
