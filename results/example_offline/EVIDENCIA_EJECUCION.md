# Evidencia de laboratorio offline · DERMS TKG Power Lab

**Ejecución realmente realizada en el entorno de construcción (19 de noviembre de 2026).**

- `run_id`: `fd7b2a83-5e49-4a6f-8264-8d992f06024c`.
- Entrada: extracto secundario de Ausgrid C12, 48 pasos de 30 minutos; datos medidos pero transformados (`REAL → DERIVED`).
- Escenario batería/FV tarifario: `SIMULATED` y `MODELED`, IEEE13 es red de `REFERENCE`.
- Solución energética: MILP con SciPy, no es control físico.
- Coste modelado optimizado: **4.7782 AUD**.
- Pico de importación modelado: **1.5169 kW**.
- Throughput BESS: **12.4119 kWh**.
- Curtailment FV: **0.0000 kWh**.
- Coste modelo fijo: **6.6005 AUD**.
- Salida RDF: `derms_graph.ttl` con **4.289 tripletas** (CIM100 + aserciones temporales).
- Estado OpenDSS Cloud: **NOT_RUN** en esta evidencia.
- Validación eléctrica de BESS: **NOT_VALIDATED**, porque QSTS remoto actual no aplica consignas Storage.
- LLM/Ollama: **NOT_RUN** (explicación determinista operativa).

El diferencial de costo corresponde al optimizador y los supuestos, no a una mejora causal del grafo. No se calculan SAIDI/SAIFI.
