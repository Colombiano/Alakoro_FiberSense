"""
Alakoro FiberSense — Classes de Domínio MSE (Edifícios Antigos)
MSE Domain Classes (Heritage Buildings)

Estruturas civis/eclesiásticas monitoradas, seus elementos estruturais
(alvenaria, fundação, torre sineira, cobertura, abóbada), fissuras e
instalações de fibra óptica — paralelas às classes de poço de petróleo.

Monitored civil/ecclesiastical structures, their structural elements
(masonry, foundation, bell tower, roof, vault), cracks and fiber optic
installations — parallel to the petroleum well classes.
"""

from datetime import datetime
from typing import List, Optional

from rdflib import Graph, Literal, XSD

from .core import ALAKORO, AlakoroEntity
from .sensing import Interrogator


class Estrutura(AlakoroEntity):
    """Estrutura monitorada (paralela a Well) / Monitored structure (parallel to Well)."""

    _type = ALAKORO.Estrutura

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 description: Optional[str] = None, localizacao: Optional[str] = None,
                 ano_construcao: Optional[int] = None, estado_conservacao: Optional[str] = None):
        super().__init__(identifier=identifier, name=name, description=description)
        self.localizacao = localizacao
        self.ano_construcao = ano_construcao
        self.estado_conservacao = estado_conservacao
        self.elementos: List[ElementoEstrutural] = []
        self.instalacoes: List[InstalacaoFibra] = []

    def add_elemento(self, elemento: "ElementoEstrutural"):
        self.elementos.append(elemento)
        elemento.estrutura = self

    def add_instalacao(self, instalacao: "InstalacaoFibra"):
        self.instalacoes.append(instalacao)
        instalacao.estrutura = self

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.localizacao:
            graph.add((self.uri, ALAKORO.hasLocalizacao, Literal(self.localizacao)))
        if self.ano_construcao is not None:
            graph.add((self.uri, ALAKORO.hasAnoConstrucao, Literal(int(self.ano_construcao), datatype=XSD.integer)))
        if self.estado_conservacao:
            graph.add((self.uri, ALAKORO.hasEstadoConservacao, Literal(self.estado_conservacao)))
        for elemento in self.elementos:
            elemento._attach(graph)
            graph.add((self.uri, ALAKORO.hasElemento, elemento.uri))
        for instalacao in self.instalacoes:
            instalacao._attach(graph)
            graph.add((self.uri, ALAKORO.hasInstalacaoFibra, instalacao.uri))


class EdificioEclesiastico(Estrutura):
    """Edifício eclesiástico (igreja, capela) / Ecclesiastical building (church, chapel)."""

    _type = ALAKORO.EdificioEclesiastico

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 description: Optional[str] = None, localizacao: Optional[str] = None,
                 ano_construcao: Optional[int] = None, estado_conservacao: Optional[str] = None,
                 estilo_arquitetonico: Optional[str] = None, diocese: Optional[str] = None,
                 paroquia: Optional[str] = None):
        super().__init__(identifier=identifier, name=name, description=description,
                         localizacao=localizacao, ano_construcao=ano_construcao,
                         estado_conservacao=estado_conservacao)
        self.estilo_arquitetonico = estilo_arquitetonico
        self.diocese = diocese
        self.paroquia = paroquia

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.estilo_arquitetonico:
            graph.add((self.uri, ALAKORO.hasEstiloArquitetonico, Literal(self.estilo_arquitetonico)))
        if self.diocese:
            graph.add((self.uri, ALAKORO.hasDiocese, Literal(self.diocese)))
        if self.paroquia:
            graph.add((self.uri, ALAKORO.hasParoquia, Literal(self.paroquia)))


