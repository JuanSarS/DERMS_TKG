"""Matriz explícita de capacidad real de la API; no falsificar validación BESS."""


def capability() -> dict:
    return {
        "remote_qsts_global_load": True,
        "remote_bess_setpoint_per_step": False,
        "remote_pv_per_step": False,
        "custom_dss_upload_admin": True,
        "actual_custom_model_run": "NOT_RUN",
        "battery_dispatch_electrical_verified": False,
    }


def verify_dispatch(_run: dict) -> dict:
    return {
        "status": "NOT_SUPPORTED",
        "reason": "La API /simulations/{id}/solve acepta solo load_multipliers globales; no setpoints de Storage/PV por intervalo.",
        "possible_next_step": "Validar un paquete DSS personalizado en una prueba aislada, no modificar el servicio original.",
    }
