"""
Alakoro FiberSense — Visualizador Qt do Módulo MSE
MSE Module Qt Viewer

Janela de visualização lado a lado das três modalidades DFOS
(DTS/DSS/DAS) a partir do dicionário canônico do gerador de assinaturas,
reutilizando o `HeatmapView` da GUI desktop (pyqtgraph).

Side-by-side viewer of the three DFOS modalities (DTS/DSS/DAS) from the
canonical signature dict, reusing the desktop GUI's `HeatmapView`
(pyqtgraph).

Autor/Author: Luiz Paulo Colombiano
Licença/License: MIT
"""

from typing import Dict, List, Optional, Sequence

import numpy as np

try:
    import pyqtgraph as pg
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QApplication,
        QLabel,
        QMainWindow,
        QSplitter,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - depende do ambiente
    raise ImportError(
        "O visualizador MSE precisa das dependências de GUI (PySide6/pyqtgraph). "
        "Instale-as com: pip install alakoro-fibersense[gui]"
    ) from exc

from ..gui.viewers.heatmap_view import HeatmapView
from .signatures import GeradorAssinaturasMSE


class JanelaVisualizacaoMSE(QMainWindow):
    """Janela DTS+DSS+DAS lado a lado para assinaturas MSE /
    Side-by-side DTS+DSS+DAS window for MSE signatures.

    Parameters
    ----------
    resultado : dict, opcional
        Dicionário canônico do `GeradorAssinaturasMSE` (chaves 'dts',
        'dss', 'das'). Modalidades None ficam com o heatmap vazio.
    posicoes_fissura_m : list[float], opcional
        Posições de fissuras a marcar (linhas tracejadas no eixo espacial
        e legenda). Quando omitido, usa `resultado['parameters']
        ['posicao_fissura_m']` (ou dos componentes), se presente.
    eixo_espacial_m : np.ndarray, opcional
        Eixo espacial em metros (uma entrada por canal), usado para
        converter posições de fissura em índices de canal. Sem ele,
        assume-se eixo uniforme 0..n_z−1 em metros.
    parent : QWidget, opcional
        Widget pai Qt.

    Notes
    -----
    O `HeatmapView` exibe o eixo espacial na vertical (linhas = canais),
    de modo que a marcação de uma posição de fissura é uma linha
    horizontal tracejada sobre o eixo da fibra, acompanhada de legenda.
    """

    TITULOS = (
        ("dts", "Temperatura (DTS)"),
        ("dss", "Deformação (DSS)"),
        ("das", "Acústica (DAS)"),
    )

    def __init__(self, resultado: Optional[Dict] = None,
                 posicoes_fissura_m: Optional[Sequence[float]] = None,
                 eixo_espacial_m: Optional[np.ndarray] = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Alakoro FiberSense — Visualização MSE (DTS / DSS / DAS)")

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(6, 6, 6, 6)

        self.legenda = QLabel("Fissuras: —")
        self.legenda.setWordWrap(True)
        layout.addWidget(self.legenda)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.viewer_dts = HeatmapView()
        self.viewer_dss = HeatmapView()
        self.viewer_das = HeatmapView()
        self._viewers = {
            "dts": self.viewer_dts,
            "dss": self.viewer_dss,
            "das": self.viewer_das,
        }
        for viewer in self._viewers.values():
            self.splitter.addWidget(viewer)
        self.splitter.setSizes([400, 400, 400])
        layout.addWidget(self.splitter)

        self.setCentralWidget(central)
        self._eixo_espacial_m = None if eixo_espacial_m is None else np.asarray(eixo_espacial_m, dtype=float)

        if resultado is not None:
            self.atualizar_resultado(resultado, posicoes_fissura_m=posicoes_fissura_m)

    # ─────────────────────────────────────────────────────────
    # API PÚBLICA / PUBLIC API
    # ─────────────────────────────────────────────────────────

    def atualizar_resultado(self, resultado: Dict,
                            posicoes_fissura_m: Optional[Sequence[float]] = None) -> None:
        """Atualiza os três heatmaps com um novo dicionário canônico /
        Refreshes the three heatmaps with a new canonical dict."""
        posicoes = self._extrair_posicoes_fissura(resultado, posicoes_fissura_m)
        for chave, titulo in self.TITULOS:
            viewer = self._viewers[chave]
            dados = resultado.get(chave)
            self._remover_marcas(viewer)
            if dados is None:
                viewer.clear()
                viewer.plot_item.setTitle("")
                continue
            viewer.set_data(np.asarray(dados, dtype=float), title=titulo)
            for pos_m in posicoes:
                self._marcar_fissura(viewer, dados, pos_m)
        self._atualizar_legenda(posicoes)

    def set_eixo_espacial(self, eixo_espacial_m: np.ndarray) -> None:
        """Define o eixo espacial (m) usado para marcar posições de fissura /
        Sets the spatial axis (m) used for crack-position markers."""
        self._eixo_espacial_m = np.asarray(eixo_espacial_m, dtype=float)

    # ─────────────────────────────────────────────────────────
    # MARCAS DE FISSURA / CRACK MARKERS
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def _extrair_posicoes_fissura(resultado: Dict,
                                  posicoes_fissura_m: Optional[Sequence[float]]) -> List[float]:
        """Resolve a lista de posições de fissura (argumento > parâmetros) /
        Resolves the crack-position list (argument > parameters)."""
        if posicoes_fissura_m is not None:
            return [float(p) for p in posicoes_fissura_m]
        params = resultado.get("parameters") or {}
        if params.get("posicao_fissura_m") is not None:
            return [float(params["posicao_fissura_m"])]
        posicoes = []
        for params_componente in (params.get("componentes") or {}).values():
            valor = (params_componente or {}).get("posicao_fissura_m")
            if valor is not None and float(valor) not in posicoes:
                posicoes.append(float(valor))
        return posicoes

    def _marcar_fissura(self, viewer: HeatmapView, dados: np.ndarray, pos_m: float) -> None:
        """Adiciona linha tracejada na posição da fissura (eixo espacial) /
        Adds a dashed line at the crack position (spatial axis).

        A posição em metros é convertida no índice de canal mais próximo;
        sem eixo espacial definido, assume-se eixo uniforme 0..n_z−1 em
        metros (índice = posição).
        """
        n_z = dados.shape[1]
        if self._eixo_espacial_m is not None and self._eixo_espacial_m.shape[0] == n_z:
            idx = int(np.argmin(np.abs(self._eixo_espacial_m - pos_m)))
        else:
            idx = int(round(pos_m))
        idx = min(max(idx, 0), n_z - 1)
        linha = pg.InfiniteLine(
            pos=idx,
            angle=0,
            pen=pg.mkPen((255, 60, 60), width=2, style=Qt.PenStyle.DashLine),
        )
        viewer.plot_item.addItem(linha)
        viewer._linhas_mse = getattr(viewer, "_linhas_mse", [])
        viewer._linhas_mse.append(linha)

    @staticmethod
    def _remover_marcas(viewer: HeatmapView) -> None:
        """Remove as linhas de fissura previamente adicionadas ao viewer /
        Removes previously added crack lines from the viewer."""
        for linha in getattr(viewer, "_linhas_mse", []):
            viewer.plot_item.removeItem(linha)
        viewer._linhas_mse = []

    def _atualizar_legenda(self, posicoes: Sequence[float]) -> None:
        if posicoes:
            texto = "Fissuras: " + " · ".join(f"{p:.1f} m" for p in posicoes)
        else:
            texto = "Fissuras: —"
        self.legenda.setText(texto)

    # ─────────────────────────────────────────────────────────
    # ACESSO AOS VIEWERS / VIEWER ACCESS
    # ─────────────────────────────────────────────────────────

    def viewers(self) -> Dict[str, HeatmapView]:
        """Retorna os três viewers indexados por modalidade /
        Returns the three viewers keyed by modality."""
        return dict(self._viewers)


def main() -> None:
    """Ponto de entrada do visualizador MSE / MSE viewer entry point."""
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    gerador = GeradorAssinaturasMSE(seed=42)
    resultado = gerador.cenario_fissura_multimodal(50.0, n_eventos_das=6)
    posicoes = [resultado["parameters"]["posicao_fissura_m"]]
    janela = JanelaVisualizacaoMSE(resultado, posicoes_fissura_m=posicoes,
                                   eixo_espacial_m=gerador.posicoes)
    janela.resize(1500, 620)
    janela.show()
    sys.exit(app.exec())


if __name__ == "__main__":  # pragma: no cover
    main()
