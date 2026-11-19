# RDF/CIM y grafo temporal

Fuente CIM100: `data/reference/DSS_model/IEEE13Nodeckt_CIM100x.XML`, aportada en `KG_example_08142026(1).zip`. Se importan tripletas `cim:ACLineSegment`, `cim:Terminal`, `cim:ConnectivityNode` y sus identificadores existentes.

Cada instante de 30 minutos de un despacho genera un recurso `tkg:StateAssertion` relacionado con `Battery`, `SimulationRun`, `validFrom`, `validTo`, `recordedAt`, `sourceId`, `usesEvidence`, `batteryKw`, `socKwh` y valores de perfil. Las relaciones de batería a bus son hipótesis **modeladas**, no topología real medida.

`GET /api/graph/asof?run_id=...&at=2011-06-30T14:00:00Z` recupera vigencias. `known_at=...` permite consultas bitemporales (conocimiento disponible en fecha). `POST /api/graph/query` solo admite SPARQL SELECT local. Todos los grafos generados se exportan a Turtle.

Ejemplo:
```sparql
PREFIX tkg: <https://example.org/derms/tkg#>
SELECT ?s ?batteryKw WHERE { ?s a tkg:StateAssertion ; tkg:batteryKw ?batteryKw . } LIMIT 10
```

RDFLib está instalado por defecto. Se puede optar por `oxrdflib` (`pip install -e '.[oxigraph]'`), pero no se requiere un servidor de grafos.
