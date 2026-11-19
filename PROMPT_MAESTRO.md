# PROMPT MAESTRO DE IMPLEMENTACIÓN | DERMS TKG POWER LAB
**Versión:** 1.0 · 19/11/2026  
**Alcance:** solo DERMS. **Este documento es una especificación para generar el proyecto, no afirma que la aplicación esté ya implementada.**

## A. Rol, resultado y reglas
Actúa como arquitecto de software científico y desarrollador senior Python/JavaScript con experiencia en FastAPI, OpenDSS/AltDSS, RDF/CIM, series temporales y optimización energética. **Entrega todos los archivos completos y ejecutables**, sin pseudocódigo ni referencias a archivos que no hayas creado, con sus pruebas, instalación y documentación Windows/PowerShell. Construye una app **separada del proyecto OpenDSS original**: `derms-tkg-power-lab/`. No modifiques `Proyecto_1811(1).zip` ni el servicio existente.

Meta: observar y controlar *experimentalmente* una simulación IEEE13 QSTS consumida por la API OpenDSS Cloud publicada, contextualizar estados y eventos con TKG RDF/CIM, calcular un despacho reproducible de BESS + FV + carga flexible, validar la factibilidad eléctrica **solo donde el contrato realmente lo permita**, y explicar resultados con Ollama opcional. La arquitectura debe permitir cambiar la función objetivo sin reescribir simulación, API, TKG ni interfaz. Nada de hardware, EMS industrial, SAIDI/SAIFI calculados ni control físico para el MVP. Etiquetar estrictamente REAL, SIMULATED, DERIVED, REFERENCE, NOT_RUN y NOT_VALIDATED.

Fuentes ya entregadas: `Proyecto_1811(1).zip`, `main_scr(1).py`, `rdf_utils(1).py`, `TKG_Dos_Prototipos_20261118.zip`, `esquema_tkg.sql`, manifiestos Ausgrid y plan Tesis II. Reutiliza lo que pase auditoría de contratos y pruebas; mantén decisiones previas. Ausgrid = perfiles históricos medidos de consumo/FV, **no** estados medidos de batería; IEEE13 = red de referencia sin asociación física directa con Ausgrid; BESS, precio, demanda flexible y su asignación a la red = escenarios modelados.

## B. Contrato REAL del servicio OpenDSS (verificado leyendo el código adjunto; comprobar en vivo antes de usar)
- URL base configurable inicial: `https://dou50du5mg1f3.cloudfront.net`. No asumir que sigue desplegada o saludable. `GET /health` devuelve `{"status":"ok"}` cuando el servicio del código responde; validar HTTP 200 y contenido, con timeout.
- Autenticación: `POST /auth/token`, cuerpo `application/x-www-form-urlencoded` con `username`, `password`. Devuelve `access_token`, `token_type`, `expires_in` y establece cookie HTTP-only. Comprobar con `GET /auth/me`. REST admite `Authorization: Bearer <token>`; WebSocket acepta cookie `opendss_access_token` del servidor o subprotocolos `['opendss.jwt', '<token>']` (tal como `scripts/qsts_ws_smoke.py`), usando WSS si HTTPS. **No enviar credenciales al navegador**; proxy backend a backend y frontend a backend local.
- `GET /models` autenticado; `POST /simulations` con `{"topology":"ieee13","load_multiplier":1.0}` devuelve `session_id`; `GET /simulations`, `GET /simulations/{id}`, `GET /simulations/{id}/results` y `DELETE /simulations/{id}` tienen control de acceso. Solo cerrar sesiones **creadas por esta app** y con confirmación.
- Iniciar QSTS: `POST /simulations/{id}/solve` con `{"simulation_type":"qsts","qsts":{"duration_hours":24,"step_minutes":30,"profile_source":"values","load_multipliers":[48 números positivos]}}`. La API requiere exactamente un multiplicador global de carga por paso; no acepta `pv_kw`, `soc`, setpoints de Storage ni control BESS individual en dicho endpoint. Si hay 48 intervalos, el vector debe tener 48 números positivos. No inventar otros campos.
- `WS /ws/simulations/{id}` envía al conectarse `snapshot`; durante ejecución emite `simulation_started`, `model_loaded`, `solving`, `qsts_progress`, `result`, `completed` o `error`. `qsts_progress` incluye `step`, `total_steps`, `progress_pct`, `simulated_minutes`, `simulated_hour`, `converged`, `load_multiplier`, `total_kw`, `total_kvar`, `min_voltage_pu`, `max_voltage_pu`, `solve_ms`. El WS **NO es canal de comandos**: creación y ejecución van por REST. Suscribirse ANTES de lanzar `/solve`; cuando termine, leer `/results` para obtener todos los `steps` y `summary`. `result` del WS para QSTS solo entrega resumen. No asumir que `completed` siempre significa resultado correcto: validar `status`, convergencia y pasos.
- Reutilizar los contratos `packages/contracts/models.py` y `packages/contracts/progress.py`, el servicio `services/api_manager/api/routes/simulations.py` y la prueba `scripts/qsts_ws_smoke.py` **como referencia**, sin copiar el backend entero. La API puede usar sesiones efímeras que se pierden tras un redeploy.
- `POST /models/upload` acepta `.dss`/`.zip` y exige admin; `POST /models/custom/{model_id}/validate?master=...` comprueba el master; los modelos personalizados se referencian con topología `custom:{model_id}:{master}`. Verificar acceso real, disponibilidad y ejecución en el worker antes de usarlos.

