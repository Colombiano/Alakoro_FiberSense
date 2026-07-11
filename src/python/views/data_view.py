"""Data View - Visualizacao de dados DAS"""

from typing import Optional, Dict, Any, List
import numpy as np


class DataView:
    """View para visualizacao de dados DAS"""
    
    def __init__(self):
        self.figure_size = (12, 6)
        self.colormap = "seismic"
        self.colorbar = True
    
    def plot_waterfall(self, data: np.ndarray, sample_rate: float = 1000.0,
                       spatial_sampling: float = 1.0, title: str = "DAS Waterfall",
                       save_path: Optional[str] = None) -> None:
        try:
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=self.figure_size)
            
            extent = [
                0,
                data.shape[1] * spatial_sampling,
                data.shape[0] / sample_rate,
                0
            ]
            
            im = ax.imshow(data, aspect="auto", cmap=self.colormap,
                           extent=extent, interpolation="bilinear")
            
            ax.set_xlabel("Distancia (m)")
            ax.set_ylabel("Tempo (s)")
            ax.set_title(title)
            
            if self.colorbar:
                plt.colorbar(im, ax=ax, label="Amplitude")
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches="tight")
            else:
                plt.show()
                
        except ImportError:
            print("Matplotlib nao disponivel para plotagem")
    
    def plot_channel(self, signal: np.ndarray, sample_rate: float = 1000.0,
                     channel: int = 0, title: Optional[str] = None,
                     save_path: Optional[str] = None) -> None:
        try:
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=self.figure_size)
            
            time = np.arange(len(signal)) / sample_rate
            ax.plot(time, signal, linewidth=0.5)
            
            ax.set_xlabel("Tempo (s)")
            ax.set_ylabel("Amplitude")
            ax.set_title(title or f"Canal {channel}")
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches="tight")
            else:
                plt.show()
                
        except ImportError:
            print("Matplotlib nao disponivel")
    
    def plot_spectrogram(self, signal: np.ndarray, sample_rate: float = 1000.0,
                         window_size: int = 256, hop_size: int = 128,
                         title: str = "Espectrograma", save_path: Optional[str] = None) -> None:
        try:
            import matplotlib.pyplot as plt
            from scipy import signal as sp_signal
            
            fig, ax = plt.subplots(figsize=self.figure_size)
            
            f, t, Sxx = sp_signal.spectrogram(
                signal, fs=sample_rate, window="hann",
                nperseg=window_size, noverlap=window_size - hop_size
            )
            
            im = ax.pcolormesh(t, f, 10 * np.log10(Sxx + 1e-10),
                              shading="gouraud", cmap="viridis")
            
            ax.set_ylabel("Frequencia (Hz)")
            ax.set_xlabel("Tempo (s)")
            ax.set_title(title)
            ax.set_ylim(0, sample_rate / 2)
            
            if self.colorbar:
                plt.colorbar(im, ax=ax, label="Potencia (dB)")
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches="tight")
            else:
                plt.show()
                
        except ImportError:
            print("Bibliotecas nao disponiveis")
    
    def plot_multiple_channels(self, data: np.ndarray, channels: List[int],
                               sample_rate: float = 1000.0,
                               save_path: Optional[str] = None) -> None:
        try:
            import matplotlib.pyplot as plt
            
            n = len(channels)
            fig, axes = plt.subplots(n, 1, figsize=(self.figure_size[0], 2 * n),
                                    sharex=True)
            
            if n == 1:
                axes = [axes]
            
            time = np.arange(data.shape[0]) / sample_rate
            
            for ax, ch in zip(axes, channels):
                ax.plot(time, data[:, ch], linewidth=0.5)
                ax.set_ylabel(f"Ch {ch}")
                ax.grid(True, alpha=0.3)
            
            axes[-1].set_xlabel("Tempo (s)")
            plt.suptitle("Multiplos Canais DAS")
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches="tight")
            else:
                plt.show()
                
        except ImportError:
            print("Matplotlib nao disponivel")
    
    def render_text_summary(self, data: Any) -> str:
        lines = [
            "=" * 50,
            "RESUMO DOS DADOS DAS",
            "=" * 50,
            f"Frames: {data.num_frames if hasattr(data, 'num_frames') else 'N/A'}",
            f"Duracao: {data.duration:.2f}s" if hasattr(data, 'duration') else "",
        ]
        
        if hasattr(data, 'get_statistics'):
            stats = data.get_statistics()
            lines.extend([
                f"Media: {stats.get('mean', 'N/A'):.6f}",
                f"Desvio Padrao: {stats.get('std', 'N/A'):.6f}",
                f"Min: {stats.get('min', 'N/A'):.6f}",
                f"Max: {stats.get('max', 'N/A'):.6f}",
                f"RMS: {stats.get('rms', 'N/A'):.6f}",
            ])
        
        lines.append("=" * 50)
        return "\n".join(lines)
