"""Genera datos/catalogo.json (lista de descargas) y mapas/manifest.json (versión de los mapas).

La web lee el catálogo para la página /datos/ y el manifiesto para saber si hay mapas nuevos.
"""
import hashlib
import json

from comun import DATOS, RAIZ, ahora_iso

RAW = "https://raw.githubusercontent.com/lluis-ridao/enllano-datos/main/"
PAGINAS = {  # dónde se ve cada conjunto en la web
    "ransomware-espana": "/ciberataques-a-tiendas/",
    "caidas-internet": "/internet-y-luz-en-espana/",
    "demanda-electrica": "/internet-y-luz-en-espana/",
    "eurepoc-espana": "/ciberataques-espana/",
    "alternativas-libres": "/alternativas-libres-en-cifras/",
    "rastreadores-webs-publicas": "/rastreadores-webs-publicas/",
}


def manifiesto_mapas():
    d = RAIZ / "mapas"
    h = hashlib.sha256()
    for n in ("espana.json", "europa.json", "mundo.json"):
        f = d / n
        if not f.exists():
            return
        h.update(f.read_bytes())
    nuevo = {"version": h.hexdigest()[:12], "archivos": ["espana.json", "europa.json", "mundo.json", "mundo-base.svg"]}
    f = d / "manifest.json"
    viejo = json.loads(f.read_text("utf-8")) if f.exists() else {}
    if viejo.get("version") != nuevo["version"]:
        nuevo["actualizado"] = ahora_iso()
        f.write_text(json.dumps(nuevo, ensure_ascii=False, indent=1), "utf-8")
        print("Mapas: nueva versión", nuevo["version"])


def main():
    manifiesto_mapas()
    conjuntos = []
    for f in sorted(DATOS.glob("*.json")):
        if f.name == "catalogo.json":
            continue
        j = json.loads(f.read_text("utf-8"))
        n = f.stem
        conjuntos.append({
            "id": n,
            "titulo": j.get("titulo", n),
            "descripcion": j.get("descripcion", ""),
            "fuente": j.get("fuente", ""),
            "url_fuente": j.get("url_fuente", ""),
            "licencia": j.get("licencia", ""),
            "actualizado": j.get("generado", ""),
            "nota": j.get("nota", ""),
            "json": RAW + "datos/" + f.name,
            "csv": RAW + "datos/" + n + ".csv" if (DATOS / f"{n}.csv").exists() else "",
            "pagina": PAGINAS.get(n, ""),
        })
    viejo = DATOS / "catalogo.json"
    previo = json.loads(viejo.read_text("utf-8")).get("conjuntos") if viejo.exists() else None
    if previo == conjuntos:
        return
    viejo.write_text(json.dumps({"generado": ahora_iso(), "repositorio": "https://github.com/lluis-ridao/enllano-datos",
                                 "conjuntos": conjuntos}, ensure_ascii=False, indent=1), "utf-8")
    print(f"Catálogo: {len(conjuntos)} conjuntos")


if __name__ == "__main__":
    main()
