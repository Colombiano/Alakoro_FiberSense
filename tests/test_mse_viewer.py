"""
Testes do visualizador Qt MSE — JanelaVisualizacaoMSE (DTS/DSS/DAS lado a lado).

Roda headless: QT_QPA_PLATFORM=offscreen (padrão de tests/test_gui.py).
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

try:
    from PySide6.QtWidgets import QLabel

    from alakoro.gui.viewers.heatmap_view import HeatmapView
    from alakoro.mse.viewer import JanelaVisualizacaoMSE

    _QT_DISPONIVEL = True
except ImportError:
    _QT_DISPONIVEL = False

pytestmark = pytest.mark.skipif(not _QT_DISPONIVEL, reason="PySide6/pyqtgraph não instalados")

from alakoro.mse import (  # noqa: E402
    ConfigAquisicaoMSE,
    GeometriaEstrutura,
    GeradorAssinaturasMSE,
)


@pytest.fixture
def cenario_curto():
    """Cenário multimodal curto (rápido para teste GUI)."""
    acq = ConfigAquisicaoMSE(n_posicoes=60, passo_espacial_m=1.0,
                             duracao_s=3600.0, fs_das_hz=500.0)
    gerador = GeradorAssinaturasMSE(GeometriaEstrutura(comprimento_fibra_m=60.0), acq, seed=7)
    res = gerador.cenario_fissura_multimodal(30.0, n_eventos_das=3, duracao_janela_das_s=1.0)
    return gerador, res


def test_janela_exibe_tres_viewers(qtbot, cenario_curto):
    gerador, res = cenario_curto
    janela = JanelaVisualizacaoMSE(res, posicoes_fissura_m=[30.0],
                                   eixo_espacial_m=gerador.posicoes)
    qtbot.addWidget(janela)
    janela.show()
    assert janela.isVisible()

    viewers = janela.viewers()
    assert set(viewers) == {"dts", "dss", "das"}
    for chave in ("dts", "dss", "das"):
        viewer = viewers[chave]
        assert isinstance(viewer, HeatmapView)
        assert viewer._data is not None
        assert viewer._data.shape == res[chave].shape
    assert viewers["dts"].plot_item.titleLabel.text == "Temperatura (DTS)"
    assert viewers["dss"].plot_item.titleLabel.text == "Deformação (DSS)"
    assert viewers["das"].plot_item.titleLabel.text == "Acústica (DAS)"


def test_janela_marca_fissuras_e_legenda(qtbot, cenario_curto):
    gerador, res = cenario_curto
    janela = JanelaVisualizacaoMSE(res, posicoes_fissura_m=[30.0],
                                   eixo_espacial_m=gerador.posicoes)
    qtbot.addWidget(janela)
    # linha tracejada em cada viewer + legenda com a posição
    for viewer in janela.viewers().values():
        assert len(getattr(viewer, "_linhas_mse", [])) == 1
        linha = viewer._linhas_mse[0]
        idx_esperado = int(np.argmin(np.abs(gerador.posicoes - 30.0)))
        assert abs(linha.pos().y() - idx_esperado) <= 1.0
    assert "30.0 m" in janela.legenda.text()


def test_posicoes_extraidas_dos_parametros(qtbot, cenario_curto):
    gerador, res = cenario_curto
    # sem posicoes_fissura_m explícitas: usa resultado['parameters']
    janela = JanelaVisualizacaoMSE(res, eixo_espacial_m=gerador.posicoes)
    qtbot.addWidget(janela)
    assert "30.0 m" in janela.legenda.text()


def test_atualizar_resultado_limpa_viewers(qtbot, cenario_curto):
    gerador, res = cenario_curto
    janela = JanelaVisualizacaoMSE(res, eixo_espacial_m=gerador.posicoes)
    qtbot.addWidget(janela)
    so_dts = gerador.difusao_termica_parede()
    janela.atualizar_resultado(so_dts)
    viewers = janela.viewers()
    assert viewers["dts"]._data is not None
    assert viewers["dss"]._data is None and viewers["das"]._data is None
    assert viewers["dss"].plot_item.titleLabel.text == ""
    assert "—" in janela.legenda.text()


def test_lazy_import_sem_qt_no_init():
    """import alakoro.mse não importa PySide6; o viewer é lazy via __getattr__."""
    import subprocess
    import sys

    codigo = (
        "import sys, alakoro.mse;"
        "assert 'PySide6' not in sys.modules, 'PySide6 importado no __init__!';"
        "print('lazy ok')"
    )
    resultado = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr
    assert "lazy ok" in resultado.stdout