## C. Seguridad, secretos y desconexiones
Crear `secrets/` para uso **EXCLUSIVAMENTE DEL BACKEND**. Añadir `secrets/opendss.example.json` con claves `base_url`, `username`, `password`, `timeout_seconds`; el archivo real `secrets/opendss.local.json` se genera manualmente, queda en `.gitignore` y no se incluye en ZIP, logs ni pruebas. Para el laboratorio local el usuario ha indicado credenciales provisionales `admin`/`admin`: admitirlas **solo en ese archivo local y solo para pruebas**, nunca como valores de producción, ni incrustarlas en frontend. Permitir variables de entorno para despliegues; al iniciar avisar del riesgo y recomendar rotarlas. `secrets/ollama.example.json`: `base_url`, `model`, `enabled`; sin exponer el servicio local públicamente.

Implementar un monitor de estado que distinga `HEALTHY`, `OFFLINE`, `AUTH_ERROR`, `DEGRADED_WS`, `STALE`, `RECOVERING`. Si `/health` no responde, responde !=200 o no devuelve `{"status":"ok"}`: **no crear sesiones, no enviar solve, no ingerir nuevos pasos, no ejecutar optimización basada en datos supuestamente nuevos y NO sobrescribir último resultado válido**. Mostrar banner de caída, fecha del último dato confirmado y modo solo lectura, conservando históricos en disco y visualización. El estado de conexión sí cambia. Si se corta WSS, no borrar resultados ni marcar una ejecución incompleta como validada; reconectar con backoff + jitter, renovar autenticación si procede, consultar GET detalle y `/results` para reconciliar la sesión y deduplicar por `(session_id, run_id, step)`; si 404, marcar sesión remota perdida sin borrar corridas locales. Reanudar solo con consentimiento explícito para una nueva simulación. Evitar datos fuera de orden, sesiones duplicadas, fugas de JWT y reintentos destructivos. Uso por defecto de TLS verificado, sin `verify=False`.

**Persistencia de doble estado:** `last_good_run` inmutable y `active_run` provisional. Actualizar vista en vivo con WS **solo mientras conexión válida**, pero publicar como nuevo `last_good_run` únicamente tras `completed`, respuesta REST `/results`, schema validado y política de convergencia declarada. Fallos HTTP 401/403/404/422/429, timeout, WSS 1008/1013, expiración de JWT y pérdida de conexión tienen mensajes y estados distintos.

