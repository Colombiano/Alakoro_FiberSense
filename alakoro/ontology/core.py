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
