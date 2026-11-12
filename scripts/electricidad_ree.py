"""Demanda eléctrica y peso de las renovables en España (Red Eléctrica, REData API).

Sin clave. Licencia: datos abiertos de Red Eléctrica (reutilización con cita de la fuente).
"""
from datetime import date, timedelta

from comun import FuenteNoDisponible, ejecutar, guardar, pedir

API = "https://apidatos.ree.es/es/datos/"


def valores(j, titulo=None):
    """Lista de (fecha, valor) del indicador indicado (o el primero)."""
    inc = j.get("included") if isinstance(j, dict) else None
    if not inc:
        raise FuenteNoDisponible("REE devolvió una respuesta sin datos")
    for i in inc:
        a = i.get("attributes", {})
        if titulo is None or a.get("title", "").lower() == titulo.lower():
            return [(v["datetime"][:10], float(v["value"])) for v in a.get("values", []) if v.get("value") is not None]
    return []


def rango(widget, desde, hasta, trunc="day"):
    return pedir(API + widget, {
        "start_date": f"{desde.isoformat()}T00:00",
        "end_date": f"{hasta.isoformat()}T23:59",
        "time_trunc": trunc,
    }, {"Accept": "application/json"})


def main():
    hoy = date.today()
    ayer = hoy - timedelta(days=1)

    # Demanda diaria del último año, pedida mes a mes (la API limita el rango diario).
    diaria = {}
    ini = (hoy.replace(day=1) - timedelta(days=365)).replace(day=1)
    while ini <= ayer:
        fin = min((ini.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1), ayer)
        for f, v in valores(rango("demanda/evolucion", ini, fin)):
            diaria[f] = v
        ini = fin + timedelta(days=1)
    if not diaria:
        raise FuenteNoDisponible("REE: sin datos de demanda")

    mensual = {}
    for f, v in diaria.items():
        mensual[f[:7]] = mensual.get(f[:7], 0) + v
    meses = [{"mes": m, "gwh": round(v / 1000, 1), "dias": sum(1 for f in diaria if f.startswith(m))} for m, v in sorted(mensual.items())]

    # Renovable frente a no renovable, últimos 30 días.
    j = rango("generacion/evolucion-renovable-no-renovable", hoy - timedelta(days=30), ayer)
    ren = dict(valores(j, "Renovable"))
    noren = dict(valores(j, "No renovable"))
    dias_ren = []
    for f in sorted(set(ren) | set(noren)):
        r, n = ren.get(f, 0), noren.get(f, 0)
        if r + n > 0:
            dias_ren.append({"fecha": f, "renovable_pct": round(r / (r + n) * 100, 1)})
    media_ren = round(sum(d["renovable_pct"] for d in dias_ren) / len(dias_ren), 1) if dias_ren else None

    ult = sorted(diaria)[-1]
    guardar(
        "demanda-electrica",
        {
            "ultimo_dia": {"fecha": ult, "gwh": round(diaria[ult] / 1000, 1)},
            "meses": meses,
            "renovable_30d": {"media_pct": media_ren, "dias": dias_ren},
            "diaria": [{"fecha": f, "mwh": round(v)} for f, v in sorted(diaria.items())],
        },
        titulo="Demanda eléctrica y renovables en España",
        descripcion="Demanda diaria y mensual del último año y porcentaje de generación renovable de los últimos 30 días.",
        fuente="Red Eléctrica (REData)",
        url_fuente="https://www.ree.es/es/datos/apidatos",
        licencia="Datos abiertos de Red Eléctrica, reutilización citando la fuente",
        filas_csv=[{"fecha": f, "demanda_mwh": round(v)} for f, v in sorted(diaria.items())],
        campos_csv=["fecha", "demanda_mwh"],
    )


if __name__ == "__main__":
    ejecutar(main)