## D. Flujo eléctrico y optimización
1. Autenticar y verificar salud, seleccionar modelo IEEE13, cargar/normalizar Ausgrid con unidad original y SHA256, elegir día y 48 pasos de 30 minutos, configurar escala y justificación de asignación hipotética.
2. Crear sesión REST y suscribirse al WSS; ejecutar QSTS remoto BASELINE con los multiplicadores positivos compatibles; guardar progreso y resultados por paso, con `run_id`, zona horaria y proveniencia. Mostrar las curvas de potencia, tensión mínima/máxima, convergencia y avance.
3. Ejecutar un planificador independiente para BESS y carga flexible con signo de batería **positivo = carga, negativo = descarga**, potencia FV disponible/recortada, importación/exportación y SOC. Las 48 decisiones deben conservar timestamps consistentes y la distinción medida/simulada/derivada. Optimización offline para MVP: **NO** llamarla real-time, no usar métricas de confiabilidad no medidas.
4. Función objetivo configurable y modular (cambiar `config/objective.json`, guardar versión/hash y volver a correr):
   `min J = w_energy * C_energia + w_peak * P_pico + w_battery * C_bateria + w_curtail * E_FV_recortada`.
   Cada término tendrá definición, unidad, normalización o escala, peso, habilitado, límites, sentido min/max y contribución reportada; no sumar unidades heterogéneas sin normalizar. Motor de términos registrables y evaluador separado del algoritmo de optimización. Comparar política fija vs optimizada, no atribuir ahorro al TKG.
5. Restricciones: `SOC_min <= SOC_t <= SOC_max`, `-Pdesc_max <= Pbess_t <= Pch_max`, balance energético, eficiencias `eta_ch/eta_dis`, `SOC_{t+1}=SOC_t + eta_ch*max(P,0)*dt - max(-P,0)*dt/eta_dis`, límite PV, potencia nominal de carga flexible, energía/ventana de tarea, restricciones de no simultaneidad, terminal SOC opcional; especificar import/export y límites de red. Rechazar plan inválido, incluso si lo propone un LLM.
6. **Verificación eléctrica diferenciada:** (A) `remote_qsts_baseline_verified`: QSTS global de carga, realmente ejecutado mediante API; (B) `dispatch_energy_model_only`: batería con algoritmo local SIN validación OpenDSS; (C) `dispatch_electrical_verified`: solo si un modelo OpenDSS aislado incorpora la FV/BESS y las consignas por intervalo y se ejecuta **efectivamente** a través de contratos soportados. El QSTS remoto actual **no** aplica consignas BESS; no etiquetar como C los resultados A/B. Para C, explorar paquete DSS custom con `Storage`, `PVSystem` y `LoadShape` o extensión compatible **sin tocar el servicio original**; registrar diferencias entre resultados y límites. Si no es posible, mostrar `NOT_VALIDATED` y explicación en UI.
7. El ciclo de modificación del escenario debe funcionar **bidireccionalmente por REST**: cambiar objetivo, PV, carga flexible o BESS -> nuevo escenario/run local -> generar modelo/perfil compatible -> solicitar sesión/solve por REST cuando sea viable -> recibir WSS -> validar `/results` -> actualizar TKG y UI. Nunca fingir que el WS acepta consignas.

## E. TKG semántico RDF/CIM
- RDFLib como API; Oxigraph persistente si se instala correctamente; exportar siempre Turtle `.ttl` y JSON de evidencia. Mantener SQLite para series, snapshot válido y experimentos, **no como sustituto oculto** del RDF.
- Nodos CIM cuando exista evidencia fuente: `ACLineSegment`, `Terminal`, `ConnectivityNode`, `EnergyConsumer`, otros tipos identificados realmente. No inventar una exportación CIM: `main_scr(1).py` espera `DSS_model/IEEE13Nodeckt_CIM100x.XML` y **ese XML no aparece en `Proyecto_1811(1).zip`**. Crear importador CIM/XML si se suministra; de no haberlo, generar un grafo de catálogo IEEE13 **derivado de DSS** con mapeo y cobertura CIM documentados, nunca afirmar equivalencia CIM completa. Conservar `http://iec.ch/TC57/CIM100#` solo si corresponde a la versión real. Evitar concatenaciones arbitrarias de URI y pérdidas de identidad.
- Ontología mínima propia `tkg:SimulationRun`, `tkg:TimeInterval`, `tkg:StateAssertion`, `tkg:Decision`, `tkg:Constraint`, `tkg:Source`, `tkg:Evidence`, `tkg:Validation`, conectadas a activos de referencia; predicados `hasState`, `connectedTo`, `observedAt`, `validFrom`, `validTo`, `recordedAt`, `sourceId`, `rawUri`, `producedBy`, `usesEvidence`, `hasDecision`, `validatedBy`. Tripletas de estados versionadas mediante nodos de aserción (o grafos nombrados documentados). Hacer consultas SPARQL **as-of** y de **knowledge-at** (bitemporal), filtrando run y fuente.
- Al seleccionar `t`, interfaz evidencia: estado BESS y SOC simulado, perfil consumo/FV medido, evento/decisión, restricciones, respuesta OpenDSS y su validación. Todo valor de progreso remoto debe vincular `session_id`, `step`, `run_id`, hash de escenario, source_kind, marca temporal del backend, tiempo simulado y `recordedAt`; diferenciar horas de simulación `simulated_minutes` de fecha UTC real de Ausgrid para evitar asociaciones engañosas.
- B0 tablas temporales, B1 KG estático y B2 RDF TKG, datos y algoritmos equivalentes. Para cada variante reportar exactitud de as-of, decisiones con contexto obsoleto, cobertura de procedencia, latencia, tamaño, costos de escritura. No atribuir mejores costos energéticos al grafo sin experimento controlado.

