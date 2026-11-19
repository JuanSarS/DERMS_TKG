"""Importa el RDF/XML CIM100 auténtico aportado por el usuario."""

from functools import lru_cache

from rdflib import RDF, Graph, Namespace

from backend.app.settings import ROOT

CIM = Namespace("http://iec.ch/TC57/CIM100#")


@lru_cache(maxsize=1)
def load_cim() -> Graph:
    path = ROOT / "data/reference/DSS_model/IEEE13Nodeckt_CIM100x.XML"
    graph = Graph()
    graph.parse(path, format="xml", publicID="https://example.org/ieee13/cim/")
    return graph


def cim_catalog() -> dict:
    graph = load_cim()
    return {
        "triples": len(graph),
        "ac_line_segments": len(list(graph.subjects(RDF.type, CIM.ACLineSegment))),
        "terminals": len(list(graph.subjects(RDF.type, CIM.Terminal))),
        "connectivity_nodes": len(list(graph.subjects(RDF.type, CIM.ConnectivityNode))),
        "source_file": "KG_example_08142026(1).zip:DSS_model/IEEE13Nodeckt_CIM100x.XML",
        "cim_version": "IEC61970CIM100",
    }
