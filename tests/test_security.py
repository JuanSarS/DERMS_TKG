import pytest

from backend.app.services.sparql_queries import safe_select


def test_path_traversal_not_accepted():
    with pytest.raises(ValueError):
        safe_select("../../secrets", "SELECT * WHERE {?s ?p ?o}")


def test_mutating_sparql_rejected():
    with pytest.raises(ValueError):
        safe_select("id", "INSERT DATA { <urn:a> <urn:b> <urn:c> }")
