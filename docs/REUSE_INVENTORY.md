# Inventario de reutilización
- `Proyecto_1811(1).zip`: se inspeccionó `packages/contracts/models.py`, `services/api_manager/api/routes/simulations.py`, `services/api_manager/auth/routes.py`, `scripts/qsts_ws_smoke.py`, servicio QSTS y `data/networks/ieee13`. No se modifica el proyecto original. Se consume por red.
- `KG_example_08142026(1).zip`: contiene RDF/XML CIM100 auténtico, IEEE13 DSS y linecodes, importados **como copia de referencia** en `data/reference/DSS_model/`.
- `main_scr(1).py` y `rdf_utils(1).py`: consulta SPARQL de `ACLineSegment`, terminales y capacidad nominal; se reutiliza el enfoque RDFLib, se reemplaza resolución de rutas manual por pathlib.
- `TKG_Dos_Prototipos_20261118.zip`: 48 pasos Ausgrid procesados y procedencia SHA256. El optimizador actual se reemplaza por MILP con ecuaciones explícitas.
- `esquema_tkg.sql`: principios de experimentos/validez/fuente preservados; base local nueva para datos, RDF en `.ttl`.