## F. LLM con Ollama, sin dependencia obligatoria
- Integración local por backend `http://127.0.0.1:11434/api/chat` con modelo configurable y `format` JSON Schema si se requiere estructura. Ollama es **servidor de inferencia**, no un método de fine-tuning. Primera fase: RAG sobre evidencia estructurada recuperada de SQL/SPARQL, sin entrenamiento. Segunda fase opcional (Tesis II): evaluación con y sin adaptación y, solo si hay corpus de ejemplos etiquetados, explorar LoRA/fine-tuning con proceso separado y métricas; no condición para MVP.
- Preguntas: «¿Por qué cargó a las 13:00?», «¿Qué restricciones conocía a las 17:00?», «¿Qué cambió frente a baseline?». Responder con `run_id`, `timestamp`, valores, evidencias y limitaciones; campo de confianza/estado de validación sin inventar certidumbre. No permitir que texto del dataset actúe como instrucción. Si Ollama está apagado, la app sigue funcionando y muestra `LLM no disponible`, preservando explicaciones deterministas.
- Cualquier propuesta de acción LLM pasa por esquema Pydantic, restricciones SOC, validador y, si existe, simulación eléctrica. El LLM no ejecuta comandos OpenDSS, no envía señales físicas ni sobrescribe resultados verificados.

## G. Interfaz web
Frontend HTML/CSS/JS ES modules con Vite para construir, Chart.js para series y Cytoscape.js para grafo; Biome para lint/formato. Backend FastAPI sirve API local + proxy WSS y, en producción, el build estático. Sin tokens en `localStorage`, `sessionStorage`, query strings ni JS embebido; autenticación OpenDSS solo en servidor. Páginas: **(1) DERMS y simulación**, **(2) Explorador TKG**, **(3) Experimentos y comparaciones**. Barra superior permanente con salud OpenDSS, WS, autenticación, Ollama, último dato válido y procedencia; selector de sesión, modelo y run. DERMS muestra: configurador de 48 pasos, pesos/objetivo editables, botonera `Comprobar / Crear sesión / Ejecutar / Recalcular / Comparar / Exportar`, progreso en vivo, curva carga/FV/BESS/SOC, potencias/tensiones, vista de alimentador (esquema no topología exacta salvo coordenadas verificadas), tabla por timestamp y panel LLM. Explorador: grafo navegable, as-of, evidencia y SPARQL modo solo consulta con límites. Comparación: B0/B1/B2, baseline vs optimizado, métricas, evidencias y exportación. Nunca graficar ceros ficticios ante ausencia de datos; mostrar N/D o NOT_VALIDATED.

## H. Árbol de archivos obligatorio; generar TODOS los archivos útiles con contenido real
Los comentarios `#` indican responsabilidad de cada archivo. No entregar carpetas con módulos vacíos, archivos duplicados ni scripts que llamen rutas inexistentes. `package-lock.json` se genera y fija con npm. Los archivos `*.local.json`, `.db`, `.ttl`, logs, dist y tokens se generan en runtime y NO se versionan.

