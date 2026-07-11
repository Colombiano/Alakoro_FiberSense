#!/usr/bin/env python3
"""
Script para gerar dados de teste DAS simulados
"""

import argparse
import numpy as np
from pathlib import Path


def generate_synthetic_das(
    num_samples: int = 10000,
    num_channels: int = 1000,
    sample_rate: float = 1000.0,
    noise_level: float = 0.01,
    num_events: int = 5,
    output_path: str = "data/raw/test_das.npy"
):
    """
    Gera dados DAS sinteticos com eventos simulados
    
    Args:
        num_samples: Numero de amostras temporais
        num_channels: Numero de canais espaciais
        sample_rate: Taxa de amostragem em Hz
        noise_level: Nivel de ruido de fundo
        num_events: Numero de eventos a inserir
        output_path: Caminho de saida
    """
    print(f"[Alakoro] Gerando dados DAS sinteticos...")
    print(f"  Dimensao: {num_samples} x {num_channels}")
    print(f"  Taxa: {sample_rate} Hz")
    
    # Ruido de fundo
    data = np.random.randn(num_samples, num_channels) * noise_level
    
    # Insere eventos
    np.random.seed(42)
    
    for i in range(num_events):
        # Localizacao do evento
        t_start = np.random.randint(num_samples // 10, num_samples * 8 // 10)
        duration = np.random.randint(100, 1000)
        ch_start = np.random.randint(0, num_channels - 100)
        num_ch = np.random.randint(20, 100)
        
        # Caracteristicas do evento
        frequency = np.random.uniform(10, 200)
        amplitude = np.random.uniform(0.1, 0.5)
        
        # Gera sinal do evento
        t = np.arange(duration) / sample_rate
        signal = amplitude * np.sin(2 * np.pi * frequency * t)
        
        # Envelope para suavizar inicio/fim
        envelope = np.ones(duration)
        fade_len = min(20, duration // 10)
        envelope[:fade_len] = np.linspace(0, 1, fade_len)
        envelope[-fade_len:] = np.linspace(1, 0, fade_len)
        signal *= envelope
        
        # Insere nos canais
        for ch in range(ch_start, min(ch_start + num_ch, num_channels)):
            t_end = min(t_start + duration, num_samples)
            sig_len = t_end - t_start
            data[t_start:t_end, ch] += signal[:sig_len]
        
        print(f"  Evento {i+1}: freq={frequency:.1f}Hz, "
              f"ch=[{ch_start}-{ch_start+num_ch}], "
              f"t=[{t_start}-{t_start+duration}]")
    
    # Salva
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.save(output, data)
    
    # Salva metadados
    meta_path = output.with_suffix(".json")
    import json
    metadata = {
        "num_samples": num_samples,
        "num_channels": num_channels,
        "sample_rate": sample_rate,
        "gauge_length": 10.2,
        "spatial_sampling": 1.0,
        "unit": "strain_rate",
        "generated_events": num_events
    }
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\n[Alakoro] Dados salvos em: {output}")
    print(f"[Alakoro] Metadados salvos em: {meta_path}")
    print(f"[Alakoro] Tamanho: {data.nbytes / 1024 / 1024:.1f} MB")
    
    return data


def main():
    parser = argparse.ArgumentParser(
        description="Gera dados DAS sinteticos para testes"
    )
    parser.add_argument("--samples", type=int, default=10000,
                       help="Numero de amostras temporais")
    parser.add_argument("--channels", type=int, default=1000,
                       help="Numero de canais")
    parser.add_argument("--sample-rate", type=float, default=1000.0,
                       help="Taxa de amostragem")
    parser.add_argument("--noise", type=float, default=0.01,
                       help="Nivel de ruido")
    parser.add_argument("--events", type=int, default=5,
                       help="Numero de eventos")
    parser.add_argument("--output", type=str, default="data/raw/test_das.npy",
                       help="Caminho de saida")
    
    args = parser.parse_args()
    
    generate_synthetic_das(
        num_samples=args.samples,
        num_channels=args.channels,
        sample_rate=args.sample_rate,
        noise_level=args.noise,
        num_events=args.events,
        output_path=args.output
    )


if __name__ == "__main__":
    main()
