from PySide6.QtCore import Qt, QRectF, QTimer, QPointF, QLineF
from PySide6.QtGui import QPen, QBrush, QColor, QWheelEvent, QMouseEvent, QPainter
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsTextItem, QGraphicsItemGroup, QGraphicsLineItem
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtSvg import QSvgRenderer

from .models import Component, BoundsMM, Side


class PulsingMarker(QGraphicsItemGroup):
    def __init__(self, center_x: float, center_y: float, base_radius: float = 4.0):
        super().__init__()
        self._center = QPointF(center_x, center_y)
        self._base_radius = base_radius
        self._min_radius = base_radius
        self._max_radius = base_radius * 2.0
        self._current_radius = base_radius
        self._growing = True
        
        self._circle = QGraphicsEllipseItem()
        self._circle.setPen(QPen(QColor("#ff0000"), 1.0))
        self._circle.setBrush(QBrush(QColor(255, 255, 0, 80)))
        self.addToGroup(self._circle)
        
        crosshair_pen = QPen(QColor("#ff0000"), 1.0)
        self._h_line = QGraphicsLineItem()
        self._h_line.setPen(crosshair_pen)
        self.addToGroup(self._h_line)
        
        self._v_line = QGraphicsLineItem()
        self._v_line.setPen(crosshair_pen)
        self.addToGroup(self._v_line)
        
        self.setZValue(15)
        self._update_geometry()

    def _update_geometry(self):
        cx, cy = self._center.x(), self._center.y()
        r = self._current_radius
        
        self._circle.setRect(cx - r, cy - r, r * 2, r * 2)
        
        crosshair_size = r * 1.5
        self._h_line.setLine(cx - crosshair_size, cy, cx + crosshair_size, cy)
        self._v_line.setLine(cx, cy - crosshair_size, cx, cy + crosshair_size)

    def pulse_step(self):
        step = 0.5
        if self._growing:
            self._current_radius += step
            if self._current_radius >= self._max_radius:
                self._growing = False
        else:
            self._current_radius -= step
            if self._current_radius <= self._min_radius:
                self._growing = True
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
        self._highlight_labels: list[QGraphicsTextItem] = []
        self._bounds: BoundsMM | None = None
        self._current_side: Side = Side.TOP
        self._zoom_factor = 1.0
        self._svg_viewbox: tuple[float, float, float, float] | None = None
        self._item_bounds: tuple[float, float, float, float] = (0, 0, 1, 1)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._on_pulse_tick)
        self._pulse_timer.setInterval(30)

    def _on_pulse_tick(self):
        for marker in self._highlight_markers:
            marker.pulse_step()

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

                marker = PulsingMarker(svg_x, svg_y, base_radius=4.0)
                self._scene.addItem(marker)
                self._highlight_markers.append(marker)

                label = QGraphicsTextItem(designator)
                label.setDefaultTextColor(QColor("#ffff00"))
                label.setPos(svg_x + 10, svg_y - 10)
                label.setZValue(20)
                self._scene.addItem(label)
                self._highlight_labels.append(label)

        if self._highlight_markers:
            self._pulse_timer.start()

        if first_pos:
            self.centerOn(QPointF(first_pos[0], first_pos[1]))

    def clear_highlights(self):
        self._pulse_timer.stop()

        for marker in self._highlight_markers:
            self._scene.removeItem(marker)
        self._highlight_markers.clear()

        for label in self._highlight_labels:
            self._scene.removeItem(label)
        self._highlight_labels.clear()

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