```text
derms-tkg-power-lab/
├── README.md                          # Instalación y demostración Windows
├── PROMPT_MAESTRO.md                 # Esta especificación, íntegra
├── AGENTS.md                         # Reglas de cambios, pruebas y no inventar resultados
├── .gitignore                        # Excluye secretos, runtime, venv, dist, tokens
├── .env.example                      # Variables no sensibles
├── pyproject.toml                    # Dependencias Python, Ruff, pytest y scripts
├── secrets/
│   ├── README.md                     # Instrucción y permisos de secretos
│   ├── opendss.example.json          # Esquema de credenciales remotas, sin clave real
│   └── ollama.example.json           # Endpoint/modelo local, sin tokens
├── config/
│   ├── application.json              # HTTP timeouts, retry, cache, modo demo
│   ├── objective.json                # Términos, pesos, unidades y normalización
│   ├── scenario_ieee13.json          # IEEE13, BESS, FV, dt, límites y escala
│   ├── sources.json                  # Orígenes, source_kind, URLs y evidencia
│   └── cim_mapping.json              # Mapeo documentado DSS->RDF/CIM
├── backend/
│   └── app/
│       ├── __init__.py               # Paquete
│       ├── main.py                   # FastAPI, rutas, estáticos y ciclo de vida
│       ├── settings.py               # Config robusta, secretos server-side
│       ├── logging_config.py         # Logs estructurados sin JWT/passwords
│       ├── api/
│       │   ├── __init__.py           # Paquete API
│       │   ├── dependencies.py       # Servicios inyectados, autorización local
│       │   ├── status.py             # GET /api/status, estado y last_good
│       │   ├── sessions.py           # Listar/crear/unir sesiones remotas
│       │   ├── simulations.py        # Ejecutar QSTS, resultados, historial
│       │   ├── objectives.py         # Leer/validar/guardar función objetivo
│       │   ├── graph.py              # Nodos/aristas, as-of, SPARQL restringido
│       │   ├── experiments.py        # Comparar políticas y baselines
│       │   └── llm.py                # Preguntas, explicación y disponibilidad
│       ├── contracts/
│       │   ├── __init__.py           # Paquete esquemas
│       │   ├── upstream.py           # Pydantic: REST/WS OpenDSS observado
│       │   ├── scenario.py           # Escenario, perfiles, run, proveniencia
│       │   ├── objective.py          # Términos/pesos, resultados y validación
│       │   ├── graph.py              # Aserciones, tiempos, eventos, evidencia
│       │   └── llm.py                # Pregunta, citas, respuesta y propuesta
│       ├── integrations/
│       │   ├── __init__.py           # Paquete conectores
│       │   ├── opendss_auth.py        # POST token, bearer, renovación, errores
│       │   ├── opendss_http.py        # REST remoto, control de cuota/timeout
│       │   ├── opendss_ws.py          # WSS remoto, snapshot/progreso/reconexión
│       │   └── ollama_http.py         # POST /api/chat, JSON y timeouts
│       ├── services/
│       │   ├── __init__.py           # Paquete dominio
│       │   ├── health_monitor.py      # FSM de conectividad, freeze, recuperación
│       │   ├── run_manager.py         # Estados active_run/last_good, atomicidad
│       │   ├── qsts_bridge.py         # WS remoto -> WS local, correlación run
│       │   ├── ausgrid.py             # Ingesta 48 pasos, tz, kWh->kW, SHA256
│       │   ├── profile_mapper.py      # Perfil->48 multiplicadores, escala física
│       │   ├── dispatcher.py          # Optimización BESS/carga flexible
│       │   ├── objective_registry.py  # Términos modulares + normalización
│       │   ├── constraints.py         # SOC, potencia, eficiencia, balance
│       │   ├── electrical_check.py    # Matriz de soporte API + validación real
│       │   ├── custom_dss.py          # Generar ZIP DSS aislado, solo si compatible
│       │   ├── rdf_store.py           # RDFLib/Oxigraph, Turtle, named graphs
│       │   ├── cim_import.py          # Importación CIM/XML o DSS catalogado
│       │   ├── tkg_builder.py         # Aserciones temporalizadas y procedencia
│       │   ├── sparql_queries.py      # Consultas as-of, knowledge-at, evidencia
│       │   ├── explanation.py         # Evidencia LLM y explicación determinista
│       │   ├── comparisons.py         # B0/B1/B2 y métricas experimentales
│       │   └── orchestrator.py        # Salud->auth->WS->REST->validación->commit
│       ├── persistence/
│       │   ├── __init__.py           # Paquete almacenamiento
│       │   ├── sqlite_store.py        # Transacciones, historiales, last_good
│       │   ├── file_store.py          # Artefactos JSON/CSV/TTL con hashes
│       │   └── schema.sql            # SQLite runs, steps, source, dispatch, cache
│       └── api_ws.py                  # WebSocket local autenticado UI/live
├── frontend/
│   ├── package.json                   # Scripts npm y dependencias fijadas
│   ├── package-lock.json              # Lock generado por npm install
│   ├── biome.json                     # Formateo/lint JS/CSS/JSON
│   ├── vite.config.js                 # Bundling y proxy API/WS local
│   ├── index.html                     # App accesible y responsiva
│   ├── src/
│   │   ├── main.js                    # Arranque/navegación y eventos globales
│   │   ├── api.js                     # Cliente REST local, errores tipados
│   │   ├── state.js                   # Store reactivo y último run válido
│   │   ├── live.js                    # WS UI y sincronización de pasos
│   │   ├── pages/
│   │   │   ├── derms.js               # Simulación, controles, curvas, despachos
│   │   │   ├── graph.js               # Explorador RDF, filtros temporales
│   │   │   └── experiments.js         # Baselines e indicadores comparables
│   │   ├── components/
│   │   │   ├── status_bar.js          # Salud API/WS/LLM, datos conservados
│   │   │   ├── scenario_form.js       # IEEE13, Ausgrid, batería, objetivo
│   │   │   ├── timeline.js            # Playback con tiempos simulados
│   │   │   ├── feeder.js              # Vista topológica referencial
│   │   │   ├── charts.js              # Chart.js: potencia, FV, SOC, tensión
│   │   │   ├── dispatch_table.js      # 48 decisiones con etiquetas de origen
│   │   │   ├── graph_view.js          # Cytoscape, nodos/aristas y as-of
│   │   │   ├── evidence.js            # Auditoría, hashes y explicaciones
│   │   │   └── llm_panel.js           # Chat contextual y citas verificables
│   │   └── styles/
│   │       ├── tokens.css             # Colores, tipografía y espaciado
│   │       └── app.css                # Layout limpio y adaptable
├── data/
│   ├── raw/README.md                  # Descargas externas y atribución
│   ├── processed/README.md            # Contrato CSV normalizado/manifest
│   ├── fixtures/ausgrid_mock.csv      # Muestra SINTÉTICA, pruebas offline
│   └── runtime/.gitkeep               # SQLite/TTL/export generados, ignorados
├── scripts/
│   ├── setup.ps1                       # venv, pip, npm y copia config ejemplo
│   ├── start.ps1                       # Levantar backend + frontend en Windows
│   ├── check_remote.ps1                # Health, auth, modelos sin mutaciones
│   ├── smoke_qsts.ps1                  # Sesión/QSTS 3 pasos + WS + results
│   ├── test_all.ps1                    # Ruff, Biome, pytest, tests frontend
│   └── export_evidence.ps1             # ZIP sin secretos y reporte de run
├── tests/
│   ├── conftest.py                     # Fixtures y servidor OpenDSS ficticio
│   ├── test_upstream_contract.py       # Rutas, token, payloads, schemas
│   ├── test_health_freeze.py           # Caída conserva last_good y no POST
│   ├── test_ws_recovery.py             # Reconexión, duplicados, pérdida sesión
│   ├── test_qsts_flow.py               # REST+WS+GET results y consistencia
│   ├── test_ausgrid.py                 # Fuente, timezone, 48 pasos, unidades
│   ├── test_dispatch.py                # SOC, potencias, constraints, objetivo
│   ├── test_objectives.py              # Pesos editables y nuevos términos
│   ├── test_tkg.py                     # RDF/CIM, as-of, bitemporal, procedencia
│   ├── test_llm.py                     # Ollama caído, evidencia y JSON seguro
│   ├── test_recovery.py                # Persistencia tras reinicio y rollback
│   └── test_security.py                # Sin filtraciones, inyección y permisos
├── docs/
│   ├── REUSE_INVENTORY.md              # Qué se reutiliza de ambos proyectos
│   ├── ARCHITECTURE.md                 # Diagrama, componentes, modos validación
│   ├── REMOTE_API_CONTRACT.md          # Contratos probados REST y WSS
│   ├── RDF_CIM_TKG.md                  # Ontología, temporalidad, SPARQL, límites
│   ├── OPTIMIZATION.md                 # Objetivos, unidades, hipótesis, solver
│   ├── PROVENANCE.md                   # REAL/SIMULATED/DERIVED/REFERENCE
│   ├── OPERATIONS.md                   # PowerShell, CloudFront, credenciales, fallos
│   ├── TEST_REPORT.md                  # Pruebas ejecutadas, fallos y evidencia
│   └── DEMO_SCRIPT.md                  # Demo de 10 min y criterios de aceptación
└── results/README.md                   # Ubicación y convenciones de exportaciones
```

