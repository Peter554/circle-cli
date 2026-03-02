from htpy import Node, Renderable, body, html, main, with_children


@with_children
def layout(children: Node) -> Renderable:
    return html[body[main[children]]]
