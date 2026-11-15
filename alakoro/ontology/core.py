"""
Alakoro FiberSense — Core da Ontologia
Ontology Core

Define namespace, modelo RDF base e entidade base.
"""

from rdflib import Graph, Namespace, Literal, URIRef, RDF, RDFS, XSD
from rdflib.namespace import OWL
from typing import Optional
import uuid


ALAKORO = Namespace("https://alakoro.fibersense/ontology#")


class OntologyModel:
    """Container RDF/OWL para a ontologia Alakoro."""

    def __init__(self):
        self.graph = Graph()
        self.graph.bind("alakoro", ALAKORO)
        self.graph.bind("owl", OWL)
        self.graph.bind("rdfs", RDFS)
        self._define_schema()

    def _define_schema(self):
        """Define classes e propriedades base da ontologia."""
        self.graph.add((ALAKORO.Entity, RDF.type, OWL.Class))
        self.graph.add((ALAKORO.Entity, RDFS.label, Literal("Entidade Alakoro", lang="pt")))
        self.graph.add((ALAKORO.Entity, RDFS.label, Literal("Alakoro Entity", lang="en")))

        self.graph.add((ALAKORO.hasName, RDF.type, OWL.DatatypeProperty))
        self.graph.add((ALAKORO.hasName, RDFS.domain, ALAKORO.Entity))
        self.graph.add((ALAKORO.hasName, RDFS.range, XSD.string))

        self.graph.add((ALAKORO.hasIdentifier, RDF.type, OWL.DatatypeProperty))
        self.graph.add((ALAKORO.hasIdentifier, RDFS.domain, ALAKORO.Entity))
        self.graph.add((ALAKORO.hasIdentifier, RDFS.range, XSD.string))

        self.graph.add((ALAKORO.hasDescription, RDF.type, OWL.DatatypeProperty))
        self.graph.add((ALAKORO.hasDescription, RDFS.domain, ALAKORO.Entity))
        self.graph.add((ALAKORO.hasDescription, RDFS.range, XSD.string))

        self.graph.add((ALAKORO.createdAt, RDF.type, OWL.DatatypeProperty))
        self.graph.add((ALAKORO.createdAt, RDFS.domain, ALAKORO.Entity))
        self.graph.add((ALAKORO.createdAt, RDFS.range, XSD.dateTime))

        # ─── Domínio MSE: estruturas e elementos / SHM domain: structures ───
        classes_mse = [
            (ALAKORO.Estrutura, "Estrutura", "Structure"),
            (ALAKORO.EdificioEclesiastico, "Edifício Eclesiástico", "Ecclesiastical Building"),
            (ALAKORO.ElementoEstrutural, "Elemento Estrutural", "Structural Element"),
            (ALAKORO.Alvenaria, "Alvenaria", "Masonry"),
            (ALAKORO.Fundacao, "Fundação", "Foundation"),
            (ALAKORO.TorreSineira, "Torre Sineira", "Bell Tower"),
            (ALAKORO.Cobertura, "Cobertura", "Roof"),
            (ALAKORO.Abobada, "Abóbada", "Vault"),
            (ALAKORO.Fissura, "Fissura", "Crack"),
            (ALAKORO.InstalacaoFibra, "Instalação de Fibra", "Fiber Installation"),
        ]
        for classe, pt, en in classes_mse:
            self.graph.add((classe, RDF.type, OWL.Class))
            self.graph.add((classe, RDFS.label, Literal(pt, lang="pt")))
            self.graph.add((classe, RDFS.label, Literal(en, lang="en")))
        self.graph.add((ALAKORO.EdificioEclesiastico, RDFS.subClassOf, ALAKORO.Estrutura))
        for subclasse in (ALAKORO.Alvenaria, ALAKORO.Fundacao, ALAKORO.TorreSineira,
                          ALAKORO.Cobertura, ALAKORO.Abobada):
            self.graph.add((subclasse, RDFS.subClassOf, ALAKORO.ElementoEstrutural))

        propriedades_mse = [
            (ALAKORO.hasLocalizacao, XSD.string),
            (ALAKORO.hasAnoConstrucao, XSD.integer),
            (ALAKORO.hasEstadoConservacao, XSD.string),
            (ALAKORO.hasEstiloArquitetonico, XSD.string),
            (ALAKORO.hasDiocese, XSD.string),
            (ALAKORO.hasParoquia, XSD.string),
            (ALAKORO.hasMaterial, XSD.string),
            (ALAKORO.hasTipoAlvenaria, XSD.string),
            (ALAKORO.hasTipoFundacao, XSD.string),
            (ALAKORO.hasAlturaM, XSD.float),
            (ALAKORO.hasNumeroSinos, XSD.integer),
            (ALAKORO.hasTipoCobertura, XSD.string),
            (ALAKORO.hasInclinacaoGraus, XSD.float),
            (ALAKORO.hasTipoAbobada, XSD.string),
            (ALAKORO.hasLuzM, XSD.float),
            (ALAKORO.hasPosicaoM, XSD.float),
            (ALAKORO.hasLarguraMm, XSD.float),
            (ALAKORO.hasTipoFissura, XSD.string),
            (ALAKORO.hasAtividade, XSD.string),
            (ALAKORO.hasComprimentoM, XSD.float),
            (ALAKORO.hasTecnica, XSD.string),
            (ALAKORO.hasDataInstalacao, XSD.dateTime),
        ]
        for propriedade, alcance in propriedades_mse:
            self.graph.add((propriedade, RDF.type, OWL.DatatypeProperty))
            self.graph.add((propriedade, RDFS.domain, ALAKORO.Entity))
            self.graph.add((propriedade, RDFS.range, alcance))

        propriedades_objeto_mse = [
            (ALAKORO.hasElemento, ALAKORO.Estrutura, ALAKORO.ElementoEstrutural),
            (ALAKORO.hasFissura, ALAKORO.ElementoEstrutural, ALAKORO.Fissura),
            (ALAKORO.hasInstalacaoFibra, ALAKORO.Estrutura, ALAKORO.InstalacaoFibra),
        ]
        for propriedade, dominio, alcance in propriedades_objeto_mse:
            self.graph.add((propriedade, RDF.type, OWL.ObjectProperty))
            self.graph.add((propriedade, RDFS.domain, dominio))
            self.graph.add((propriedade, RDFS.range, alcance))

        # ─── Domínio poço: eventos canônicos (CL-12, IE:A-02) ───
        # Well domain: canonical events (CL-12, IE:A-02). Registra como
        # classes OWL as especializações de Event (as 4 pré-existentes e as
        # 12 novas da Onda 2), tornando o grafo consultável por tipo de
        # evento. / Registers the Event specializations (the 4 pre-existing
        # and the 12 new Wave-2 ones) as OWL classes.
        classes_eventos = [
            (ALAKORO.JouleThomsonEvent, "Evento Joule-Thomson", "Joule-Thomson Event"),
            (ALAKORO.LeakEvent, "Evento de Vazamento", "Leak Event"),
            (ALAKORO.FlowEvent, "Evento de Fluxo", "Flow Event"),
            (ALAKORO.WarmBackEvent, "Evento Warm-Back", "Warm-Back Event"),
            (ALAKORO.SlopeVelocityEvent, "Evento de Velocidade por Inclinação", "Slope Velocity Event"),
            (ALAKORO.GasLiftValveEvent, "Evento de Válvula de Gás Lift", "Gas Lift Valve Event"),
            (ALAKORO.GLVBellowRuptureEvent, "Evento de Fole Furado de GLV", "GLV Bellow Rupture Event"),
            (ALAKORO.ValveChatterEvent, "Evento de Chatter de Válvula", "Valve Chatter Event"),
            (ALAKORO.FracScreenoutEvent, "Evento de Screen-out de Fratura", "Fracture Screen-out Event"),
            (ALAKORO.FracProppantDistributionEvent, "Evento de Distribuição de Propante", "Proppant Distribution Event"),
            (ALAKORO.FracHeightGrowthEvent, "Evento de Crescimento de Altura de Fratura", "Fracture Height Growth Event"),
            (ALAKORO.PerforationEffectivenessEvent, "Evento de Efetividade de Canhoneio", "Perforation Effectiveness Event"),
            (ALAKORO.CementBondEvaluationEvent, "Evento de Avaliação de Cimentação", "Cement Bond Evaluation Event"),
            (ALAKORO.ReCementingAssessmentEvent, "Evento de Avaliação de Recimentação", "Re-Cementing Assessment Event"),
            (ALAKORO.CrossflowZonalEvent, "Evento de Fluxo Cruzado Zonal", "Zonal Crossflow Event"),
            (ALAKORO.CementChannelingEvent, "Evento de Canalização de Cimento", "Cement Channeling Event"),
            (ALAKORO.WellboreReferenceMeasurements, "Medições de Referência do Poço", "Wellbore Reference Measurements"),
        ]
        for classe, pt, en in classes_eventos:
            self.graph.add((classe, RDF.type, OWL.Class))
            self.graph.add((classe, RDFS.label, Literal(pt, lang="pt")))
            self.graph.add((classe, RDFS.label, Literal(en, lang="en")))

        propriedades_poco = [
            (ALAKORO.hasEventType, XSD.string),
            (ALAKORO.hasTimestamp, XSD.dateTime),
            (ALAKORO.hasDepthMD, XSD.float),
            (ALAKORO.hasConfidence, XSD.float),
            (ALAKORO.hasSeverity, XSD.string),
            (ALAKORO.hasRecommendation, XSD.string),
            (ALAKORO.hasCorrelationId, XSD.string),
            (ALAKORO.hasInterfaceDepth, XSD.float),
            (ALAKORO.hasLeakDepth, XSD.float),
            (ALAKORO.hasFlowRateMs, XSD.float),
            (ALAKORO.hasInjectionDepth, XSD.float),
            # Campos cinemáticos CL-04 / CL-04 kinematic fields:
            (ALAKORO.hasApparentVelocityMs, XSD.float),
            (ALAKORO.hasFlowDirection, XSD.string),
            (ALAKORO.hasDiscrimination, XSD.string),
            # Especializações de GLV/chatter/frac/cimento (CL-12) / GLV,
            # chatter, frac and cement specializations (CL-12):
            (ALAKORO.hasValveDepthsM, XSD.float),
            (ALAKORO.hasRuptureValveIdx, XSD.integer),
            (ALAKORO.hasChatterBandHz, XSD.float),
            (ALAKORO.hasFracHeightM, XSD.float),
            (ALAKORO.hasAffectedDepthRangeM, XSD.float),
            (ALAKORO.hasChannelCount, XSD.integer),
            # Metadados Brillouin (SP:B-05) / Brillouin metadata (SP:B-05):
            (ALAKORO.hasBrillouinC11MhzPerUstrain, XSD.float),
            (ALAKORO.hasBrillouinC12MhzPerC, XSD.float),
            (ALAKORO.hasThermalReferenceModality, XSD.string),
            (ALAKORO.hasDualFiberConfig, XSD.boolean),
            # Gauges de referência do poço (IE:D-05) / Well reference gauges:
            (ALAKORO.hasGaugeDepthMD, XSD.float),
            (ALAKORO.hasGaugeTemperatureC, XSD.float),
            (ALAKORO.hasGaugePressureBar, XSD.float),
        ]
        for propriedade, alcance in propriedades_poco:
            self.graph.add((propriedade, RDF.type, OWL.DatatypeProperty))
            self.graph.add((propriedade, RDFS.domain, ALAKORO.Entity))
            self.graph.add((propriedade, RDFS.range, alcance))

    def add(self, entity: "AlakoroEntity"):
        """Adiciona uma entidade ao grafo."""
        entity._attach(self.graph)

    def to_turtle(self) -> str:
        """Serializa a ontologia em Turtle."""
        return self.graph.serialize(format="turtle")

    def to_jsonld(self) -> str:
        """Serializa a ontologia em JSON-LD."""
        return self.graph.serialize(format="json-ld")

    def to_owl(self) -> str:
        """Serializa a ontologia em OWL/XML."""
        return self.graph.serialize(format="xml")

    def query(self, sparql: str):
        """Executa uma consulta SPARQL no grafo."""
        return self.graph.query(sparql)


class AlakoroEntity:
    """Entidade base da ontologia Alakoro."""

    _type = ALAKORO.Entity

    def __init__(self, identifier: Optional[str] = None, name: Optional[str] = None,
                 description: Optional[str] = None):
        self.identifier = identifier or str(uuid.uuid4())
        self.name = name or self.__class__.__name__
        self.description = description
        self.uri = ALAKORO[self.identifier]

    def _attach(self, graph: Graph):
        graph.add((self.uri, RDF.type, self._type))
        graph.add((self.uri, ALAKORO.hasIdentifier, Literal(self.identifier)))
        graph.add((self.uri, ALAKORO.hasName, Literal(self.name)))
        if self.description:
            graph.add((self.uri, ALAKORO.hasDescription, Literal(self.description)))
