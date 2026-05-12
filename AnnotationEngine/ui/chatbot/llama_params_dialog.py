"""ui/chatbot/llama_params_dialog.py - Configuration dialog for llama.cpp parameters."""
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QSpinBox,
    QDoubleSpinBox,
    QDialogButtonBox,
    QVBoxLayout
)

class LlamaParamsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("llama.cpp Parameters")
        self.setFixedSize(300, 200)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.spin_n_ctx = QSpinBox()
        self.spin_n_ctx.setRange(256, 128000)
        self.spin_n_ctx.setSingleStep(512)
        form_layout.addRow("Context Size (n_ctx):", self.spin_n_ctx)

        self.spin_max_tokens = QSpinBox()
        self.spin_max_tokens.setRange(-1, 32000)
        form_layout.addRow("Max Tokens:", self.spin_max_tokens)

        self.spin_temperature = QDoubleSpinBox()
        self.spin_temperature.setRange(0.0, 2.0)
        self.spin_temperature.setSingleStep(0.1)
        form_layout.addRow("Temperature:", self.spin_temperature)

        self.spin_top_p = QDoubleSpinBox()
        self.spin_top_p.setRange(0.0, 1.0)
        self.spin_top_p.setSingleStep(0.05)
        form_layout.addRow("Top-P:", self.spin_top_p)

        self.spin_repeat_penalty = QDoubleSpinBox()
        self.spin_repeat_penalty.setRange(1.0, 2.0)
        self.spin_repeat_penalty.setSingleStep(0.05)
        form_layout.addRow("Repeat Penalty:", self.spin_repeat_penalty)

        layout.addLayout(form_layout)

        self.btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.btn_box.accepted.connect(self.accept)
        self.btn_box.rejected.connect(self.reject)
        layout.addWidget(self.btn_box)

    def set_values(self, n_ctx: int, max_tokens: int, temperature: float, top_p: float, repeat_penalty: float):
        self.spin_n_ctx.setValue(n_ctx)
        self.spin_max_tokens.setValue(max_tokens)
        self.spin_temperature.setValue(temperature)
        self.spin_top_p.setValue(top_p)
        self.spin_repeat_penalty.setValue(repeat_penalty)

    def get_values(self) -> tuple[int, int, float, float, float]:
        return (
            self.spin_n_ctx.value(),
            self.spin_max_tokens.value(),
            self.spin_temperature.value(),
            self.spin_top_p.value(),
            self.spin_repeat_penalty.value()
        )

