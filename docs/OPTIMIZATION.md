# Optimización offline reproducible

Minimizar `J = w_energy*C_energia/scale_energy + w_peak*P_pico/scale_peak + w_battery*E_throughput/scale_battery + w_curtail*E_FV_recortada/scale_curtail`.

- `battery_kw > 0` representa **carga**, `< 0` descarga.
- Dinámica: `SOC[t+1] = SOC[t] + dt*eta_charge*Pcharge[t] - dt*Pdischarge[t]/eta_discharge`.
- Restricciones: SOC mínimo/máximo, límites de cargador/descargador, carga/descarga excluyentes, importación/exportación excluyentes, disponibilidad PV, límite grid, cargo flexible exactamente `slots_required` dentro de `earliest_slot .. latest_slot`, SOC final mínimo.
- Se usa `scipy.optimize.milp` con variables binarias para exclusión y programación flexible. Horizonte completo del día (offline), sin afirmaciones de pronóstico perfecto online.
- Tarifas AUD y batería de prueba son **SIMULATED**, aunque consumo/FV proceden del extracto Ausgrid. La función objetivo `config/objective.json` es editable sin reescribir servicios. El resultado usa `NOT_VALIDATED` para el despacho de batería porque la API QSTS vigente no acepta consignas BESS por paso.
- Política fija baseline y despacho MILP usan la misma demanda/FV/tarifa. Una reducción de costo indica beneficio del optimizador y de los supuestos, no del grafo.
- SAIDI y SAIFI: fuera de alcance del MVP, sin datos de interrupciones/usuarios afectados.
