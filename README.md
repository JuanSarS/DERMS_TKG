# DERMS TKG Power Lab

**Prototipo Tesis II, no un EMS industrial ni un sistema de protección/control físico.**

Una aplicación web con FastAPI (backend) y JavaScript/Vite (frontend) que conecta con OpenDSS Cloud mediante REST/WSS, ejecuta QSTS de 48 pasos, conserva corridas verificadas y permite optimizar un modelo energético BESS/FV/carga flexible de forma desacoplada. Utiliza el modelo CIM100 RDF/XML real de IEEE13 aportado por el usuario, genera un grafo temporal RDF y admite explicaciones locales opcionales mediante Ollama.

## Windows 11 · instalación

```powershell
Expand-Archive "$HOME\Downloads\derms-tkg-power-lab.zip" "$HOME\Documents" -Force
cd "$HOME\Documents\derms-tkg-power-lab"
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

Edite **solamente** `secrets/opendss.local.json`: `base_url` usa `https://d2u0styn2zl3g5.cloudfront.net`; complete `username` y `password` localmente. Credenciales provisionales `admin`/`admin` solo si siguen siendo válidas en su servidor de laboratorio, y deben rotarse. No aparecen en frontend ni en el ZIP. Para Ollama, copie `secrets/ollama.example.json` a `secrets/ollama.local.json`, establezca `enabled=true` y el modelo instalado.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_remote.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

Abra `http://127.0.0.1:5173`. El servidor backend queda en `http://127.0.0.1:8088/docs`. Si no hay CloudFront, el estado será OFFLINE; la última corrida verificada continuará disponible. El botón **Laboratorio offline explícito** ejecuta un ensayo local separado y **NO** suplanta el histórico remoto.

Para prueba remota mutante **solo con consentimiento**:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke_qsts.ps1 -ConfirmRemoteMutation
```

## Calidad

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test_all.ps1
```

El flujo QSTS remoto crea sesión y se suscribe primero a `WSS /ws/simulations/{id}`. El POST `/simulations/{id}/solve` acepta multiplicadores globales, no consignas BESS. Los resultados remotos finales solo se confirman después de `GET /results`, validación de pasos y convergencia. Un error de conexión nunca reemplaza `last_good_run`.

## Evidencia

Los datos de Ausgrid son mediciones históricas procesadas con procedencia documentada; IEEE13/CIM es una red de referencia sin vinculación física directa. La tarifa, BESS y carga flexible son escenarios modelados. El optimizador usa SciPy MILP con variables binarias de carga/descarga, importación/exportación y carga flexible, límites SOC, eficiencias, pérdidas y función objetivo editable en `config/objective.json`. Los resultados de la batería continúan como `NOT_VALIDATED` eléctricamente hasta ejecutar un modelo OpenDSS que aplique efectivamente tales consignas.

Más detalle: `docs/ARCHITECTURE.md`, `docs/REMOTE_API_CONTRACT.md`, `docs/OPTIMIZATION.md` y `docs/TEST_REPORT.md`.
