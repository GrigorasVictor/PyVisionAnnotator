from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox, QCheckBox, QLabel
from PyQt6.QtCore import Qt

class AutoSegRunDialog(QDialog):
    def __init__(self, parent=None, default_labels=""):
        super().__init__(parent)
        self.setWindowTitle("Run AutoSeg (YOLO)")
        self.resize(400, 200)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.edit_labels = QLineEdit()
        self.edit_labels.setText(default_labels)
        self.edit_labels.setPlaceholderText("person, car, dog...")
        form.addRow("Labels (comma-sep):", self.edit_labels)
        
        layout.addLayout(form)
        
        layout.addWidget(QLabel("Output Mode:"))
        self.chk_bbox = QCheckBox("Bounding Box (bbox)")
        self.chk_bbox.setChecked(True)
        layout.addWidget(self.chk_bbox)
        
        self.chk_segment = QCheckBox("Segmentation Mask (segment)")
        self.chk_segment.setChecked(True)
        layout.addWidget(self.chk_segment)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def get_values(self):
        labels = self.edit_labels.text().strip()
        modes = []
        if self.chk_bbox.isChecked(): modes.append("bbox")
        if self.chk_segment.isChecked(): modes.append("segment")
        return labels, modes

