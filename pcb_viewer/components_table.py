import re
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import QTableView, QHeaderView

from .models import Component, Side


def natural_sort_key(designator: str):
    parts = re.split(r'(\d+)', designator)
    return [int(p) if p.isdigit() else p.lower() for p in parts]


class ComponentGroup:
    def __init__(self, value: str, components: list[Component]):
        self.value = value
        self.components = sorted(components, key=lambda c: natural_sort_key(c.designator))

    @property
    def designators(self) -> str:
        return ", ".join(c.designator for c in self.components)

    @property
    def description(self) -> str:
        return self.components[0].description if self.components else ""


class ComponentsTableModel(QAbstractTableModel):
    COLUMNS = ["Designators", "Value"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._components: list[Component] = []
        self._groups: list[ComponentGroup] = []
        self._side_filter: Side | None = None

    def set_components(self, components: list[Component]):
        self.beginResetModel()
        self._components = components
        self._apply_filter()
        self.endResetModel()

    def set_side_filter(self, side: Side | None):
        self.beginResetModel()
        self._side_filter = side
        self._apply_filter()
        self.endResetModel()

    def _apply_filter(self):
        if self._side_filter is None:
            filtered = self._components[:]
        else:
            filtered = [c for c in self._components if c.side == self._side_filter]

        groups_dict: dict[str, list[Component]] = {}
        for comp in filtered:
            if comp.comment not in groups_dict:
                groups_dict[comp.comment] = []
            groups_dict[comp.comment].append(comp)

        self._groups = [ComponentGroup(value, comps) for value, comps in groups_dict.items()]
        self._groups.sort(key=lambda g: natural_sort_key(g.components[0].designator) if g.components else [])

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._groups)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        group = self._groups[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return group.designators
            elif index.column() == 1:
                return group.value
        elif role == Qt.ItemDataRole.ToolTipRole:
            return f"{group.designators}: {group.description}"

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.COLUMNS[section]
        return None

    def get_group(self, row: int) -> ComponentGroup | None:
        if 0 <= row < len(self._groups):
            return self._groups[row]
        return None

    def get_components_by_value(self, value: str) -> list[Component]:
        for group in self._groups:
            if group.value == value:
                return group.components
        return []


class ComponentsTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.verticalHeader().setVisible(False)
