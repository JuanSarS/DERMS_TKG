"""Mapeo explícitamente modelado del perfil del hogar a multiplicador GLOBAL QSTS."""


def to_multipliers(profile: dict, *, scale_multiplier: float = 1) -> list[float]:
    loads = [r["load_kw"] for r in profile["records"]]
    average = sum(loads) / len(loads)
    if average <= 0:
        raise ValueError("Perfil de carga sin base positiva")
    multiples = [round(scale_multiplier * x / average, 6) for x in loads]
    if any(not (0 < x <= 5) for x in multiples):
        raise ValueError("La API exige multiplicadores positivos <= 5; cambie el escalamiento")
    return multiples
