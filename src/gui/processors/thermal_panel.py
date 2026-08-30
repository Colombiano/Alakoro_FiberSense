"""
Painel de processadores térmicos para DTS.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ThermalPanel(QWidget):
    """Painel de processamento térmico para dados DTS."""

    process_requested = Signal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        group = QGroupBox("DTS Thermal Processing")
        form = QFormLayout(group)

        self.depth_step_spin = QDoubleSpinBox()
        self.depth_step_spin.setRange(0.001, 1000.0)
        self.depth_step_spin.setValue(1.0)
        self.depth_step_spin.setSuffix(" m")
        form.addRow("Depth step:", self.depth_step_spin)

        self.surface_temp_spin = QDoubleSpinBox()
        self.surface_temp_spin.setRange(-50.0, 100.0)
        self.surface_temp_spin.setValue(20.0)
        self.surface_temp_spin.setSuffix(" °C")
        form.addRow("Surface temp:", self.surface_temp_spin)

        self.gradient_spin = QDoubleSpinBox()
        self.gradient_spin.setRange(0.0, 0.5)
        self.gradient_spin.setValue(0.03)
        self.gradient_spin.setDecimals(4)
        self.gradient_spin.setSuffix(" °C/m")
        form.addRow("Geothermal gradient:", self.gradient_spin)

        self.anomaly_sigma_spin = QDoubleSpinBox()
        self.anomaly_sigma_spin.setRange(0.5, 10.0)
        self.anomaly_sigma_spin.setValue(3.0)
        self.anomaly_sigma_spin.setDecimals(1)
        self.anomaly_sigma_spin.setSuffix(" σ")
        form.addRow("Anomaly threshold:", self.anomaly_sigma_spin)

        self.spatial_median_spin = QSpinBox()
        self.spatial_median_spin.setRange(3, 101)
        self.spatial_median_spin.setValue(5)
        self.spatial_median_spin.setSingleStep(2)
        form.addRow("Spatial median window:", self.spatial_median_spin)

        for name, action in [
            ("Thermal Gradient", "thermal_gradient"),
            ("Geothermal Baseline Correction", "geothermal_baseline_correction"),
            ("Thermal Anomaly Detection", "thermal_anomaly_detection"),
            ("Spatial Median Filter", "spatial_median_filter"),
            ("Full DTS Pipeline", "dts_pipeline"),
        ]:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, a=action: self._request(a))
            form.addRow(btn)

        layout.addWidget(group)
        layout.addStretch()

    def _request(self, action: str):
        kwargs = {
            "depth_step_m": self.depth_step_spin.value(),
            "surface_temp": self.surface_temp_spin.value(),
            "gradient": self.gradient_spin.value(),
            "threshold_sigma": self.anomaly_sigma_spin.value(),
            "window_size": self.spatial_median_spin.value(),
        }
        self.process_requested.emit(action, kwargs)
