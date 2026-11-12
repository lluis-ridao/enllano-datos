"""Ciberataques contra España según el European Repository of Cyber Incidents (EuRepoC).

Base académica (Heidelberg, Innsbruck, SWP Berlín) con incidentes desde el año 2000, revisados por expertos.
Sin clave. Licencia: CC BY 4.0. Se descarga la última versión publicada en Zenodo.
"""
import csv
import io
import re

from comun import FuenteNoDisponible, ejecutar, guardar, pedir

# Registro de Zenodo de la última versión conocida (1.3). Si sale otra, basta cambiar este número.
ZENODO = "https://zenodo.org/api/records/14965395"
VACIOS = {"", "not available", "unknown", "n/a", "na", "none", "nan", "not attributed"}


def elegir_archivo(rec):
    csvs = [f for f in rec.get("files", []) if f.get("key", "").lower().endswith(".csv")]
    if not csvs:
        raise FuenteNoDisponible("Zenodo: el registro no tiene CSV")
    # El dataset principal (no el de atribución, receptores ni el diádico).
    malos = ("attribution", "dyadic", "receiver", "initiator", "codebook")
    buenos = [f for f in csvs if not any(m in f["key"].lower() for m in malos)]
    elegido = max(buenos or csvs, key=lambda f: f.get("size", 0))
    links = elegido.get("links", {})
    return elegido["key"], links.get("content") or links.get("self")


def col(cab, *candidatas):
    low = {c.lower().strip(): c for c in cab}
    for c in candidatas:
        if c in low:
            return low[c]
    for c in candidatas:
        for k, orig in low.items():
            if c in k:
                return orig
    return None


# «Korea, Democratic People's Republic of» → «Democratic People's Republic of Korea» (para no partirlo por la coma)
INVERTIR = re.compile(r"([A-Z][\w .-]*?), ((?:[\w'.-]+ )*?(?:Republic|Federation|State|Province|Kingdom)(?: [\w'.-]+)*? of)\b")


def limpio(v):
    if v is None:
        return []
    v = INVERTIR.sub(lambda m: f"{m.group(2)} {m.group(1)}", str(v))
    return [x.strip() for x in v.replace(";", ",").split(",") if x.strip().lower() not in VACIOS]


def fecha_iso(v):
    """EuRepoC usa dd.mm.aaaa; acepta también aaaa-mm-dd. Devuelve '' si no hay fecha."""
    v = (v or "").strip()
    m = re.match(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", v)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", v)
    return m.group(0) if m else ""


def main():
    rec = pedir(ZENODO)
    if not isinstance(rec, dict):
        raise FuenteNoDisponible("Zenodo no devolvió JSON")
    nombre, url = elegir_archivo(rec)
    crudo = pedir(url, binario=True, timeout=180)
    lector = csv.DictReader(io.StringIO(crudo.decode("utf-8-sig", "replace")))
    cab = lector.fieldnames or []
    c_id = col(cab, "incident_id", "id")
    c_nom = col(cab, "name", "incident_name")
    c_fecha = col(cab, "start_date", "date")
    c_rec = col(cab, "receiver_country")
    c_tipo = col(cab, "incident_type", "operation_type")
    c_ini = col(cab, "initiator_country")
    c_cat = col(cab, "receiver_category")
    if not (c_rec and c_fecha):
        raise FuenteNoDisponible(f"EuRepoC: columnas inesperadas en {nombre}: {cab[:15]}")

    incidentes = {}
    for f in lector:
        if "spain" not in (f.get(c_rec) or "").lower():
            continue
        clave = (f.get(c_id) if c_id else None) or f"{f.get(c_nom)}|{f.get(c_fecha)}"
        i = incidentes.setdefault(clave, {"nombre": (f.get(c_nom) or "").strip(), "fecha": fecha_iso(f.get(c_fecha)),
                                          "tipos": set(), "origen": set(), "sectores": set()})
        i["tipos"].update(limpio(f.get(c_tipo)) if c_tipo else [])
        i["origen"].update(limpio(f.get(c_ini)) if c_ini else [])
        i["sectores"].update(limpio(f.get(c_cat)) if c_cat else [])
    if not incidentes:
        raise FuenteNoDisponible("EuRepoC: ningún incidente con España como víctima (¿ha cambiado el formato?)")

    def contar(campo):
        c = {}
        for i in incidentes.values():
            for x in i[campo]:
                c[x] = c.get(x, 0) + 1
        return dict(sorted(c.items(), key=lambda kv: -kv[1]))

    por_anio = {}
    for i in incidentes.values():
        if i["fecha"][:4].isdigit():
            por_anio[i["fecha"][:4]] = por_anio.get(i["fecha"][:4], 0) + 1
    lista = sorted(
        ({"fecha": i["fecha"], "nombre": i["nombre"], "tipo": ", ".join(sorted(i["tipos"])),
          "origen": ", ".join(sorted(i["origen"])) or "Sin atribuir", "sector": ", ".join(sorted(i["sectores"]))}
         for i in incidentes.values()),
        key=lambda x: x["fecha"] or "0000", reverse=True)

    guardar(
        "eurepoc-espana",
        {
            "total": len(incidentes),
            "por_anio": dict(sorted(por_anio.items())),
            "por_tipo": contar("tipos"),
            "por_origen": contar("origen"),
            "por_sector": contar("sectores"),
            "incidentes": lista,
            "version": rec.get("metadata", {}).get("version", ""),
            "archivo": nombre,
        },
        titulo="Ciberataques contra España (EuRepoC)",
        descripcion="Incidentes con alguna víctima en España recogidos y codificados por expertos desde el año 2000.",
        fuente="European Repository of Cyber Incidents (EuRepoC)",
        url_fuente="https://eurepoc.eu",
        licencia="CC BY 4.0 (EuRepoC)",
        filas_csv=lista,
        campos_csv=["fecha", "nombre", "tipo", "origen", "sector"],
        nota="La atribución («origen») es la que recoge EuRepoC de fuentes públicas; muchos incidentes no tienen autor conocido.",
    )


if __name__ == "__main__":
    ejecutar(main)
