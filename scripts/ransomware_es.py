"""Reivindicaciones de ransomware contra organizaciones de España, por mes y sector.

Fuente: Ransomware.live (API PRO gratuita con clave personal, uso no comercial con atribución).
Solo se publican RECUENTOS. Nunca nombres de víctimas: son afirmaciones de delincuentes, no ataques confirmados.

Secreto necesario: RWL_API_KEY
"""
from datetime import date

from comun import ejecutar, guardar, leer_previo, pedir, secreto

MESES = 24
API = "https://api-pro.ransomware.live/victims/"

SECTORES = {
    "Technology": "Tecnología", "Government": "Administración pública", "Public Sector": "Administración pública",
    "Healthcare": "Sanidad", "Construction": "Construcción", "Manufacturing": "Industria", "Education": "Educación",
    "Financial Services": "Servicios financieros", "Business Services": "Servicios a empresas",
    "Transportation/Logistics": "Transporte y logística", "Retail": "Comercio",
    "Hospitality and Tourism": "Turismo y hostelería", "Energy": "Energía", "Telecommunication": "Telecomunicaciones",
    "Agriculture and Food Production": "Agricultura y alimentación", "Consumer Services": "Servicios al consumidor",
    "Media & Entertainment": "Medios y ocio", "Legal": "Legal", "Real Estate": "Inmobiliario", "Insurance": "Seguros",
    "Pharmaceutical": "Farmacéutico",
}


def lista(j):
    if isinstance(j, list):
        return j
    if isinstance(j, dict):
        for k in ("victims", "data", "results", "items"):
            if isinstance(j.get(k), list):
                return j[k]
    return []


def campo(r, claves):
    for k in claves:
        v = r.get(k)
        if v and isinstance(v, (str, int, float)):
            return str(v)
    return ""


def meses_atras(n):
    hoy = date.today().replace(day=1)
    out = []
    y, m = hoy.year, hoy.month
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return sorted(out)


def main():
    clave = secreto("RWL_API_KEY")
    previo = leer_previo("ransomware-espana")
    guardados = {x["mes"]: x for x in (previo or {}).get("datos", {}).get("meses", [])}
    meses = meses_atras(MESES)
    recientes = set(meses[-2:])  # el mes actual y el anterior siempre se refrescan

    resultado = []
    for ym in meses:
        if ym in guardados and ym not in recientes:
            resultado.append(guardados[ym])
            continue
        j = pedir(API, {"year": ym[:4], "month": ym[5:]}, {"X-API-KEY": clave})
        sect = {}
        total = 0
        for v in lista(j):
            pais = campo(v, ["country", "country_code"]).upper()[:2]
            if pais != "ES":
                continue
            total += 1
            s = campo(v, ["activity", "sector", "industry"])
            s = "Sin clasificar" if s in ("", "Not Found") else SECTORES.get(s, s)
            sect[s] = sect.get(s, 0) + 1
        resultado.append({"mes": ym, "total": total, "sectores": dict(sorted(sect.items(), key=lambda x: -x[1]))})

    tot_sect = {}
    for x in resultado:
        for s, n in x["sectores"].items():
            tot_sect[s] = tot_sect.get(s, 0) + n
    filas = [{"mes": x["mes"], "sector": s, "reivindicaciones": n} for x in resultado for s, n in x["sectores"].items()]

    guardar(
        "ransomware-espana",
        {
            "meses": resultado,
            "sectores_total": dict(sorted(tot_sect.items(), key=lambda x: -x[1])),
            "total": sum(x["total"] for x in resultado),
        },
        titulo="Reivindicaciones de ransomware contra organizaciones de España",
        descripcion=f"Recuento mensual por sector de los últimos {MESES} meses. Solo recuentos, sin nombres.",
        fuente="Ransomware.live",
        url_fuente="https://www.ransomware.live",
        licencia="Recuentos de enllano a partir de Ransomware.live (uso no comercial, con atribución)",
        filas_csv=filas,
        campos_csv=["mes", "sector", "reivindicaciones"],
        nota="Son afirmaciones publicadas por bandas criminales en sus webs de filtraciones, no ataques confirmados.",
    )


if __name__ == "__main__":
    ejecutar(main)
