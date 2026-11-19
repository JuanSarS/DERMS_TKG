"""Exporta RDF Turtle; usa `oxrdflib` solo si está instalado de forma explícita."""

from pathlib import Path

from rdflib import Graph


def load_turtle(path: Path) -> Graph:
    graph = Graph()
    if path.exists():
        graph.parse(path, format="turtle")
    return graph


def save_turtle(graph: Graph, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".ttl.tmp")
    graph.serialize(destination=temp, format="turtle")
    temp.replace(path)
    return path


def open_oxigraph(path: Path):
    """Se instala opcionalmente con `pip install -e '.[oxigraph]'`."""
    import oxrdflib  # noqa: F401
    from rdflib import Dataset

    dataset = Dataset(store="Oxigraph")
    dataset.open(str(path), create=True)
    return dataset
