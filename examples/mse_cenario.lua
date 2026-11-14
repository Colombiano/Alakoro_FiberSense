-- Ruína de Igreja Colonial — demonstração
-- ========================================
--
-- Cenário do módulo MSE (Monitoramento da Saúde Estrutural) para o
-- Alakoro FiberSense. A fibra percorre a fachada, o corpo da nave e a
-- torre sineira de uma igreja em ruína, monitorando duas fissuras ativas.
--
-- Parâmetros físicos e referências da literatura:
--   * Difusão térmica 1D em alvenaria (Owczarek 2021):
--       alpha = 5e-7 m²/s (faixa 3.5e-7–1e-6 m²/s)
--       ciclo diário: omega = 7.272e-5 rad/s (T = 86400 s)
--       penetração delta = sqrt(2*alpha/omega) ≈ 0.117 m
--       amplitude superficial diária A0 = 15–35 K (usamos 20 K)
--       componente anual: A0 = 15–25 K, delta ≈ 2.24 m (opcional)
--   * Fissura ativa em Brillouin/DSS (Glisic & Inaudi 2012):
--       pico localizado de 3500–5000 µε = w/L_t, com w = 0.35–0.5 mm
--       sobre comprimento de transferência L_t ≈ 10 cm; largura espacial
--       do pico ~2×L_SR (L_SR = resolução espacial, 1 m).
--   * Cross-sensibilidade térmica do Brillouin (Hubbard 2021; Di Gennaro 2025):
--       20 µε/°C — 1 °C ≡ 20 µε aparentes em TODO o traço DSS.
--   * Coeficiente de dilatação térmica do tijolo: 4–8e-6/°C (usamos 5.6e-6).
--   * Emissão acústica de fissura (DAS): impulsos 50–500 Hz, 10–200 ms,
--       degrau permanente quase-estático de 5–250 µε por evento; ringing
--       modal de torres de alvenaria em 1–5 Hz (torção ~2–2.5×f1,
--       amortecimento 1–5%).
--
-- O script retorna uma tabela Lua convertida em dict Python por
-- alakoro.mse.cenarios.carrega_cenario_lua().

local N = 400  -- posições ao longo de 100 m (passo 0.25 m)

-- Profundidade de instalação da fibra na parede (m), crescente ao longo
-- do percurso: fachada (raso) -> interno (mais embutido). Alimenta a
-- solução analítica A(x) = A0*e^(-x/delta), defasagem dt(x) = x/(delta*omega).
local profundidade = {}
for i = 1, N do
  profundidade[i] = 0.02 + 0.10 * (i / N)
end

return {
  nome = "Ruína de Igreja Colonial — demonstração",
  descricao = "Igreja barroca em ruína (séc. XVIII) com duas fissuras ativas monitoradas por DFOS.",

  geometria = {
    comprimento_fibra_m = 100.0,
    trechos = {
      -- fibra colada na fachada sul: sol pleno (fator 1.0)
      { inicio_m = 0.0,  fim_m = 30.0,  exposicao = 1.0,  orientacao = "sul" },
      -- corpo da nave, fachada norte: sol fraco da manhã (fator 0.4)
      { inicio_m = 30.0, fim_m = 55.0,  exposicao = 0.4,  orientacao = "norte" },
      -- interior até a torre sineira: quase sem insolação direta
      { inicio_m = 55.0, fim_m = 100.0, exposicao = 0.15, orientacao = "interno_torre" },
    },
    profundidade_posicoes = profundidade,
  },

  material = {
    nome = "tijolo_macico",
    coef_expansao_termica = 5.6e-6,  -- 1/°C (faixa 4–8e-6 para alvenaria de tijolo)
  },

  fissuras = {
    -- fissura transversal ativa na fachada sul (0.4 mm => pico ~4000 µε com L_t = 0.1 m)
    { posicao_m = 32.0, largura_mm = 0.40, tipo = "transversal",  atividade = "ativa" },
    -- fissura longitudinal estável junto à torre sineira
    { posicao_m = 71.5, largura_mm = 0.15, tipo = "longitudinal", atividade = "estavel" },
  },

  aquisicao = {
    n_posicoes = N,                 -- 400 posições em 100 m
    passo_espacial_m = 0.25,
    fs_dts_hz = 1.0 / 60.0,         -- 1 traço/minuto (campanha de 24 h)
    fs_dss_hz = 1.0 / 60.0,
    fs_das_hz = 1000.0,             -- DAS acústico a 1 kHz (janela curta)
    duracao_s = 86400.0,            -- 1 dia de campanha
  },

  gerador = {
    tipo = "cenario_fissura_multimodal",
    posicao_fissura_m = 32.0,       -- fissura ativa (mesma posição nas 3 modalidades)
    abertura_mm = 0.40,             -- w = 0.4 mm => ~4000 µε sobre L_t = 0.1 m
    taxa_creep_ue_dia = 10.0,       -- creep 1–50 µε/dia (faixa da literatura)
    offset_ponte_k = 3.0,           -- ponte térmica: offset persistente 1–5 K
    n_eventos_das = 8,              -- taxa ativa 1–30 eventos/h (janela curta)
    degrau_ue = 100.0,              -- degrau permanente 5–250 µε por evento
    incluir_termico = true,         -- cross-sensibilidade Brillouin 20 µε/°C
    duracao_janela_das_s = 30.0,    -- janela DAS (campanha completa seria 100+ GB)
    alpha = 5e-7,                   -- difusividade térmica da alvenaria (Owczarek 2021)
    amplitude_superficial_k = 20.0, -- A0 diário 15–35 K
  },
}