class ElementoEstrutural(AlakoroEntity):
    """Elemento estrutural de uma edificação / Structural element of a building."""

    _type = ALAKORO.ElementoEstrutural

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 description: Optional[str] = None, material: Optional[str] = None,
                 data_ultima_inspecao: Optional[datetime] = None):
        super().__init__(identifier=identifier, name=name, description=description)
        self.material = material
        self.data_ultima_inspecao = data_ultima_inspecao
        self.estrutura: Optional[Estrutura] = None
        self.fissuras: List[Fissura] = []

    def add_fissura(self, fissura: "Fissura"):
        self.fissuras.append(fissura)
        fissura.elemento = self

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.material:
            graph.add((self.uri, ALAKORO.hasMaterial, Literal(self.material)))
        if self.data_ultima_inspecao:
            graph.add((self.uri, ALAKORO.hasDataUltimaInspecao,
                       Literal(self.data_ultima_inspecao.isoformat(), datatype=XSD.dateTime)))
        if self.estrutura is not None:
            graph.add((self.uri, ALAKORO.isElementoOf, self.estrutura.uri))
        for fissura in self.fissuras:
            fissura._attach(graph)
            graph.add((self.uri, ALAKORO.hasFissura, fissura.uri))


class Alvenaria(ElementoEstrutural):
    """Parede de alvenaria / Masonry wall."""

    _type = ALAKORO.Alvenaria

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 description: Optional[str] = None, material: Optional[str] = None,
                 data_ultima_inspecao: Optional[datetime] = None,
                 tipo_alvenaria: Optional[str] = None):
        super().__init__(identifier=identifier, name=name, description=description,
                         material=material, data_ultima_inspecao=data_ultima_inspecao)
        self.tipo_alvenaria = tipo_alvenaria

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.tipo_alvenaria:
            graph.add((self.uri, ALAKORO.hasTipoAlvenaria, Literal(self.tipo_alvenaria)))


class Fundacao(ElementoEstrutural):
    """Fundação de edificação / Building foundation."""

    _type = ALAKORO.Fundacao

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 description: Optional[str] = None, material: Optional[str] = None,
                 data_ultima_inspecao: Optional[datetime] = None,
                 tipo_fundacao: Optional[str] = None):
        super().__init__(identifier=identifier, name=name, description=description,
                         material=material, data_ultima_inspecao=data_ultima_inspecao)
        self.tipo_fundacao = tipo_fundacao

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.tipo_fundacao:
            graph.add((self.uri, ALAKORO.hasTipoFundacao, Literal(self.tipo_fundacao)))


class TorreSineira(ElementoEstrutural):
    """Torre sineira / Bell tower."""

    _type = ALAKORO.TorreSineira

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 description: Optional[str] = None, material: Optional[str] = None,
                 data_ultima_inspecao: Optional[datetime] = None,
                 altura_m: Optional[float] = None, n_sinos: Optional[int] = None):
        super().__init__(identifier=identifier, name=name, description=description,
                         material=material, data_ultima_inspecao=data_ultima_inspecao)
        self.altura_m = altura_m
        self.n_sinos = n_sinos

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.altura_m is not None:
            graph.add((self.uri, ALAKORO.hasAlturaM, Literal(self.altura_m, datatype=XSD.float)))
        if self.n_sinos is not None:
            graph.add((self.uri, ALAKORO.hasNumeroSinos, Literal(int(self.n_sinos), datatype=XSD.integer)))


class Cobertura(ElementoEstrutural):
    """Cobertura (telhado) / Roof."""

    _type = ALAKORO.Cobertura

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 description: Optional[str] = None, material: Optional[str] = None,
                 data_ultima_inspecao: Optional[datetime] = None,
                 tipo_cobertura: Optional[str] = None, inclinacao_graus: Optional[float] = None):
        super().__init__(identifier=identifier, name=name, description=description,
                         material=material, data_ultima_inspecao=data_ultima_inspecao)
        self.tipo_cobertura = tipo_cobertura
        self.inclinacao_graus = inclinacao_graus

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.tipo_cobertura:
            graph.add((self.uri, ALAKORO.hasTipoCobertura, Literal(self.tipo_cobertura)))
        if self.inclinacao_graus is not None:
            graph.add((self.uri, ALAKORO.hasInclinacaoGraus,
                       Literal(self.inclinacao_graus, datatype=XSD.float)))


