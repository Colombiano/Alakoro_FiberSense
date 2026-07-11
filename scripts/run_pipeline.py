#!/usr/bin/env python3
"""
Script para executar o pipeline de processamento
"""

import argparse
import sys
import time
from pathlib import Path

# Adiciona src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "python"))

from controllers import PipelineController
from models import PipelineConfig, ProcessingConfig
from views import DataView, EventView, DashboardView


def run_pipeline(input_file: str, config_file: str = None, output_dir: str = "data/processed"):
    """Executa o pipeline completo"""
    
    print("=" * 60)
    print("  ALAKORO FIBERSENSE - Pipeline de Processamento")
    print("=" * 60)
    
    # Carrega configuracao
    if config_file:
        import yaml
        with open(config_file) as f:
            config_dict = yaml.safe_load(f)
        config = PipelineConfig(**config_dict.get("pipeline", {}))
    else:
        config = PipelineConfig()
    
    config.output_path = output_dir
    
    # Cria controller
    pipeline = PipelineController(config)
    
    # Callbacks
    def on_stage(stage, info):
        print(f"  [Stage] {stage} completo em {info['time']:.2f}s")
    
    def on_complete(data):
        print(f"\n  Pipeline completo!")
        print(f"  Frames: {data.num_frames}")
        if data.metadata:
            events = data.metadata.custom_fields.get("num_events", 0)
            print(f"  Eventos detectados: {events}")
    
    def on_error(error):
        print(f"\n  [ERRO] {error}")
    
    pipeline.on_stage_complete = on_stage
    pipeline.on_pipeline_complete = on_complete
    pipeline.on_error = on_error
    
    # Executa
    start = time.time()
    result = pipeline.run(input_file)
    elapsed = time.time() - start
    
    print(f"\n  Tempo total: {elapsed:.2f}s")
    
    # Visualizacao
    if result.num_frames > 0:
        print("\n  Gerando visualizacoes...")
        
        data_view = DataView()
        concat_data = result.get_concatenated_data()
        
        # Waterfall
        data_view.plot_waterfall(
            concat_data[:5000],
            sample_rate=result.metadata.temporal_sampling if result.metadata else 1000.0,
            title="DAS Waterfall",
            save_path=f"{output_dir}/waterfall.png"
        )
        print(f"  - Waterfall: {output_dir}/waterfall.png")
        
        # Eventos
        events_data = result.metadata.custom_fields.get("events", []) if result.metadata else []
        if events_data:
            event_view = EventView()
            from models import DASEvent
            events = [DASEvent.from_dict(e) for e in events_data]
            print(f"\n  Resumo dos Eventos:")
            print(event_view.render_event_summary(events))
    
    print("\n" + "=" * 60)
    print("  Processamento concluido com sucesso!")
    print("=" * 60)
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Executa pipeline de processamento DAS"
    )
    parser.add_argument("input", help="Arquivo de entrada")
    parser.add_argument("--config", "-c", help="Arquivo de configuracao")
    parser.add_argument("--output", "-o", default="data/processed",
                       help="Diretorio de saida")
    
    args = parser.parse_args()
    
    run_pipeline(args.input, args.config, args.output)


if __name__ == "__main__":
    main()
