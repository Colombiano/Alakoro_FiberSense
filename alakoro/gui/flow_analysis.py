"""
Alakoro FiberSense — Janela de Análise de Fluxo (Onda 2)
Flow Analysis Window (Wave 2)

Autor/Author: Luiz Paulo Colombiano
Licença/License: MIT

Visualização multimodal das bandas LF-DAS / HF-DAS / DTS lado a lado com o
painel de resultados do motor de inferência (tipo, profundidade, velocidade,
discriminação). Reutiliza o HeatmapView de alakoro.gui.viewers.heatmap_view.

Multimodal visualization of the LF-DAS / HF-DAS / DTS bands side by side
with the inference-engine results panel. Reuses HeatmapView.

Requer o extra `gui` (PySide6 + PyQtGraph): pip install alakoro-fibersense[gui]
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence

import numpy as np

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QHBoxLayout,
        QListWidget,
        QMainWindow,
        QSplitter,
        QVBoxLayout,
        QWidget,
    )

    from alakoro.gui.viewers.heatmap_view import HeatmapView
except ImportError as exc:  # pragma: no cover - extra opcional
    raise ImportError(
        "Dependências de GUI não instaladas. Instale com: "
        "pip install alakoro-fibersense[gui]   (PySide6 + PyQtGraph)"
    ) from exc


class JanelaAnaliseFluxo(QMainWindow):
    """
    Janela de análise de fluxo: três HeatmapView (LF-DAS filtrado, HF-DAS e
    DTS) lado a lado, mais QListWidget inferior com os resultados do motor
    (tipo, profundidade, velocidade, discriminação). / Flow-analysis window:
    three side-by-side HeatmapViews (filtered LF-DAS, HF-DAS and DTS) plus a
    bottom QListWidget with the engine results (type, depth, velocity,
    discrimination).
    """

    def __init__(self, parent=None, fs_hz: float = 1000.0):
        """
        Args:
            parent: Widget pai / parent widget.
            fs_hz: Taxa de amostragem usada para separar DAS em LF/HF quando
                `atualizar` recebe um array DAS bruto / Sampling rate used to
                split raw DAS into LF/HF bands in `atualizar`.
        """
        super().__init__(parent)
        self.fs_hz = float(fs_hz)
        self.setWindowTitle("Alakoro FiberSense — Análise de Fluxo / Flow Analysis")

        central = QWidget()
        layout = QVBoxLayout(central)

        # Três viewers lado a lado / three side-by-side viewers
        splitter = QSplitter(Qt.Horizontal)
        self.viewer_lf = HeatmapView()
        self.viewer_hf = HeatmapView()
        self.viewer_dts = HeatmapView()
        for viewer, titulo in (
            (self.viewer_lf, "LF-DAS (0.05–1.0 Hz)"),
            (self.viewer_hf, "HF-DAS (> 1 Hz)"),
            (self.viewer_dts, "DTS"),
        ):
            holder = QWidget()
            hbox = QVBoxLayout(holder)
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.addWidget(viewer)
            splitter.addWidget(holder)
        splitter.setSizes([1, 1, 1])
        layout.addWidget(splitter, stretch=3)

        # Painel inferior com os resultados do motor / bottom results panel
        self.lista_resultados = QListWidget()
        layout.addWidget(self.lista_resultados, stretch=1)

        self.setCentralWidget(central)
        self.resize(1200, 700)

    # ─── API pública / public API ───

    def atualizar(self,
                  dts: np.ndarray,
                  das: np.ndarray,
                  resultados: Sequence[Dict]) -> None:
        """
        Atualiza os três viewers e a lista de resultados.

        Args:
            dts: Array 2D (time, depth) DTS em °C / DTS array in °C.
            das: Array 2D (time, channels) DAS. Pode ser um dict com as
                bandas já separadas: {"lf": ..., "hf": ...}; caso contrário o
                array é dividido internamente em LF (0.05–1.0 Hz) e HF
                (> 1 Hz) com `fs_hz` do construtor. / Raw DAS array (split
                internally) or pre-split dict with "lf"/"hf" bands.
            resultados: Sequência de dicts com os campos "tipo" (ou "type"),
                "profundidade_m" (ou "depth_m"), "velocidade_ms" (ou
                "velocity_ms") e "discriminacao" (ou "discrimination").
        """
        dts = np.asarray(dts, dtype=np.float64)

        if isinstance(das, dict):
            lf = np.asarray(das["lf"], dtype=np.float64)
            hf = np.asarray(das["hf"], dtype=np.float64)
        else:
            from alakoro.processing.advanced_processors import (
                extract_hf_das,
                extract_lfdas,
            )

            das_arr = np.asarray(das, dtype=np.float64)
            lf = extract_lfdas(das_arr, fs_hz=self.fs_hz)
            hf = extract_hf_das(das_arr, fs_hz=self.fs_hz)

        self.viewer_lf.set_data(lf, title="LF-DAS (0.05–1.0 Hz)")
        self.viewer_hf.set_data(hf, title="HF-DAS (> 1 Hz)")
        self.viewer_dts.set_data(dts, title="DTS")

        self.lista_resultados.clear()
        for r in resultados or []:
            self.lista_resultados.addItem(self._formata_resultado(r))

    @staticmethod
    def _formata_resultado(r: Dict) -> str:
        tipo = r.get("tipo") or r.get("type") or r.get("event_type") or "evento"
        profundidade = r.get("profundidade_m", r.get("depth_m", r.get("profundidade")))
        velocidade = r.get("velocidade_ms", r.get("velocity_ms", r.get("velocidade")))
        discriminacao = r.get("discriminacao", r.get("discrimination", "—"))

        partes = [str(tipo)]
        if profundidade is not None:
            partes.append(f"@{float(profundidade):.1f} m")
        if velocidade is not None:
            partes.append(f"v={float(velocidade):.2f} m/s")
        partes.append(f"[{discriminacao}]")
        return " ".join(partes)


def main() -> None:  # pragma: no cover - demonstração interativa
    """Demo com dados sintéticos curtos / Short synthetic-data demo."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])

    rng = np.random.default_rng(7)
    n_t, n_z, fs = 2000, 64, 1000.0
    t = np.arange(n_t) / fs
    z = np.arange(n_z, dtype=float)

    # Evento descendente coerente + conteúdo de banda
    atrasos = z / 25.0
    dt = t[:, None] - atrasos[None, :]
    das = np.exp(-0.5 * (dt / 0.02) ** 2) * np.sin(2.0 * np.pi * 40.0 * dt)
    das += rng.normal(0.0, 0.05, (n_t, n_z))

    # DTS com anomalia quente localizada
    dts = 20.0 + 0.03 * z[None, :] + rng.normal(0.0, 0.02, (n_t, n_z))
    dts[:, 24:40] += 6.0

    resultados = [
        {"tipo": "slope_velocity", "profundidade_m": 1450.0,
         "velocidade_ms": 25.0, "discriminacao": "hydraulic"},
        {"tipo": "joule_thomson", "profundidade_m": 1200.0,
         "velocidade_ms": None, "discriminacao": "thermal"},
    ]

    janela = JanelaAnaliseFluxo(fs_hz=fs)
    janela.atualizar(dts, das, resultados)
    janela.show()
    app.exec()


if __name__ == "__main__":  # pragma: no cover
    main()


__all__ = ["JanelaAnaliseFluxo", "main"]
