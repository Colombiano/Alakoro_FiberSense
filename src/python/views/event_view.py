"""Event View - Visualizacao de eventos detectados"""

from typing import List, Optional
import numpy as np

from ..models import DASEvent, EventClassification


class EventView:
    """View para visualizacao de eventos"""
    
    def __init__(self):
        self.color_map = {
            EventClassification.VIBRATION: "#3498db",
            EventClassification.FRACTURE: "#e74c3c",
            EventClassification.FLOW: "#2ecc71",
            EventClassification.LEAK: "#f39c12",
            EventClassification.CUSTOM: "#9b59b6",
            EventClassification.UNKNOWN: "#95a5a6",
        }
    
    def plot_events_timeline(self, events: List[DASEvent],
                             title: str = "Timeline de Eventos",
                             save_path: Optional[str] = None) -> None:
        try:
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(14, 6))
            
            for event in events:
                color = self.color_map.get(event.classification, "#95a5a6")
                ax.scatter(event.timestamp, event.channel_start,
                          c=color, s=event.confidence * 100,
                          alpha=0.6, edgecolors="black", linewidth=0.5)
            
            ax.set_xlabel("Tempo (s)")
            ax.set_ylabel("Canal")
            ax.set_title(title)
            ax.grid(True, alpha=0.3)
            
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor=color, label=cls.value)
                for cls, color in self.color_map.items()
            ]
            ax.legend(handles=legend_elements, loc="upper right")
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches="tight")
            else:
                plt.show()
                
        except ImportError:
            print("Matplotlib nao disponivel")
    
    def plot_event_waveform(self, event: DASEvent,
                            save_path: Optional[str] = None) -> None:
        if event.waveform is None:
            print("Evento sem waveform")
            return
        
        try:
            import matplotlib.pyplot as plt
            
            fig, axes = plt.subplots(2, 1, figsize=(10, 6))
            
            time = np.arange(len(event.waveform))
            axes[0].plot(time, event.waveform, linewidth=0.8)
            axes[0].set_ylabel("Amplitude")
            axes[0].set_title(f"Evento {event.event_id} - {event.classification.value}")
            axes[0].grid(True, alpha=0.3)
            
            spectrum = np.abs(np.fft.fft(event.waveform))
            freqs = np.fft.fftfreq(len(event.waveform))
            positive_freqs = freqs[:len(freqs)//2]
            positive_spectrum = spectrum[:len(spectrum)//2]
            
            axes[1].plot(positive_freqs, positive_spectrum, linewidth=0.8)
            axes[1].set_xlabel("Frequencia (Hz)")
            axes[1].set_ylabel("Magnitude")
            axes[1].set_title("Espectro")
            axes[1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches="tight")
            else:
                plt.show()
                
        except ImportError:
            print("Matplotlib nao disponivel")
    
    def plot_classification_distribution(self, events: List[DASEvent],
                                         save_path: Optional[str] = None) -> None:
        try:
            import matplotlib.pyplot as plt
            from collections import Counter
            
            classifications = [e.classification for e in events]
            counts = Counter(classifications)
            
            labels = [cls.value for cls in counts.keys()]
            values = list(counts.values())
            colors = [self.color_map.get(cls, "#95a5a6") for cls in counts.keys()]
            
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.bar(labels, values, color=colors, edgecolor="black", linewidth=0.5)
            ax.set_xlabel("Classificacao")
            ax.set_ylabel("Contagem")
            ax.set_title("Distribuicao de Eventos")
            ax.grid(True, alpha=0.3, axis="y")
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches="tight")
            else:
                plt.show()
                
        except ImportError:
            print("Matplotlib nao disponivel")
    
    def render_event_summary(self, events: List[DASEvent]) -> str:
        lines = [
            "=" * 50,
            "RESUMO DOS EVENTOS DETECTADOS",
            "=" * 50,
            f"Total de eventos: {len(events)}",
            "",
        ]
        
        from collections import defaultdict
        by_class = defaultdict(list)
        for e in events:
            by_class[e.classification.value].append(e)
        
        for cls, evts in sorted(by_class.items()):
            lines.append(f"\n{cls.upper()}: {len(evts)} eventos")
            lines.append("-" * 30)
            for e in evts[:5]:
                lines.append(
                    f"  [{e.event_id}] t={e.timestamp:.3f}s "
                    f"ch=[{e.channel_start}-{e.channel_end}] "
                    f"conf={e.confidence:.2f} snr={e.snr:.1f}dB"
                )
            if len(evts) > 5:
                lines.append(f"  ... e mais {len(evts) - 5} eventos")
        
        lines.append("\n" + "=" * 50)
        return "\n".join(lines)
