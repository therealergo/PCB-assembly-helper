from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QToolBar,
    QComboBox,
    QPushButton,
    QFileDialog,
    QLabel,
    QMessageBox,
    QGroupBox,
    QSlider,
    QSizePolicy,
)

from .models import Component, BoundsMM, Side
from .pickplace import parse_pickplace_csv
from .gerber_loader import discover_gerbers, GerberSet
from .render_board import render_gerber_to_svg, get_board_bounds
from .components_table import ComponentsTableModel, ComponentsTableView
from .pcb_view import PCBView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PCB Viewer")
        self.setMinimumSize(1200, 800)

        self._components: list[Component] = []
        self._gerber_set: GerberSet | None = None
        self._bounds: BoundsMM | None = None
        self._current_side: Side = Side.TOP
        self._svg_cache: dict[Side, bytes] = {}

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._load_gerber_btn = QPushButton("Load Gerber Folder...")
        toolbar.addWidget(self._load_gerber_btn)

        self._load_pnp_btn = QPushButton("Load Pick && Place CSV...")
        toolbar.addWidget(self._load_pnp_btn)

        toolbar.addSeparator()

        toolbar.addWidget(QLabel("Side: "))
        self._side_combo = QComboBox()
        self._side_combo.addItem("Top", Side.TOP)
        self._side_combo.addItem("Bottom", Side.BOTTOM)
        toolbar.addWidget(self._side_combo)

        toolbar.addSeparator()

        self._zoom_fit_btn = QPushButton("Zoom to Fit")
        toolbar.addWidget(self._zoom_fit_btn)

        toolbar.addWidget(QLabel("  Marker Size: "))
        self._marker_size_slider = QSlider(Qt.Orientation.Horizontal)
        self._marker_size_slider.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._marker_size_slider.setValue(50)
        toolbar.addWidget(self._marker_size_slider)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        table_group = QGroupBox("Components")
        table_layout = QVBoxLayout(table_group)

        self._table_model = ComponentsTableModel()
        self._table_view = ComponentsTableView()
        self._table_view.setModel(self._table_model)
        table_layout.addWidget(self._table_view)

        left_layout.addWidget(table_group)

        self._pcb_view = PCBView()

        splitter.addWidget(left_panel)
        splitter.addWidget(self._pcb_view)
        splitter.setSizes([300, 900])

        self._status_label = QLabel("Load Gerber folder and Pick & Place CSV to begin")
        self.statusBar().addWidget(self._status_label)

    def _connect_signals(self):
        self._load_gerber_btn.clicked.connect(self._on_load_gerber)
        self._load_pnp_btn.clicked.connect(self._on_load_pnp)
        self._side_combo.currentIndexChanged.connect(self._on_side_changed)
        self._zoom_fit_btn.clicked.connect(self._pcb_view.zoom_to_fit)
        self._table_view.selectionModel().selectionChanged.connect(
            self._on_table_selection_changed
        )
        self._marker_size_slider.valueChanged.connect(self._on_marker_size_changed)

    def _on_load_gerber(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Gerber Folder", ""
        )
        if not folder:
            return

        try:
            self._gerber_set = discover_gerbers(folder)
            self._bounds = get_board_bounds(self._gerber_set)
            self._svg_cache.clear()
            self._render_current_side()
            self._update_component_markers()
            self._status_label.setText(f"Loaded Gerbers from: {folder}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load Gerbers: {e}")

    def _on_load_pnp(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Pick & Place CSV", "", "CSV Files (*.csv);;All Files (*)"
        )
        if not file_path:
            return

        try:
            self._components = parse_pickplace_csv(file_path)
            self._table_model.set_components(self._components)
            self._table_model.set_side_filter(self._current_side)
            self._update_component_markers()
            self._status_label.setText(
                f"Loaded {len(self._components)} components from: {file_path}"
            )
            self._table_view.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load Pick & Place: {e}")

    def _on_side_changed(self, index: int):
        self._current_side = self._side_combo.itemData(index)
        self._table_model.set_side_filter(self._current_side)
        self._pcb_view.clear_highlights()
        self._render_current_side()
        self._update_component_markers()

    def _render_current_side(self):
        if self._gerber_set is None or self._bounds is None:
            return

        if self._current_side not in self._svg_cache:
            svg_data = render_gerber_to_svg(
                self._gerber_set, self._current_side, self._bounds
            )
            self._svg_cache[self._current_side] = svg_data

        self._pcb_view.set_board_svg(
            self._svg_cache[self._current_side], self._bounds
        )
        self._pcb_view.zoom_to_fit()

    def _update_component_markers(self):
        if self._bounds is None:
            return

        self._pcb_view.set_components(
            self._components, self._bounds, self._current_side
        )

    def _on_table_selection_changed(self, selected, deselected):
        indexes = self._table_view.selectionModel().selectedRows()
        if not indexes:
            self._pcb_view.clear_highlights()
            return

        row = indexes[0].row()
        group = self._table_model.get_group(row)
        if group is None:
            return

        designators = [c.designator for c in group.components]
        self._pcb_view.highlight_components(designators)

    def _on_marker_size_changed(self, new_value):
        val_lin = ((new_value + 20.0) / 140.0) * 2.0
        self._pcb_view.set_marker_size(val_lin * val_lin)