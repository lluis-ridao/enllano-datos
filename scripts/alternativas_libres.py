"""Alternativas libres en cifras: estrellas en GitHub y descargas en Flathub (total, último mes y desde España).

Lista editable en config/alternativas.json. Sin clave obligatoria; en GitHub Actions usa GITHUB_TOKEN.
"""
import json
import os

from comun import CONFIG, FuenteNoDisponible, ejecutar, guardar, leer_previo, pedir


def github(repo):
    if not repo:
        return {}
    cab = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        cab["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    try:
        j = pedir(f"https://api.github.com/repos/{repo}", cabeceras=cab, intentos=2)
    except FuenteNoDisponible:
        return {}
    return {"estrellas": j.get("stargazers_count"), "ultimo_cambio": (j.get("pushed_at") or "")[:10],
            "licencia": ((j.get("license") or {}).get("spdx_id") or "")}


def flathub(app):
    if not app:
        return {}
    try:
        j = pedir(f"https://flathub.org/api/v2/stats/{app}", intentos=2)
    except FuenteNoDisponible:
        return {}
    if not isinstance(j, dict):
        return {}
    pais = j.get("installs_per_country") or {}
    return {"descargas_total": j.get("installs_total"), "descargas_mes": j.get("installs_last_month"),
            "descargas_espana": pais.get("ES") if isinstance(pais, dict) else None}


def main():
    apps = json.loads((CONFIG / "alternativas.json").read_text("utf-8"))
    previo = {a["nombre"]: a for a in (leer_previo("alternativas-libres") or {}).get("datos", {}).get("apps", [])}
    salida, fallos = [], 0
    for a in apps:
        g, f = github(a.get("github")), flathub(a.get("flathub"))
        if (a.get("github") and not g) or (a.get("flathub") and not f):
            fallos += 1
            old = previo.get(a["nombre"], {})  # conserva la última cifra buena de cada app
            g = g or {k: old.get(k) for k in ("estrellas", "ultimo_cambio", "licencia")}
            f = f or {k: old.get(k) for k in ("descargas_total", "descargas_mes", "descargas_espana")}
        salida.append({**{k: a[k] for k in ("nombre", "alternativa_a", "categoria", "web")},
                       "github": a.get("github", ""), "flathub": a.get("flathub", ""), **g, **f})
    if fallos == len(apps):
        raise FuenteNoDisponible("GitHub y Flathub no respondieron")
    salida.sort(key=lambda x: -(x.get("descargas_total") or 0))
    guardar(
        "alternativas-libres",
        {"apps": salida},
        titulo="Alternativas libres en cifras",
        descripcion="Programas libres que sustituyen a los de pago más conocidos: estrellas en GitHub y descargas en Flathub.",
        fuente="GitHub API y estadísticas públicas de Flathub",
        url_fuente="https://flathub.org/statistics",
        licencia="CC BY 4.0 (recopilación de enllano)",
        filas_csv=salida,
        campos_csv=["nombre", "alternativa_a", "categoria", "estrellas", "descargas_total", "descargas_mes",
                    "descargas_espana", "licencia", "ultimo_cambio", "github", "flathub", "web"],
        nota="Flathub cuenta descargas en Linux (instalaciones y algunas actualizaciones), no usuarios activos.",
    )


if __name__ == "__main__":
    ejecutar(main)
