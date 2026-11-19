# Procedencia y estados de evidencia

- `REAL`: datos medidos de Ausgrid, procedencia de fuente externa indicada; no son mediciones de IEEE13.
- `DERIVED`: conversión energética de unidades y despacho MILP, basado en datos y modelos.
- `SIMULATED`: batería, carga flexible, tarifas y topología de asignación del escenario.
- `REFERENCE`: circuito IEEE13/CIM100 de referencia eléctrica.
- `NOT_VALIDATED`: una acción BESS aún no fue aplicada y verificada en OpenDSS.
- `remote_qsts_baseline_verified`: verificación de multiplicadores globales QSTS, no verificación de BESS.

Al exportar una corrida, `manifest.json` indica los hashes SHA256 de los archivos. `data/processed/*.manifest.json` conserva el SHA256 de fuente y su contrato; las rutas absolutas históricas del manifiesto original no son válidas en la nueva instalación.
