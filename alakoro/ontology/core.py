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
