-- Alakoro FiberSense — Exemplo de calibração de poço para análise de fluxo
-- Well-calibration example for flow analysis (extra `calibration`).
--
-- O script deve retornar uma tabela com as chaves canônicas consumidas por
-- alakoro.processing.calibration:
--   zonas_calibracao: faixas de profundidade NÃO fraturadas usadas para
--     calibrar o coeficiente de acoplamento strain-temperatura;
--   priors: priors físicos (coeficiente térmico fase→°C, SP:I-03);
--   thresholds: limiares das regras ternárias de discriminação de fluxo
--     (ML:F-04), aplicados em FlowRegressor via aplica_calibracao().
--
-- Poço exemplo: completamento em 1500–1650 m; a zona 1200–1450 m é de
-- coluna íntegra (sem fraturas hidráulicas), usada como referência de
-- calibração do coeficiente de acoplamento.

return {
  poco = "POCO-DEMO-01",
  campo = "Campo Litoral Demo",
  data_calibracao = "2026-11-10",

  -- Zonas de calibração não fraturadas (coluna íntegra / zona de referência)
  zonas_calibracao = {
    {
      inicio_m = 1200.0,
      fim_m = 1450.0,
      fraturada = false,
      justificativa = "Coluna íntegra acima do intervalo completado; fundo térmico estável para calibração do coeficiente de acoplamento."
    },
  },

  -- Priors físicos
  priors = {
    -- Coeficiente térmico fase->temperatura [°C/rad] (SP:I-03).
    -- Literatura LF-DAS/eXDTS: ~0.0028 °C/rad, faixa 0.001-0.005 calibrável por poço.
    coeficiente_acoplamento_c_por_rad = 0.0028,
    faixa_coeficiente = {0.001, 0.005},
  },

  -- Limiares das regras de inferência (ML:F-04); chaves devem corresponder a
  -- atributos de classe do alvo (ex.: FlowRegressor).
  thresholds = {
    velocidade_minima_m_s = 0.5,
    razao_energia_banda_minima = 0.3,
    anomalia_sigma = 3.0,
    banda_discriminacao_hz = {15.0, 100.0},
    snr_min_db = 0.5,
  },
}
