from htpy import Renderable, h1

from ..components.layout import layout


def home() -> Renderable:
    return layout[h1["Hello, htpy!"]]
