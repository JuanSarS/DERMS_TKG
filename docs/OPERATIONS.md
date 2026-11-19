# Operación Windows / incidencias

1. `powershell -ExecutionPolicy Bypass -File scripts/setup.ps1` crea entorno, instala backend y frontend.
2. Configure `secrets/opendss.local.json` **solo** en la máquina de trabajo, sin versionar.
3. `powershell -ExecutionPolicy Bypass -File scripts/check_remote.ps1` comprueba salud/login/modelos, sin mutar sesiones.
4. `powershell -ExecutionPolicy Bypass -File scripts/start.ps1`, y abra `http://127.0.0.1:5173`.
5. Si CloudFront está OFFLINE, NO se crean nuevas sesiones ni se borra la última corrida. Use laboratorio offline solo si quiere un experimento **nuevo y separado**.
6. `AUTH_ERROR` indica credenciales inválidas/expiradas; `DEGRADED_WS` permite inspeccionar resultados recuperados por REST; `ERROR` conserva eventos provisionales para auditoría sin alterar `last_good_run`.
7. `scripts/smoke_qsts.ps1 -ConfirmRemoteMutation` crea sesión QSTS remota de 3 pasos. No ejecutar por defecto.
8. `scripts/export_evidence.ps1 -RunId ...` crea ZIP del run sin carpetas de secretos.
9. Si cambio objetivo, la ejecución previa conserva el objetivo original; se crea una nueva corrida derivada.
