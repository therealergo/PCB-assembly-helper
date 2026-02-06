import math

from PySide6.QtCore import Qt, QRectF, QTimer, QElapsedTimer, QPointF, QLineF
from PySide6.QtGui import QPen, QBrush, QColor, QWheelEvent, QMouseEvent, QPainter
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsItemGroup, QGraphicsLineItem
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtSvg import QSvgRenderer

from .models import Component, BoundsMM, Side


class PulsingMarker(QGraphicsItemGroup):
    def __init__(self, center_x: float, center_y: float, marker_size: float, marker_size_mult: float, designator: str):
        super().__init__()
        self._center = QPointF(center_x, center_y)
        self._center_x = center_x
        self._center_y = center_y
        self._marker_size = marker_size
        self._marker_size_mult = marker_size_mult
        self._designator = designator
        
        self._circle = QGraphicsEllipseItem()
        self._circle.setPen(QPen(QColor("#ff0000"), marker_size))
        self._circle.setBrush(QBrush(QColor(255, 255, 0, 80)))
        self.addToGroup(self._circle)
        
        crosshair_pen = QPen(QColor("#ff0000"), marker_size)
        self._h_line = QGraphicsLineItem()
        self._h_line.setPen(crosshair_pen)
        self.addToGroup(self._h_line)
        
        self._v_line = QGraphicsLineItem()
        self._v_line.setPen(crosshair_pen)
        self.addToGroup(self._v_line)
        
        self.setZValue(15)
        self._update_geometry()

        self._label = QGraphicsTextItem(designator)
        self._label.setDefaultTextColor(QColor("#ffff00"))
        self._label.setScale(marker_size)
        self._label.setPos(center_x + 5.0 * marker_size, center_y - 12.5 * marker_size)
        self._label.setZValue(20)
        self.addToGroup(self._label)

    def _update_geometry(self):
        cx, cy = self._center.x(), self._center.y()
        r = self._marker_size * 4.0 * self._marker_size_mult
        
        self._circle.setRect(cx - r, cy - r, r * 2, r * 2)
        
        crosshair_size = r * 1.5
        self._h_line.setLine(cx - crosshair_size, cy, cx + crosshair_size, cy)
        self._v_line.setLine(cx, cy - crosshair_size, cx, cy + crosshair_size)

    def pulse_step(self, marker_size_mult):
        self._marker_size_mult = marker_size_mult
        self._update_geometry()


class PCBView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(QColor("#1a1a1a")))

        self._svg_item: QGraphicsSvgItem | None = None
        self._svg_renderer: QSvgRenderer | None = None
        self._component_positions: dict[str, tuple[float, float]] = {}
        self._highlight_markers: list[PulsingMarker] = []
        self._bounds: BoundsMM | None = None
        self._current_side: Side = Side.TOP
        self._zoom_factor = 1.0
        self._svg_viewbox: tuple[float, float, float, float] | None = None
        self._item_bounds: tuple[float, float, float, float] = (0, 0, 1, 1)
        self._marker_size = 0.5
        self._marker_size_mult = 1.0

        self._pulse_timer_elapsed = QElapsedTimer()
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._on_pulse_tick)
        self._pulse_timer.setInterval(30)
        self._pulse_timer.start()
        self._pulse_timer_elapsed.start()

    def _on_pulse_tick(self):
        self._marker_size_mult = math.sin(self._pulse_timer_elapsed.elapsed() / 300.0) * 0.3 + 1.0
        for marker in self._highlight_markers:
            marker.pulse_step(self._marker_size_mult)

    def set_board_svg(self, svg_data: bytes, bounds: BoundsMM):
        self._bounds = bounds
        self.clear_highlights()
        self._scene.clear()
        self._component_positions.clear()

        self._svg_renderer = QSvgRenderer(svg_data)
        self._svg_item = QGraphicsSvgItem()
        self._svg_item.setSharedRenderer(self._svg_renderer)
        self._scene.addItem(self._svg_item)

        vb = self._svg_renderer.viewBoxF()
        self._svg_viewbox = (vb.x(), vb.y(), vb.width(), vb.height())

        br = self._svg_item.boundingRect()
        self._item_bounds = (br.x(), br.y(), br.width(), br.height())

        self._scene.setSceneRect(self._svg_item.boundingRect())

    def set_components(self, components: list[Component], bounds: BoundsMM, side: Side):
        self._bounds = bounds
        self._current_side = side
        self._component_positions.clear()

        for comp in components:
            if comp.side != side:
                continue
            self._store_component_position(comp)

    def _store_component_position(self, comp: Component):
        if self._bounds is None or self._svg_viewbox is None:
            return

        vb_x, vb_y, vb_w, vb_h = self._svg_viewbox
        ib_x, ib_y, ib_w, ib_h = self._item_bounds

        x_mm = comp.x_mm
        y_mm = comp.y_mm

        if self._current_side == Side.BOTTOM:
            x_mm = self._bounds.xmin + self._bounds.xmax - x_mm

        norm_x = (x_mm - vb_x) / vb_w if vb_w else 0
        norm_y = 1.0 - ((y_mm - vb_y) / vb_h) if vb_h else 0

        item_x = ib_x + norm_x * ib_w
        item_y = ib_y + norm_y * ib_h

        self._component_positions[comp.designator] = (item_x, item_y)

    def highlight_components(self, designators: list[str]):
        self.clear_highlights()

        first_pos = None
        for designator in designators:
            pos = self._component_positions.get(designator)
            if pos:
                svg_x, svg_y = pos
                if first_pos is None:
                    first_pos = pos

                marker = PulsingMarker(
                    svg_x, 
                    svg_y, 
                    self._marker_size, 
                    self._marker_size_mult, 
                    designator)
                self._scene.addItem(marker)
                self._highlight_markers.append(marker)

        if first_pos:
            self.centerOn(QPointF(first_pos[0], first_pos[1]))

    def clear_highlights(self):
        for marker in self._highlight_markers:
            self._scene.removeItem(marker)
        self._highlight_markers.clear()

    def zoom_to_fit(self):
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom_factor = self.transform().m11()

    def wheelEvent(self, event: QWheelEvent):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        self._zoom_factor *= zoom_factor
        self.scale(zoom_factor, zoom_factor)

    def set_marker_size(self, _marker_size):
        self._marker_size = _marker_size
        highlight_markers_clone = self._highlight_markers[:]
        self.clear_highlights()
        for highlight_marker in highlight_markers_clone:
            marker = PulsingMarker(
                highlight_marker._center_x, 
                highlight_marker._center_y, 
                _marker_size, 
                highlight_marker._marker_size_mult, 
                highlight_marker._designator)
            self._scene.addItem(marker)
            self._highlight_markers.append(marker)