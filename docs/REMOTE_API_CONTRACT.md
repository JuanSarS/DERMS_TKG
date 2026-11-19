# API OpenDSS observada en el código del proyecto

- `GET /health`: HTTP 200 + `{"status":"ok"}`.
- `POST /auth/token`: formulario `username`, `password`, devuelve JWT y cookie `opendss_access_token`; se usa REST `Authorization: Bearer`.
- `GET /auth/me`, `GET /models`, `GET /simulations`, `POST /simulations` (`topology`, `load_multiplier`) y `GET /simulations/{session_id}`.
- `POST /simulations/{session_id}/solve` con `{ "simulation_type":"qsts", "qsts":{"duration_hours":24,"step_minutes":30,"profile_source":"values","load_multipliers":[48 valores >0]} }`.
- `WS /ws/simulations/{id}` token en subprotocolos `opendss.jwt` y `<token>`; snapshot inmediato; mensajes `qsts_progress`, `result`, `completed`, `error`. El WS no acepta controles. Suscribirse **ANTES** de `/solve`.
- `GET /simulations/{id}/results`: `steps[]` con `converged`, `total_kw`, `min_voltage_pu`, etc. Este GET es la autoridad del cierre válido.
- La subida `POST /models/upload` requiere admin y modelos personalizados, pero no se usa para presentar BESS como verificada sin prueba explícita.
- La URL más reciente suministrada por el usuario: `https://d2u0styn2zl3g5.cloudfront.net`. **La conectividad real debe comprobarse desde su entorno; la presencia del código no prueba despliegue.**