## I. API local mínima y mensajes
Backend expone `GET /api/status`, `GET /api/models`, `GET /api/sessions`, `POST /api/sessions`, `POST /api/runs`, `GET /api/runs/{run_id}`, `GET /api/runs/{run_id}/steps`, `POST /api/runs/{run_id}/dispatch`, `POST /api/runs/{run_id}/verify` (rechazar `NOT_SUPPORTED` honestamente), `GET/PUT /api/objective`, `GET /api/graph/asof?run_id=&at=`, `POST /api/graph/query` limitado, `POST /api/llm/explain`, `GET /api/experiments/compare`, `WS /api/live/{run_id}`. Documentar ejemplos JSON Pydantic, códigos de error, controles y quién es dueño de la sesión. Proteger rutas mutantes locales contra acceso externo/CSRF según topología de despliegue. Ningún endpoint remoto inventado.

## J. Calidad, aceptación y entrega
- Python 3.11+ (ajustar a restricciones reales), tipos, docstrings, estructura pequeña, `ruff check .` y `ruff format --check .` sin errores; frontend `npx biome check .` sin errores; bloqueo de dependencias y tests `pytest -q` + pruebas de frontend. No añadir 7 frameworks para tareas simples. Comentarios explican **por qué**, no repiten lo que ya dice el código.
- Test 1: con `/health` sano, login y `/models` permiten elegir IEEE13; se registra `session_id`. Sin respuesta de health, **no se ejecuta POST** y se conserva `last_good_run` en disco y pantalla con aviso de fecha.
- Test 2: suscribirse WSS antes del solve; ejecutar QSTS 3 pasos (0.25h a 5min) con `[0.8, 1.0, 1.2]` y verificar `snapshot`, `qsts_progress`, `result`, `completed`, `/results.steps == 3`; para flujo principal 24h/30min exige exactamente 48 registros. Probar 401, 403, 404, 429, WS 1008/1013, timeout, duplicados y expiración JWT.
- Test 3: ejecutar planificador sin conexión externa con fixtures simulados y demostrar límites SOC, balance y cambio de objetivo; comprobar que no confunde BESS local con control remoto.
- Test 4: construir y consultar TKG RDF/TTL con fuente/validez/registro y mostrar estado antes/después de indisponibilidad, incluyendo caso de dato tardío. B0/B1/B2 sobre datos idénticos.
- Test 5: Ollama indisponible no impide simulación; cuando esté disponible las explicaciones citan fuentes y su JSON se valida. LLM sin permisos de ejecutar comandos.
- Test 6: guardar CSV + SQLite + TTL + manifest SHA256 y reporte de corrida, reabrir offline, mostrar estado obsoleto, conservar último resultado confirmado; `export_evidence.ps1` no contiene secretos.
- Entrega **completa**: crear todos los archivos mencionados, instalación con comandos PowerShell exactos, árbol final verificado, matriz de cobertura y informe de ejecución con `PASS/FAIL/NOT_RUN`. Ejecutar lo posible en el entorno; jamás fabricar una llamada a CloudFront/OpenDSS ni dar por integrado un storage no soportado.

**Orden de implementación obligatorio:** 1) contratos reales/auth/health; 2) cache inmutable/WS REST; 3) perfil Ausgrid+QSTS remoto; 4) optimizador configurable offline; 5) RDF/CIM y SPARQL; 6) interfaz; 7) Ollama; 8) adaptación DSS custom y validación eléctrica si la API permite; 9) pruebas, documentación y reporte. Después de cada fase conservar todo lo que funciona. Si hay límites del API, entregar el flujo honesto funcionando y registrar el bloqueo específico. **No empezar el módulo de fallas todavía.**
