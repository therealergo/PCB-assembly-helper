from pathlib import Path

from gerbonara import GerberFile
from gerbonara.layers import LayerStack

from .models import BoundsMM, Side
from .gerber_loader import GerberSet


def get_board_bounds(gerber_set: GerberSet) -> BoundsMM:
    all_bounds = []

    files_to_check = [
        gerber_set.outline,
        gerber_set.gtl,
        gerber_set.gbl,
        gerber_set.gto,
        gerber_set.gbo,
    ]

    for gpath in files_to_check:
        if gpath and gpath.exists():
            try:
                gf = GerberFile.open(gpath)
                bounds = gf.bounding_box()
                if bounds and bounds[0] is not None:
                    (xmin, ymin), (xmax, ymax) = bounds
                    all_bounds.append((xmin, ymin, xmax, ymax))
            except Exception:
                pass

    if not all_bounds:
        return BoundsMM()

    xmin = min(b[0] for b in all_bounds)
    ymin = min(b[1] for b in all_bounds)
    xmax = max(b[2] for b in all_bounds)
    ymax = max(b[3] for b in all_bounds)

    return BoundsMM(xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax)


def render_gerber_to_svg(
    gerber_set: GerberSet, side: Side, bounds: BoundsMM
) -> bytes:
    width = bounds.width
    height = bounds.height

    if side == Side.TOP:
        outline = gerber_set.outline
        copper = gerber_set.gtl
        soldermask = gerber_set.gts
        silkscreen = gerber_set.gto
    else:
        outline = gerber_set.outline
        copper = gerber_set.gbl
        soldermask = gerber_set.gbs
        silkscreen = gerber_set.gbo

    if side == Side.TOP:
        transform = f'scale(1,-1) translate(0,{-(bounds.ymin + bounds.ymax)})'
    else:
        center_x = bounds.xmin + width / 2
        transform = f'scale(-1,-1) translate({-2 * center_x},{-(bounds.ymin + bounds.ymax)})'

    svg_parts = [
        f'<?xml version="1.0" encoding="utf-8"?>',
        f'<svg width="{width}mm" height="{height}mm" '
        f'viewBox="{bounds.xmin} {bounds.ymin} {width} {height}" '
        f'style="background-color:#1a1a1a" '
        f'xmlns="http://www.w3.org/2000/svg">',
        f'<g transform="{transform}">'
    ]

    if outline and outline.exists():
        svg_parts.append(_render_layer(outline, "#1a3d1a"))

    if copper and copper.exists():
        svg_parts.append(_render_layer(copper, "#b87333"))

    if soldermask and soldermask.exists():
        svg_parts.append(f'<g opacity="0.85">')
        svg_parts.append(_render_layer(soldermask, "#1a5f1a"))
        svg_parts.append('</g>')

    if soldermask and soldermask.exists():
        svg_parts.append(_render_layer(soldermask, "#d4af37"))

    if silkscreen and silkscreen.exists():
        svg_parts.append(_render_layer(silkscreen, "#ffffff"))

    svg_parts.append('</g>')
    svg_parts.append('</svg>')
    return '\n'.join(svg_parts).encode('utf-8')


def _render_layer(layer_path: Path, color: str) -> str:
    try:
        gf = GerberFile.open(layer_path)
        svg_objects = list(gf.svg_objects(fg=color, bg='none'))
        return '\n'.join(str(obj) for obj in svg_objects)
    except Exception as e:
        print(f"Error rendering {layer_path}: {e}")
        return ''
