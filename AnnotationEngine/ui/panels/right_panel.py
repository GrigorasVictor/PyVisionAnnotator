"""
ui/panels/right_panel.py — RightPanel

Right sidebar: owns all annotation-list, properties, tool-settings,
image-adjustment and label-chip logic. Talks to AnnotationManager and
AnnotationCanvas directly instead of routing everything through MainWindow.
"""
from __future__ import annotations

from typing import Optional, Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QGroupBox,
    QFormLayout,
    QFrame,
    QButtonGroup,
    QSlider,
    QCheckBox,
    QColorDialog,
    QMessageBox,
)

from core.annotation import BoundingBoxItem, PolygonItem, MaskItem


class RightPanel(QWidget):
    """Right sidebar panel — fully self-contained business logic.

    Outward signals (for MainWindow status bar / canvas crosshair):
        status_message(str)      — request to update status bar.
        tool_changed(str)        — new tool mode string ("rectangle"/"polygon"/"sam").
        crosshair_toggled(bool)  — crosshair enable state changed.
        canvas_brightness(int)   — set canvas brightness.
        canvas_contrast(float)   — set canvas contrast.
        canvas_gamma(float)      — set canvas gamma.
    """

    status_message = pyqtSignal(str)
    tool_changed = pyqtSignal(str)       # ToolMode string
    crosshair_toggled = pyqtSignal(bool)
    canvas_brightness = pyqtSignal(int)
    canvas_contrast = pyqtSignal(float)
    canvas_gamma = pyqtSignal(float)
    autoseg_config_requested = pyqtSignal()  # open AutoSeg settings dialog

    # ToolMode constants
    TOOL_RECT    = "rectangle"
    TOOL_POLY    = "polygon"
    TOOL_AUTOSEG = "autoseg"

    def __init__(
        self,
        manager,           # AnnotationManager
        canvas_fn: Callable,   # zero-arg → AnnotationCanvas (lazy to avoid circular)
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._manager = manager
        self._get_canvas = canvas_fn

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._build_properties_group(layout)
        self._build_tool_settings_group(layout)
        self._build_existing_labels_group(layout)
        self._build_tools_group(layout)
        self._build_separator(layout)
        self._build_annotations_list(layout)
        self._build_image_adjustments(layout)
        self._build_crosshair(layout)

        self._connect_internal_signals()

        # Keep manager annotation signals wired so lists stay fresh
        manager.annotation_added.connect(self._refresh_all)
        manager.annotation_removed.connect(self._on_annotation_removed)
        manager.annotation_updated.connect(self._refresh_all)
        manager.annotations_cleared.connect(self._refresh_all)

    # ================================================================== #
    #  Build helpers
    # ================================================================== #
    def _build_properties_group(self, layout: QVBoxLayout) -> None:
        self.props_group = QGroupBox("Properties (Selected)")
        form = QFormLayout(self.props_group)

        self.lbl_id = QLabel("—")
        form.addRow("ID:", self.lbl_id)

        self.edit_label = QLineEdit()
        self.edit_label.setPlaceholderText("e.g. car, person …")
        form.addRow("Label:", self.edit_label)

        color_row = QHBoxLayout()
        self.color_swatch = QFrame()
        self.color_swatch.setFixedSize(24, 24)
        self.color_swatch.setStyleSheet("background-color: #ff3232; border: 1px solid #888;")
        color_row.addWidget(self.color_swatch)
        self.btn_pick_color = QPushButton("Pick Colour …")
        color_row.addWidget(self.btn_pick_color)
        form.addRow("Colour:", color_row)

        self.lbl_coords = QLabel("—")
        form.addRow("Coords:", self.lbl_coords)

        self.props_group.setVisible(False)
        layout.addWidget(self.props_group)

    def _build_tool_settings_group(self, layout: QVBoxLayout) -> None:
        grp = QGroupBox("Active Tool Settings")
        form = QFormLayout(grp)

        self.tool_label_edit = QLineEdit()
        self.tool_label_edit.setPlaceholderText("Default Label")
        form.addRow("Next Label:", self.tool_label_edit)

        color_row = QHBoxLayout()
        self.tool_swatch = QFrame()
        self.tool_swatch.setFixedSize(24, 24)
        self.tool_swatch.setStyleSheet("background-color: #ff3232; border: 1px solid #888;")
        color_row.addWidget(self.tool_swatch)
        self.btn_tool_color = QPushButton("Set Color")
        color_row.addWidget(self.btn_tool_color)
        form.addRow("Next Color:", color_row)

        layout.addWidget(grp)

    def _build_existing_labels_group(self, layout: QVBoxLayout) -> None:
        grp = QGroupBox("Existing Labels")
        inner = QVBoxLayout(grp)
        inner.setContentsMargins(4, 4, 4, 4)

        self.label_counts_list = QListWidget()
        self.label_counts_list.setToolTip("Click a label to set it as the active label.")
        self.label_counts_list.setFixedHeight(120)
        self.label_counts_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.label_counts_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.label_counts_list.setSpacing(5)
        self.label_counts_list.setMovement(QListWidget.Movement.Static)
        inner.addWidget(self.label_counts_list)

        layout.addWidget(grp)

    def _build_tools_group(self, layout: QVBoxLayout) -> None:
        grp = QGroupBox("Tools")
        row = QHBoxLayout(grp)

        self.btn_tool_rect = QPushButton("Rect")
        self.btn_tool_rect.setCheckable(True)
        self.btn_tool_rect.setChecked(True)
        self.btn_tool_rect.setFixedSize(60, 60)
        self.btn_tool_rect.setStyleSheet("font-weight: bold;")

        self.btn_tool_poly = QPushButton("Poly")
        self.btn_tool_poly.setCheckable(True)
        self.btn_tool_poly.setFixedSize(60, 60)
        self.btn_tool_poly.setStyleSheet("font-weight: bold;")

        self.btn_tool_autoseg = QPushButton("AutoSeg")
        self.btn_tool_autoseg.setCheckable(True)
        self.btn_tool_autoseg.setFixedSize(60, 60)
        self.btn_tool_autoseg.setToolTip("Click on an object to auto-segment it")

        self.tools_btn_group = QButtonGroup(self)
        self.tools_btn_group.addButton(self.btn_tool_rect)
        self.tools_btn_group.addButton(self.btn_tool_poly)
        self.tools_btn_group.addButton(self.btn_tool_autoseg)

        row.addWidget(self.btn_tool_rect)
        row.addWidget(self.btn_tool_poly)
        row.addWidget(self.btn_tool_autoseg)
        row.addStretch()

        layout.addWidget(grp)

    def _build_separator(self, layout: QVBoxLayout) -> None:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)

    def _build_annotations_list(self, layout: QVBoxLayout) -> None:
        layout.addWidget(QLabel("Annotations:"))
        self.annotation_list = QListWidget()
        layout.addWidget(self.annotation_list)
        self.btn_delete = QPushButton("Delete Selected")
        layout.addWidget(self.btn_delete)

    def _build_image_adjustments(self, layout: QVBoxLayout) -> None:
        grp = QGroupBox("Image Adjustments")
        form = QFormLayout(grp)

        def _slider(lo, hi, val, tick):
            s = QSlider(Qt.Orientation.Horizontal)
            s.setRange(lo, hi); s.setValue(val)
            s.setTickPosition(QSlider.TickPosition.TicksBelow)
            s.setTickInterval(tick)
            return s

        self.sld_brightness = _slider(-100, 100, 0, 50)
        self.lbl_brightness_val = QLabel("0")
        br = QHBoxLayout(); br.addWidget(self.sld_brightness); br.addWidget(self.lbl_brightness_val)
        form.addRow("Brightness:", br)

        self.sld_contrast = _slider(10, 300, 100, 50)
        self.lbl_contrast_val = QLabel("1.0×")
        ct = QHBoxLayout(); ct.addWidget(self.sld_contrast); ct.addWidget(self.lbl_contrast_val)
        form.addRow("Contrast:", ct)

        self.sld_gamma = _slider(10, 300, 100, 50)
        self.lbl_gamma_val = QLabel("1.0")
        gm = QHBoxLayout(); gm.addWidget(self.sld_gamma); gm.addWidget(self.lbl_gamma_val)
        form.addRow("Gamma:", gm)

        self.btn_reset_adj = QPushButton("Reset")
        form.addRow(self.btn_reset_adj)
        layout.addWidget(grp)

    def _build_crosshair(self, layout: QVBoxLayout) -> None:
        self.chk_crosshair = QCheckBox("Crosshair")
        self.chk_crosshair.setChecked(True)
        layout.addWidget(self.chk_crosshair)

    # ================================================================== #
    #  Internal wiring
    # ================================================================== #
    def _connect_internal_signals(self) -> None:
        # Properties panel
        self.edit_label.editingFinished.connect(self._on_label_edited)
        self.btn_pick_color.clicked.connect(self._on_pick_color)

        # Tool settings
        self.tool_label_edit.editingFinished.connect(self._on_tool_label_edited)
        self.btn_tool_color.clicked.connect(self._on_tool_color_picked)

        # Existing labels
        self.label_counts_list.itemClicked.connect(self._on_existing_label_clicked)

        # Tool buttons
        self.tools_btn_group.buttonClicked.connect(self._on_tool_btn_clicked)

        # Annotations list
        self.annotation_list.currentItemChanged.connect(self._on_annotation_list_clicked)
        self.btn_delete.clicked.connect(self._on_delete)

        # Adjustments
        self.sld_brightness.valueChanged.connect(self._on_brightness_changed)
        self.sld_contrast.valueChanged.connect(self._on_contrast_changed)
        self.sld_gamma.valueChanged.connect(self._on_gamma_changed)
        self.btn_reset_adj.clicked.connect(self._on_reset_adjustments)

        # Crosshair
        self.chk_crosshair.toggled.connect(self.crosshair_toggled)

    # ================================================================== #
    #  Manager signal slots — keep lists fresh
    # ================================================================== #
    def _refresh_all(self, _id: str = "") -> None:
        self._rebuild_annotation_list()
        self._rebuild_label_chips()

    def _on_annotation_removed(self, _id: str = "") -> None:
        self._refresh_all()
        self.hide_properties()

    # Called by canvas scene.selectionChanged (wired from MainWindow)
    def on_scene_selection_changed(self) -> None:
        """Update properties panel based on current canvas selection."""
        canvas = self._get_canvas()
        selected = [
            it for it in canvas.scene().selectedItems()
            if isinstance(it, (BoundingBoxItem, PolygonItem, MaskItem))
        ]
        if len(selected) == 1:
            item = selected[0]
            d = item.to_dict()
            coords = (
                f"pts={len(d.get('points', []))}"
                if d.get("type") in ("poly", "mask")
                else f"({d['x']}, {d['y']})  {d['w']} × {d['h']}"
            )
            self.show_properties(item.annotation_id, item.label, item.color.name(), coords)
        else:
            self.hide_properties()

    # ================================================================== #
    #  Business-logic slots — Properties
    # ================================================================== #
    def _on_label_edited(self) -> None:
        box = self._selected_item()
        if box is None:
            return
        box.label = self.edit_label.text().strip()
        box.prepareGeometryChange()
        box.update()
        self._manager.update_item(box.annotation_id)

    def _on_pick_color(self) -> None:
        box = self._selected_item()
        if box is None:
            return
        chosen = QColorDialog.getColor(box.color, self, "Choose Annotation Colour")
        if not chosen.isValid():
            return
        box.color = chosen
        d = box.to_dict()
        coords = (
            f"pts={len(d.get('points', []))}"
            if d.get("type") in ("poly", "mask")
            else f"({d['x']}, {d['y']})  {d['w']} × {d['h']}"
        )
        self.show_properties(box.annotation_id, box.label, chosen.name(), coords)
        self._manager.update_item(box.annotation_id)

    # ================================================================== #
    #  Business-logic slots — Tool Settings
    # ================================================================== #
    def _on_tool_label_edited(self) -> None:
        self._manager.default_label = self.tool_label_edit.text().strip()

    def _on_tool_color_picked(self) -> None:
        color = QColorDialog.getColor(
            QColor(self._manager.default_color), self, "Choose Default Color"
        )
        if not color.isValid():
            return
        self._manager.default_color = color.name()
        self.tool_swatch.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #888;"
        )

    def _on_existing_label_clicked(self, item: QListWidgetItem) -> None:
        label = item.data(Qt.ItemDataRole.UserRole)
        color_name = item.data(Qt.ItemDataRole.UserRole + 1)
        self.tool_label_edit.setText(label)
        self._manager.default_label = label
        if color_name:
            self._manager.default_color = color_name
            self.tool_swatch.setStyleSheet(
                f"background-color: {color_name}; border: 1px solid #888;"
            )

    # ================================================================== #
    #  Business-logic slots — Tool buttons
    # ================================================================== #
    def _on_tool_btn_clicked(self, btn) -> None:
        if btn is self.btn_tool_autoseg:
            from ui.autoseg_settings_dialog import AutoSegSettingsDialog
            if not AutoSegSettingsDialog.is_configured():
                QMessageBox.warning(
                    self, "AutoSeg Not Configured",
                    "Please configure the AutoSeg model path first.\n"
                    "Go to the toolbar → ⚙ AutoSeg to set it up.",
                )
                self.btn_tool_rect.setChecked(True)
                self.tool_changed.emit(self.TOOL_RECT)
                return
            self.tool_changed.emit(self.TOOL_AUTOSEG)
            self.status_message.emit(
                "Tool: AutoSeg — Left-click on an object to auto-segment it."
            )
        elif btn is self.btn_tool_poly:
            self.tool_changed.emit(self.TOOL_POLY)
            self.status_message.emit(
                "Tool: Polygon — Left-click to add points, Right-click (or Enter) to close."
            )
        else:
            self.tool_changed.emit(self.TOOL_RECT)
            self.status_message.emit("Tool: Rectangle — Click and drag to create box.")

    # ================================================================== #
    #  Business-logic slots — Annotations list
    # ================================================================== #
    def _on_annotation_list_clicked(
        self, current: Optional[QListWidgetItem], _previous
    ) -> None:
        if current is None:
            return
        ann_id: str = current.data(Qt.ItemDataRole.UserRole)
        item = self._manager.get(ann_id)
        if item is None:
            return
        canvas = self._get_canvas()
        canvas.scene().clearSelection()
        item.setSelected(True)

    def _on_delete(self) -> None:
        self._get_canvas().delete_selected()

    # ================================================================== #
    #  Business-logic slots — Adjustments
    # ================================================================== #
    def _on_brightness_changed(self, value: int) -> None:
        self.lbl_brightness_val.setText(str(value))
        self.canvas_brightness.emit(value)

    def _on_contrast_changed(self, value: int) -> None:
        real = value / 100.0
        self.lbl_contrast_val.setText(f"{real:.1f}×")
        self.canvas_contrast.emit(real)

    def _on_gamma_changed(self, value: int) -> None:
        real = value / 100.0
        self.lbl_gamma_val.setText(f"{real:.2f}")
        self.canvas_gamma.emit(real)

    def _on_reset_adjustments(self) -> None:
        self.sld_brightness.setValue(0)
        self.sld_contrast.setValue(100)
        self.sld_gamma.setValue(100)

    # ================================================================== #
    #  Helpers
    # ================================================================== #
    def _selected_item(self) -> Optional[BoundingBoxItem | PolygonItem | MaskItem]:
        canvas = self._get_canvas()
        sel = [
            it for it in canvas.scene().selectedItems()
            if isinstance(it, (BoundingBoxItem, PolygonItem, MaskItem))
        ]
        return sel[0] if len(sel) == 1 else None

    def _rebuild_annotation_list(self) -> None:
        self.annotation_list.clear()
        for d in self._manager.get_all_dicts():
            label_tag = f" [{d['label']}]" if d.get("label") else ""
            coords = (
                f"pts={len(d.get('points', []))}"
                if d.get("type") in ("poly", "mask")
                else f"x={d['x']}  y={d['y']}  w={d['w']}  h={d['h']}"
            )
            li = QListWidgetItem(f"[{d['id']}]{label_tag}  {coords}")
            li.setData(Qt.ItemDataRole.UserRole, d["id"])
            self.annotation_list.addItem(li)

    def _rebuild_label_chips(self) -> None:
        label_map: dict[str, dict] = {}
        for it in self._manager.get_all():
            lbl = it.label.strip()
            if not lbl:
                continue
            if lbl not in label_map:
                label_map[lbl] = {"count": 0, "color": it.color.name()}
            label_map[lbl]["count"] += 1

        self.label_counts_list.clear()
        for lbl in sorted(label_map.keys()):
            info = label_map[lbl]
            item = QListWidgetItem(f"{lbl} ({info['count']})")
            item.setData(Qt.ItemDataRole.UserRole, lbl)
            item.setData(Qt.ItemDataRole.UserRole + 1, info["color"])
            pix = QPixmap(24, 24)
            pix.fill(QColor(info["color"]))
            item.setIcon(QIcon(pix))
            self.label_counts_list.addItem(item)

    # ================================================================== #
    #  Public setters (called by MainWindow or other panels if needed)
    # ================================================================== #
    def show_properties(self, annotation_id: str, label: str,
                        color_name: str, coords_text: str) -> None:
        self.props_group.setVisible(True)
        self.lbl_id.setText(annotation_id)
        self.edit_label.blockSignals(True)
        self.edit_label.setText(label)
        self.edit_label.blockSignals(False)
        self.color_swatch.setStyleSheet(
            f"background-color: {color_name}; border: 1px solid #888;"
        )
        self.lbl_coords.setText(coords_text)

    def hide_properties(self) -> None:
        self.props_group.setVisible(False)
        self.lbl_id.setText("—")
        self.edit_label.blockSignals(True)
        self.edit_label.clear()
        self.edit_label.blockSignals(False)
        self.color_swatch.setStyleSheet("background-color: #ff3232; border: 1px solid #888;")
        self.lbl_coords.setText("—")

    def set_tool_swatch(self, color_name: str) -> None:
        self.tool_swatch.setStyleSheet(
            f"background-color: {color_name}; border: 1px solid #888;"
        )

    def set_tool_label_text(self, text: str) -> None:
        self.tool_label_edit.setText(text)

    def reset_adjustments(self) -> None:
        self.sld_brightness.setValue(0)
        self.sld_contrast.setValue(100)
        self.sld_gamma.setValue(100)

