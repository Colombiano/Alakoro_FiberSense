"""Dashboard View - Painel de monitoramento em tempo real"""

from typing import Optional, Dict, Any, List
from datetime import datetime


class DashboardView:
    """Dashboard para monitoramento do sistema"""
    
    def __init__(self):
        self.refresh_rate_ms = 1000
        self.max_events_display = 50
    
    def render_console_dashboard(self, pipeline_status: Dict[str, Any],
                                  events_summary: Dict[str, Any],
                                  data_stats: Dict[str, Any],
                                  system_metrics: Dict[str, Any]) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        lines = [
            "\033[2J\033[H",
            "=" * 70,
            f"  ALAKORO FIBERSENSE - DASHBOARD              {now}",
            "=" * 70,
            "",
            "[PIPELINE]",
            f"  Status: {'EXECUTANDO' if pipeline_status.get('running') else 'PARADO'}",
            f"  Estagio atual: {pipeline_status.get('current_stage', 'N/A')}",
            f"  Tempo total: {pipeline_status.get('elapsed_time', 0):.2f}s",
            f"  Frames processados: {pipeline_status.get('frames_processed', 0)}",
            "",
            "[EVENTOS]",
            f"  Total detectados: {events_summary.get('total_events', 0)}",
            f"  Media confianca: {events_summary.get('avg_confidence', 0):.3f}",
            f"  Media SNR: {events_summary.get('avg_snr', 0):.1f} dB",
        ]
        
        if "classifications" in events_summary:
            lines.append("  Por tipo:")
            for cls, count in events_summary["classifications"].items():
                lines.append(f"    - {cls}: {count}")
        
        lines.extend([
            "",
            "[DADOS]",
            f"  Frames: {data_stats.get('num_frames', 0)}",
            f"  Duracao: {data_stats.get('duration_seconds', 0):.2f}s",
            f"  Canais: {data_stats.get('num_channels', 'N/A')}",
            f"  Amostras: {data_stats.get('total_samples', 0)}",
            "",
            "[SISTEMA]",
            f"  Eventos processados: {system_metrics.get('events_processed', 0)}",
            f"  Taxa de processamento: {system_metrics.get('processing_rate', 0):.1f} frames/s",
            f"  Memoria: {system_metrics.get('memory_usage', 'N/A')}",
            "",
            "=" * 70,
            "Pressione Ctrl+C para sair",
            "=" * 70,
        ])
        
        return "\n".join(lines)
    
    def render_html_dashboard(self, pipeline_status: Dict[str, Any],
                              events_summary: Dict[str, Any],
                              data_stats: Dict[str, Any]) -> str:
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Alakoro FiberSense - Dashboard</title>
            <meta charset="utf-8">
            <meta http-equiv="refresh" content="5">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #1a1a2e; color: #eee; margin: 0; padding: 20px; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                h1 {{ color: #00d4ff; text-align: center; margin-bottom: 30px; }}
                .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }}
                .card {{ background: #16213e; border-radius: 10px; padding: 20px; border: 1px solid #0f3460; }}
                .card h2 {{ color: #e94560; margin-top: 0; font-size: 1.2em; }}
                .metric {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #0f3460; }}
                .metric:last-child {{ border-bottom: none; }}
                .label {{ color: #a0a0a0; }}
                .value {{ color: #00d4ff; font-weight: bold; }}
                .status-running {{ color: #2ecc71; }}
                .status-stopped {{ color: #e74c3c; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Alakoro FiberSense</h1>
                <div class="grid">
                    <div class="card">
                        <h2>Pipeline</h2>
                        <div class="metric">
                            <span class="label">Status</span>
                            <span class="value {'status-running' if pipeline_status.get('running') else 'status-stopped'}">
                                {'EXECUTANDO' if pipeline_status.get('running') else 'PARADO'}
                            </span>
                        </div>
                        <div class="metric">
                            <span class="label">Estagio</span>
                            <span class="value">{pipeline_status.get('current_stage', 'N/A')}</span>
                        </div>
                        <div class="metric">
                            <span class="label">Tempo</span>
                            <span class="value">{pipeline_status.get('elapsed_time', 0):.2f}s</span>
                        </div>
                        <div class="metric">
                            <span class="label">Frames</span>
                            <span class="value">{pipeline_status.get('frames_processed', 0)}</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Eventos</h2>
                        <div class="metric">
                            <span class="label">Total</span>
                            <span class="value">{events_summary.get('total_events', 0)}</span>
                        </div>
                        <div class="metric">
                            <span class="label">Confianca media</span>
                            <span class="value">{events_summary.get('avg_confidence', 0):.3f}</span>
                        </div>
                        <div class="metric">
                            <span class="label">SNR medio</span>
                            <span class="value">{events_summary.get('avg_snr', 0):.1f} dB</span>
                        </div>
                    </div>
                    
                    <div class="card">
                        <h2>Dados</h2>
                        <div class="metric">
                            <span class="label">Frames</span>
                            <span class="value">{data_stats.get('num_frames', 0)}</span>
                        </div>
                        <div class="metric">
                            <span class="label">Duracao</span>
                            <span class="value">{data_stats.get('duration_seconds', 0):.2f}s</span>
                        </div>
                        <div class="metric">
                            <span class="label">Canais</span>
                            <span class="value">{data_stats.get('num_channels', 'N/A')}</span>
                        </div>
                    </div>
                </div>
                
                <div style="text-align: center; margin-top: 30px; color: #666;">
                    Alakoro FiberSense v1.0.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """
        return html
    
    def render_json_status(self, pipeline_status: Dict[str, Any],
                           events_summary: Dict[str, Any],
                           data_stats: Dict[str, Any]) -> str:
        import json
        return json.dumps({
            "pipeline": pipeline_status,
            "events": events_summary,
            "data": data_stats,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }, indent=2)
