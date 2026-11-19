# Estado de pruebas

Use `scripts/test_all.ps1` para confirmar versión local. Las pruebas automatizadas no sustituyen conexión real ni laboratorio eléctrico.

| Caso | Estado | Alcance |
|---|---|---|
| Python pytest offline | PASS (22 pruebas en el entorno de creación; repetir en Windows) | Contratos, MILP, CIM100, TKG, persistencia, WSS falso, seguridad |
| Curl /health CloudFront | NOT_RUN / NO VERIFICABLE | No se ha confirmado endpoint remoto saludable |
| QSTS REST+WSS remoto real | NOT_RUN | Requiere servicio y credenciales reales |
| Verificación eléctrica de BESS | NOT_SUPPORTED | API expone multiplicadores globales, no setpoints Storage |
| Ollama con modelo instalado | NOT_RUN | Opcional, no hay modelo conectado en evaluación offline |
| SAIDI/SAIFI | OUT_OF_SCOPE | Se evaluarán en Tesis II con datos de interrupciones |
| Frontend npm/Vite/Biome | NOT_RUN: npm registry inaccesible desde el entorno de creación; npm install lo realiza en Windows | Entorno debe disponer de acceso a paquetes npm |

- `node --check` en todos los módulos JS: **PASS**.
- `node --test frontend/tests/*.test.js`: **2 PASS**.
- `python -m compileall -q backend tests scripts`: **PASS**.
- FastAPI TestClient con proveedor remoto simulado: **PASS** (`/api/status=OFFLINE`, `POST /api/runs=503`, `POST /api/experiments/offline=200`, RDF y comparación).
- `ruff check` / `ruff format --check`: **NOT_RUN** en entorno de creación, `ruff` no pudo descargarse. Setup ejecuta Ruff con correcciones seguras y pruebas posteriores.
- Frontend `npm install` devolvió **EAI_AGAIN** por acceso a `registry.npmjs.org`, por eso el lockfile se genera al instalar en equipo con conexión.
- `/health` de CloudFront no pudo comprobarse de forma concluyente desde el entorno de construcción; **NOT_VERIFIED**, no se interpreta como caída confirmada del servicio.
