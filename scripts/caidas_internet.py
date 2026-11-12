"""Caídas de internet en España y Europa (Cloudflare Radar, Outage Center).

Secreto necesario: CLOUDFLARE_API_TOKEN (token con permiso de lectura «Radar»; es gratis).
Licencia de los datos de Cloudflare Radar: CC BY-NC 4.0.
"""
from comun import ejecutar, guardar, pedir, secreto

API = "https://api.cloudflare.com/client/v4/radar/annotations/outages"

CAUSAS = {
    "POWER_OUTAGE": "Corte eléctrico", "CABLE_CUT": "Corte de cable", "WEATHER": "Meteorología",
    "GOVERNMENT_DIRECTED": "Orden de un gobierno", "MAINTENANCE": "Mantenimiento", "CYBERATTACK": "Ciberataque",
    "TECHNICAL_PROBLEM": "Problema técnico", "FIRE": "Incendio", "EARTHQUAKE": "Terremoto",
    "MILITARY_ACTION": "Acción militar", "DNS": "Fallo de DNS", "BLOCKING": "Bloqueo", "MECHANICAL": "Avería",
    "UNKNOWN": "Desconocida",
}
TIPOS = {"NATIONWIDE": "Todo el país", "REGIONAL": "Regional", "NETWORK": "Un operador", "PLATFORM": "Una plataforma"}
EUROPA = set("AL AD AT BA BE BG BY CH CY CZ DE DK EE ES FI FR GB GR HR HU IE IS IT LI LT LU LV MC MD ME MK MT NL NO PL PT RO RS SE SI SK SM UA XK".split())


def main():
    tok = secreto("CLOUDFLARE_API_TOKEN")
    cab = {"Authorization": f"Bearer {tok}"}

    j = pedir(API, {"location": "ES", "dateRange": "52w", "limit": 100, "format": "json"}, cab)
    anot = (j.get("result") or {}).get("annotations") or []
    caidas = []
    for a in anot:
        o = a.get("outage") or {}
        caidas.append({
            "inicio": (a.get("startDate") or "")[:16],
            "fin": (a.get("endDate") or "")[:16],
            "causa": CAUSAS.get(o.get("outageCause", ""), (o.get("outageCause") or "").replace("_", " ").capitalize()),
            "tipo": TIPOS.get(o.get("outageType", ""), o.get("outageType") or ""),
            "alcance": a.get("scope") or "",
            "operadores": [x.get("name") for x in (a.get("asnsDetails") or []) if x.get("name")],
            "descripcion": a.get("description") or "",
            "enlace": a.get("linkedUrl") or "",
        })
    caidas.sort(key=lambda x: x["inicio"], reverse=True)

    j2 = pedir(API + "/locations", {"dateRange": "52w", "limit": 200, "format": "json"}, cab)
    paises = {}
    for x in (j2.get("result") or {}).get("annotations") or []:
        c = x.get("clientCountryAlpha2", "")
        if c in EUROPA:
            paises[c] = {"nombre": x.get("clientCountryName", c), "caidas": int(float(x.get("value", 0)))}
    paises = dict(sorted(paises.items(), key=lambda kv: -kv[1]["caidas"]))

    guardar(
        "caidas-internet",
        {"espana": caidas, "europa": paises},
        titulo="Caídas de internet en España y Europa",
        descripcion="Cortes de conexión detectados y verificados por Cloudflare Radar en las últimas 52 semanas.",
        fuente="Cloudflare Radar",
        url_fuente="https://radar.cloudflare.com/outage-center",
        licencia="CC BY-NC 4.0 (Cloudflare Radar)",
        filas_csv=[{**c, "operadores": "; ".join(c["operadores"])} for c in caidas],
        campos_csv=["inicio", "fin", "causa", "tipo", "alcance", "operadores", "descripcion", "enlace"],
    )


if __name__ == "__main__":
    ejecutar(main)
