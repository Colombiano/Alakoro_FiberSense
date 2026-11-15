"""
Testes da Onda 2 — GUI de Análise de Fluxo (headless, QT_QPA_PLATFORM=offscreen)

- Janela constrói com dados sintéticos curtos
- Três HeatmapView (LF-DAS, HF-DAS, DTS) presentes e populados
- QListWidget com os resultados do motor populado
"""

from __future__ import annotations

import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from alakoro.gui.flow_analysis import JanelaAnaliseFluxo

FS_HZ = 200.0
N_T, N_Z = 400, 16


def _dados_sinteticos():
    rng = np.random.default_rng(11)
    t = np.arange(N_T) / FS_HZ
    z = np.arange(N_Z, dtype=float)

    atrasos = z / 20.0
    dt = t[:, None] - atrasos[None, :]
    das = np.exp(-0.5 * (dt / 0.05) ** 2) * np.sin(2.0 * np.pi * 20.0 * dt)
    das += rng.normal(0.0, 0.05, (N_T, N_Z))

    dts = 20.0 + 0.03 * z[None, :] + rng.normal(0.0, 0.02, (N_T, N_Z))
    dts[:, 6:12] += 5.0
    return das, dts


def _resultados():
    return [
        {"tipo": "slope_velocity", "profundidade_m": 1450.0,
         "velocidade_ms": 20.0, "discriminacao": "hydraulic"},
        {"tipo": "joule_thomson", "profundidade_m": 1200.0,
         "velocidade_ms": None, "discriminacao": "thermal"},
        {"type": "warm_back", "depth_m": 1500.0, "discrimination": "inconclusive"},
    ]


def test_janela_constroi_com_tres_viewers(qtbot):
    janela = JanelaAnaliseFluxo(fs_hz=FS_HZ)
    qtbot.addWidget(janela)
    janela.show()
    assert janela.isVisible()
    assert janela.viewer_lf is not None
    assert janela.viewer_hf is not None
    assert janela.viewer_dts is not None


def test_atualizar_popula_viewers_e_lista(qtbot):
    janela = JanelaAnaliseFluxo(fs_hz=FS_HZ)
    qtbot.addWidget(janela)

    das, dts = _dados_sinteticos()
    resultados = _resultados()
    janela.atualizar(dts, das, resultados)

    # três viewers populados com os shapes corretos
    assert janela.viewer_lf._data is not None
    assert janela.viewer_hf._data is not None
    assert janela.viewer_dts._data is not None
    assert janela.viewer_lf._data.shape == (N_T, N_Z)
    assert janela.viewer_hf._data.shape == (N_T, N_Z)
    assert janela.viewer_dts._data.shape == (N_T, N_Z)

    # lista de resultados do motor
    assert janela.lista_resultados.count() == len(resultados)
    texto0 = janela.lista_resultados.item(0).text()
    assert "slope_velocity" in texto0
    assert "1450.0 m" in texto0
    assert "v=20.00 m/s" in texto0
    assert "[hydraulic]" in texto0
    # chaves em inglês também formatadas
    assert "warm_back" in janela.lista_resultados.item(2).text()


def test_atualizar_aceita_bandas_pre_separadas(qtbot):
    janela = JanelaAnaliseFluxo(fs_hz=FS_HZ)
    qtbot.addWidget(janela)

    das, dts = _dados_sinteticos()
    janela.atualizar(dts, {"lf": das * 0.001, "hf": das}, [])
    assert janela.viewer_lf._data.shape == (N_T, N_Z)
    assert janela.viewer_hf._data.shape == (N_T, N_Z)
    assert janela.lista_resultados.count() == 0


def test_import_gui_exporta_janela():
    import alakoro.gui

    assert "JanelaAnaliseFluxo" in alakoro.gui.__all__
    assert alakoro.gui.JanelaAnaliseFluxo is JanelaAnaliseFluxo
