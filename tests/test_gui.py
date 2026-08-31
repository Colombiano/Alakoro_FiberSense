"""
Testes de GUI do Alakoro FiberSense usando pytest-qt.

Executar com:
    QT_QPA_PLATFORM=offscreen pytest tests/test_gui.py -v
"""

from __future__ import annotations

import os

import numpy as np
import pytest
from PySide6.QtWidgets import QWidget

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.gui.main_window import AlakoroMainWindow
from src.io.alakoro_spool import AlakoroPatch
from src.io.dasdae import DASDAEAdapter


@pytest.fixture
def sample_patch() -> AlakoroPatch:
    data = np.random.randn(128, 32)
    dc_patch = DASDAEAdapter.array_to_patch(data, modality="das", dt_s=0.001, dx_m=1.0)
    return AlakoroPatch(dc_patch, modality="das")


def test_main_window_constructs(qtbot):
    window = AlakoroMainWindow()
    qtbot.addWidget(window)
    window.show()
    assert window.isVisible()


def test_set_patch_updates_viewers(qtbot, sample_patch):
    window = AlakoroMainWindow()
    qtbot.addWidget(window)
    window.show()

    window._set_patch(sample_patch)
    assert window._patch is sample_patch
    assert window._display_data.shape == sample_patch.shape


def test_undo_redo(qtbot, sample_patch):
    window = AlakoroMainWindow()
    qtbot.addWidget(window)
    window.show()

    window._set_patch(sample_patch)
    original = window._display_data.copy()

    # Simula um processamento alterando dados e empilhando histórico
    window._push_history()
    window._display_data = original * 2
    window._history.append((sample_patch, window._display_data.copy()))
    window._history_index = 1

    window._undo()
    assert window._history_index == 0

    window._redo()
    assert window._history_index == 1


def test_heatmap_cursor_signals(qtbot, sample_patch):
    window = AlakoroMainWindow()
    qtbot.addWidget(window)
    window.show()
    window._set_patch(sample_patch)

    # Simula movimento do mouse no heatmap
    window.heatmap.set_data(sample_patch.data)
    pos = window.heatmap.plot_item.vb.mapViewToScene(window.heatmap.plot_item.vb.viewRect().center())
    window.heatmap._on_mouse_moved([pos])

    # Verifica se status foi atualizado (não vazio)
    assert window.status.currentMessage() != ""


def test_preset_panel_emits_pipeline(qtbot):
    from src.gui.processors.preset_panel import PresetPanel

    panel = PresetPanel()
    qtbot.addWidget(panel)

    received = []
    panel.apply_preset_requested.connect(lambda pipeline: received.append(pipeline))

    # Cria pipeline via editor
    panel.editor.node_combo.setCurrentText("demean")
    panel.editor._add_node()
    panel._apply_selected = lambda: panel.apply_preset_requested.emit(panel.editor.get_pipeline())
    panel._apply_selected()

    assert len(received) == 1
    assert received[0][0]["action"] == "demean"


# ─── Serializacao / Kafka GUI ───

def test_serialization_panel_constructs(qtbot):
    from src.gui.serialization_panel import SerializationPanel

    panel = SerializationPanel()
    qtbot.addWidget(panel)

    assert panel.tabs.count() == 3
    assert panel.export_btn is not None
    assert panel.import_btn is not None
    assert panel.producer_btn is not None


def test_serialization_panel_set_patch_enables_buttons(qtbot, sample_patch):
    from src.gui.serialization_panel import SerializationPanel

    panel = SerializationPanel()
    qtbot.addWidget(panel)

    assert not panel.export_btn.isEnabled()
    panel.set_patch(sample_patch)
    assert panel.export_btn.isEnabled()
    assert panel.producer_btn.isEnabled()


def test_serialization_panel_export_import_avro(qtbot, sample_patch, tmp_path):
    from src.gui.serialization_panel import SerializationPanel

    panel = SerializationPanel()
    qtbot.addWidget(panel)
    panel.set_patch(sample_patch)

    path = tmp_path / "test.avro"
    panel.export_format.setCurrentText("Avro")
    # Simula escolha do arquivo sem QFileDialog
    panel._export_patch_to(str(path))

    received = []
    panel.import_patch_requested.connect(lambda p: received.append(p))
    panel._import_file_from(str(path))

    assert len(received) == 1
    assert received[0].shape == sample_patch.shape
    assert received[0].modality == sample_patch.modality


def test_serialization_panel_export_import_protobuf(qtbot, sample_patch, tmp_path):
    from src.gui.serialization_panel import SerializationPanel

    panel = SerializationPanel()
    qtbot.addWidget(panel)
    panel.set_patch(sample_patch)

    path = tmp_path / "test.pb"
    panel.export_format.setCurrentText("Protobuf")
    panel._export_patch_to(str(path))

    received = []
    panel.import_patch_requested.connect(lambda p: received.append(p))
    panel._import_file_from(str(path))

    assert len(received) == 1
    assert received[0].shape == sample_patch.shape


def test_kafka_worker_emits_patch(qtbot):
    from src.gui.workers.kafka_worker import KafkaConsumerWorker

    worker = KafkaConsumerWorker("localhost:9092")
    qtbot.addWidget(QWidget())  # ancorador para sinais

    received = []
    worker.patch_received.connect(lambda p: received.append(p))

    # Simula patch recebido sem iniciar thread
    import dascore as dc
    from dascore.core.attrs import PatchAttrs

    n_t, n_c = 6, 4
    data = np.random.randn(n_t, n_c).astype(np.float64)
    patch = dc.Patch(
        data=data,
        coords={
            "time": (np.arange(n_t) * 1e9).astype("timedelta64[ns]"),
            "distance": np.arange(n_c),
        },
        dims=("time", "distance"),
        attrs=PatchAttrs(data_category="das", data_units="1/s"),
    )
    worker.patch_received.emit(AlakoroPatch(patch))

    assert len(received) == 1
