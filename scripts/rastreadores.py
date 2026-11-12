"""Rastreadores en webs públicas españolas ANTES de aceptar cookies.

Abre la portada de cada web de config/webs-publicas.json con un navegador sin pantalla (Chromium vía Playwright),
como lo haría cualquier visitante, SIN pulsar ningún botón del aviso de cookies. Anota a qué dominios de
terceros se conecta y qué cookies de terceros deja. Clasifica los dominios con la lista abierta de Disconnect.

Es un análisis pasivo: una sola visita a la portada, sin formularios ni pruebas de seguridad.

Uso:  python scripts/rastreadores.py            (todas las webs)
      python scripts/rastreadores.py --prueba    (clasifica un HAR de ejemplo, sin navegador)
"""
import json
import sys
from datetime import date

import tldextract

from comun import CONFIG, FuenteNoDisponible, ejecutar, guardar, pedir

DISCONNECT = "https://raw.githubusercontent.com/disconnectme/disconnect-tracking-protection/master/services.json"
# Categorías de Disconnect que cuentan como rastreo (se excluyen contenido, antifraude y gestores de consentimiento).
RASTREO = {"Advertising": "Publicidad", "Analytics": "Analítica", "Social": "Redes sociales",
           "FingerprintingInvasive": "Huella digital", "FingerprintingGeneral": "Huella digital",
           "Cryptomining": "Criptominería", "Email": "Rastreo de correo", "EmailAggressive": "Rastreo de correo"}
ESPERA_MS = 6000

extraer = tldextract.TLDExtract(suffix_list_urls=())  # usa la lista de sufijos incluida, sin red


def base(host):
    e = extraer(host)
    return f"{e.domain}.{e.suffix}" if e.suffix else host


def mapa_disconnect():
    j = pedir(DISCONNECT)
    m = {}
    cats = j.get("categories", {})
    for cat in RASTREO:  # en orden de prioridad: un dominio se queda con su primera categoría
        for ent in cats.get(cat, []):
            for empresa, sitios in ent.items():
                for _, dominios in sitios.items():
                    if isinstance(dominios, list):
                        for d in dominios:
                            m.setdefault(d.lower(), (empresa, RASTREO[cat]))
    return m


def clasificar(host, mapa):
    partes = host.lower().split(".")
    for i in range(len(partes) - 1):
        d = ".".join(partes[i:])
        if d in mapa:
            return mapa[d]
    return None


def resumir_web(web, hosts, cookies, mapa):
    propio = base(web["host"])
    terceros = sorted({base(h) for h in hosts if base(h) != propio})
    rastreadores = {}
    for h in hosts:
        if base(h) == propio:
            continue
        c = clasificar(h, mapa)
        if c:
            rastreadores.setdefault(base(h), {"dominio": base(h), "empresa": c[0], "categoria": c[1]})
    cookies_ter = [c for c in cookies if base(c.lstrip(".")) != propio]
    return {
        "nombre": web["nombre"], "url": web["url"], "tipo": web["tipo"], "ok": True,
        "terceros": len(terceros),
        "rastreadores": sorted(rastreadores.values(), key=lambda x: (x["empresa"], x["dominio"])),
        "empresas": sorted({r["empresa"] for r in rastreadores.values()}),
        "cookies_terceros": len(set(cookies_ter)),
    }


def visitar(webs, mapa):
    from playwright.sync_api import sync_playwright  # solo hace falta en el modo real

    res = []
    with sync_playwright() as p:
        nav = p.chromium.launch()
        for w in webs:
            ctx = nav.new_context(locale="es-ES", timezone_id="Europe/Madrid",
                                  user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36 enllano-datos")
            hosts = set()
            pag = ctx.new_page()
            pag.on("request", lambda r: hosts.add(r.url.split("/")[2].split(":")[0]) if r.url.startswith("http") else None)
            try:
                pag.goto(w["url"], wait_until="load", timeout=45000)
                pag.wait_for_timeout(ESPERA_MS)
                w["host"] = pag.url.split("/")[2].split(":")[0]
                cookies = [c["domain"] for c in ctx.cookies()]
                res.append(resumir_web(w, hosts, cookies, mapa))
                print(f"  {w['nombre']}: {len(res[-1]['rastreadores'])} rastreadores")
            except Exception as e:  # noqa: BLE001 - una web caída no debe parar el resto
                print(f"  {w['nombre']}: no se pudo abrir ({type(e).__name__})")
                res.append({"nombre": w["nombre"], "url": w["url"], "tipo": w["tipo"], "ok": False})
            finally:
                ctx.close()
        nav.close()
    return res


def main():
    webs = json.loads((CONFIG / "webs-publicas.json").read_text("utf-8"))
    for w in webs:
        w["host"] = w["url"].split("/")[2]
    mapa = mapa_disconnect()
    if "--prueba" in sys.argv:
        f = json.loads(open(sys.argv[sys.argv.index("--prueba") + 1], encoding="utf-8").read())
        res = [resumir_web(next(w for w in webs if w["nombre"] == x["nombre"]), x["hosts"], x["cookies"], mapa) for x in f]
    else:
        res = visitar(webs, mapa)
    ok = [r for r in res if r.get("ok")]
    if "--prueba" not in sys.argv and len(ok) < max(3, len(webs) // 3):
        raise FuenteNoDisponible(f"solo se pudieron abrir {len(ok)} webs")

    empresas = {}
    for r in ok:
        for e in r["empresas"]:
            empresas[e] = empresas.get(e, 0) + 1
    con = sum(1 for r in ok if r["rastreadores"])
    res.sort(key=lambda r: (-len(r.get("rastreadores", [])), r["nombre"]))
    filas = [{"web": r["nombre"], "tipo": r["tipo"], "url": r["url"],
              "rastreadores": len(r.get("rastreadores", [])) if r.get("ok") else "",
              "empresas": "; ".join(r.get("empresas", [])), "dominios_terceros": r.get("terceros", ""),
              "cookies_terceros": r.get("cookies_terceros", ""), "analizada": "sí" if r.get("ok") else "no",
              "fecha": date.today().isoformat()} for r in res]
    guardar(
        "rastreadores-webs-publicas",
        {
            "fecha": date.today().isoformat(),
            "analizadas": len(ok),
            "con_rastreadores": con,
            "pct_con_rastreadores": round(con / len(ok) * 100) if ok else 0,
            "empresas": dict(sorted(empresas.items(), key=lambda kv: -kv[1])),
            "webs": res,
        },
        titulo="Rastreadores en webs públicas españolas antes de aceptar cookies",
        descripcion="Qué empresas de publicidad, analítica o redes sociales reciben datos al abrir la portada de webs de la Administración, sin aceptar cookies.",
        fuente="Análisis propio de enllano con Playwright; clasificación con la lista de Disconnect",
        url_fuente="https://github.com/disconnectme/disconnect-tracking-protection",
        licencia="CC BY 4.0 (datos de enllano)",
        filas_csv=filas,
        campos_csv=["web", "tipo", "url", "rastreadores", "empresas", "dominios_terceros", "cookies_terceros", "analizada", "fecha"],
        nota="Una visita automática a la portada desde un servidor de GitHub, sin interactuar con el aviso de cookies. Que se cargue un dominio de terceros no prueba por sí solo una infracción: es un indicio para revisar.",
    )


if __name__ == "__main__":
    ejecutar(main)
