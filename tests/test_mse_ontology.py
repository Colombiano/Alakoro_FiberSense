"""
Alakoro FiberSense — Testes da Ontologia MSE
MSE Ontology Tests
"""

from datetime import datetime

import pytest

from alakoro.ontology import (
    Abobada,
    Alvenaria,
    AnomaliaTermicaEvento,
    AberturaFissuraTermicaEvento,
    Cobertura,
    EdificioEclesiastico,
    ElementoEstrutural,
    Estrutura,
    EventoAcusticoFissura,
    Fundacao,
    Fissura,
    InstalacaoFibra,
    Interrogator,
    OntologyModel,
    PropagacaoFissuraEvento,
    RecalqueEvento,
    TorreSineira,
)


@pytest.fixture
def model():
    return OntologyModel()


class TestEstruturas:
    def test_estrutura_com_elementos_e_fissuras(self, model):
        estrutura = EdificioEclesiastico(
            identifier="Estrutura-01",
            name="Igreja de São Pedro",
            localizacao="Pelourinho, Salvador/BA",
            ano_construcao=1750,
            estado_conservacao="ruina",
            estilo_arquitetonico="barroco",
            diocese="Arquidiocese de São Salvador da Bahia",
            paroquia="São Pedro dos Clérigos",
        )
        torre = TorreSineira(name="Torre-01", altura_m=22.0, n_sinos=2, material="pedra")
        alvenaria = Alvenaria(name="Alvenaria-Fachada-Norte", tipo_alvenaria="tijolo_macico")
        fundacao = Fundacao(name="Fundacao-01", tipo_fundacao="corridas")
        cobertura = Cobertura(name="Cobertura-01", tipo_cobertura="duas_aguas", inclinacao_graus=35.0)
        abobada = Abobada(name="Abobada-01", tipo_abobada="berco", luz_m=8.0)
        fissura = Fissura(name="Fissura-01", posicao_m=32.5, largura_mm=0.4,
                          tipo="transversal", atividade="ativa")
        alvenaria.add_fissura(fissura)

        estrutura.add_elemento(torre)
        estrutura.add_elemento(alvenaria)
        estrutura.add_elemento(fundacao)
        estrutura.add_elemento(cobertura)
        estrutura.add_elemento(abobada)

        model.add(estrutura)
        ttl = model.to_turtle()

        for trecho in [
            "Estrutura-01",
            "Igreja de São Pedro",
            "Pelourinho",
            "1750",
            "ruina",
            "barroco",
            "TorreSineira",
            "Alvenaria",
            "Fundacao",
            "Cobertura",
            "Abobada",
            "Fissura-01",
            "transversal",
            "ativa",
            "tijolo_macico",
            "duas_aguas",
            "berco",
        ]:
            assert trecho in ttl

    def test_numericos_serializam(self, model):
        torre = TorreSineira(name="Torre-02", altura_m=22.0, n_sinos=2)
        fissura = Fissura(name="Fissura-02", posicao_m=32.5, largura_mm=0.4)
        model.add(torre)
        model.add(fissura)
        ttl = model.to_turtle()
        assert "22.0" in ttl
        assert "32.5" in ttl
        assert "0.4" in ttl

    def test_instalacao_fibra_com_interrogador(self, model):
        estrutura = Estrutura(identifier="Estrutura-02", name="Capela de Santo Antônio")
        instalacao = InstalacaoFibra(
            name="Fibra-01",
            comprimento_m=100.0,
            tecnica="colada",
            data_instalacao=datetime(2026, 3, 15, 10, 30, 0),
        )
        interrogador = Interrogator(name="Interrogador-01", manufacturer="Alakoro", model="MSE-Sim")
        estrutura.add_instalacao(instalacao)
        instalacao.interrogador = interrogador

        model.add(estrutura)
        model.add(interrogador)
        ttl = model.to_turtle()

        assert "Fibra-01" in ttl
        assert "colada" in ttl
        assert "InstalacaoFibra" in ttl
        assert "Interrogador-01" in ttl
        assert "2026-03-15T10:30:00" in ttl

    def test_jsonld_contem_estrutura(self, model):
        estrutura = Estrutura(identifier="Estrutura-01", name="Igreja de São Pedro")
        model.add(estrutura)
        jld = model.to_jsonld()
        assert "Estrutura-01" in jld
        assert "Igreja de São Pedro" in jld

    def test_schema_declara_classes_mse(self):
        modelo = OntologyModel()
        ttl = modelo.to_turtle()
        for classe in ["Estrutura", "EdificioEclesiastico", "TorreSineira", "Fissura", "InstalacaoFibra"]:
            assert classe in ttl

    def test_elemento_base_sem_subclasse(self, model):
        elemento = ElementoEstrutural(name="Arco-01", material="pedra")
        model.add(elemento)
        ttl = model.to_turtle()
        assert "Arco-01" in ttl
        assert "pedra" in ttl


class TestEventosMSE:
    def test_eventos_instanciveis_com_kwargs_proprios(self):
        ev1 = PropagacaoFissuraEvento(posicao_fissura_m=32.5, abertura_ue=4200.0,
                                      confidence=0.9, severity="High")
        ev2 = AberturaFissuraTermicaEvento(posicao_m=32.5, variacao_termica_c=12.0, confidence=0.7)
        ev3 = EventoAcusticoFissura(posicao_m=32.5, energia=1.2e-3, taxa_eventos_h=6.0, confidence=0.8)
        ev4 = AnomaliaTermicaEvento(posicao_m=32.5, offset_k=3.0, confidence=0.85)
        ev5 = RecalqueEvento(taxa_ue_dia=5.0, posicao_m=95.0, confidence=0.6)

        assert ev1.posicao_fissura_m == 32.5 and ev1.abertura_ue == 4200.0
        assert ev2.variacao_termica_c == 12.0
        assert ev3.energia == 1.2e-3 and ev3.taxa_eventos_h == 6.0
        assert ev4.offset_k == 3.0
        assert ev5.taxa_ue_dia == 5.0 and ev5.posicao_m == 95.0

    def test_eventos_serializam(self, model):
        eventos = [
            PropagacaoFissuraEvento(posicao_fissura_m=32.5, abertura_ue=4200.0, confidence=0.9),
            AberturaFissuraTermicaEvento(posicao_m=32.5, variacao_termica_c=12.0),
            EventoAcusticoFissura(posicao_m=32.5, energia=1.2e-3, taxa_eventos_h=6.0),
            AnomaliaTermicaEvento(posicao_m=32.5, offset_k=3.0),
            RecalqueEvento(taxa_ue_dia=5.0, posicao_m=95.0),
        ]
        for evento in eventos:
            model.add(evento)
        ttl = model.to_turtle()

        assert "CrackPropagation" in ttl
        assert "4200.0" in ttl
        assert "ThermalCrackOpening" in ttl
        assert "CrackAcousticEmission" in ttl
        assert "ThermalAnomaly" in ttl
        assert "DifferentialSettlement" in ttl
        assert "PropagacaoFissuraEvento" in ttl
        assert "AnomaliaTermicaEvento" in ttl
        assert "RecalqueEvento" in ttl