class Abobada(ElementoEstrutural):
    """Abóbada / Vault."""

    _type = ALAKORO.Abobada

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 description: Optional[str] = None, material: Optional[str] = None,
                 data_ultima_inspecao: Optional[datetime] = None,
                 tipo_abobada: Optional[str] = None, luz_m: Optional[float] = None):
        super().__init__(identifier=identifier, name=name, description=description,
                         material=material, data_ultima_inspecao=data_ultima_inspecao)
        self.tipo_abobada = tipo_abobada
        self.luz_m = luz_m

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.tipo_abobada:
            graph.add((self.uri, ALAKORO.hasTipoAbobada, Literal(self.tipo_abobada)))
        if self.luz_m is not None:
            graph.add((self.uri, ALAKORO.hasLuzM, Literal(self.luz_m, datatype=XSD.float)))


class Fissura(AlakoroEntity):
    """Fissura em elemento estrutural / Crack in a structural element."""

    _type = ALAKORO.Fissura

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 description: Optional[str] = None, posicao_m: Optional[float] = None,
                 largura_mm: Optional[float] = None, tipo: Optional[str] = None,
                 atividade: Optional[str] = None):
        super().__init__(identifier=identifier, name=name, description=description)
        self.posicao_m = posicao_m
        self.largura_mm = largura_mm
        self.tipo = tipo  # "transversal" | "longitudinal"
        self.atividade = atividade  # "ativa" | "estavel" | "dormente"
        self.elemento: Optional[ElementoEstrutural] = None

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.posicao_m is not None:
            graph.add((self.uri, ALAKORO.hasPosicaoM, Literal(self.posicao_m, datatype=XSD.float)))
        if self.largura_mm is not None:
            graph.add((self.uri, ALAKORO.hasLarguraMm, Literal(self.largura_mm, datatype=XSD.float)))
        if self.tipo:
            graph.add((self.uri, ALAKORO.hasTipoFissura, Literal(self.tipo)))
        if self.atividade:
            graph.add((self.uri, ALAKORO.hasAtividade, Literal(self.atividade)))
        if self.elemento is not None:
            graph.add((self.uri, ALAKORO.isFissuraOf, self.elemento.uri))


class InstalacaoFibra(AlakoroEntity):
    """Instalação de fibra óptica na estrutura / Fiber optic installation on the structure."""

    _type = ALAKORO.InstalacaoFibra

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 description: Optional[str] = None, comprimento_m: Optional[float] = None,
                 tecnica: Optional[str] = None, data_instalacao: Optional[datetime] = None):
        super().__init__(identifier=identifier, name=name, description=description)
        self.comprimento_m = comprimento_m
        self.tecnica = tecnica  # "colada" | "embutida_junta" | "ranhura"
        self.data_instalacao = data_instalacao
        self.estrutura: Optional[Estrutura] = None
        self.interrogador: Optional[Interrogator] = None

    def _attach(self, graph: Graph):
        super()._attach(graph)
        if self.comprimento_m is not None:
            graph.add((self.uri, ALAKORO.hasComprimentoM, Literal(self.comprimento_m, datatype=XSD.float)))
        if self.tecnica:
            graph.add((self.uri, ALAKORO.hasTecnica, Literal(self.tecnica)))
        if self.data_instalacao:
            graph.add((self.uri, ALAKORO.hasDataInstalacao,
                       Literal(self.data_instalacao.isoformat(), datatype=XSD.dateTime)))
        if self.estrutura is not None:
            graph.add((self.uri, ALAKORO.isInstalacaoOf, self.estrutura.uri))
        if self.interrogador is not None:
            graph.add((self.uri, ALAKORO.measuredWithInterrogator, self.interrogador.uri))
