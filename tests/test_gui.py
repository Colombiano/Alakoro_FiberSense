"""
Testes de GUI do Alakoro FiberSense usando pytest-qt.

Executar com:
    QT_QPA_PLATFORM=offscreen pytest tests/test_gui.py -v
"""

from __future__ import annotations

import os

import numpy as np
import pytest

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
