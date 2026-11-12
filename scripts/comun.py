"""Utilidades compartidas por los scripts de enllano-datos.

Solo biblioteca estándar. Cada script escribe dos archivos en datos/:
un JSON (para la web) y, si tiene sentido, un CSV (para descargar).

Regla de oro: si una fuente falla, NO se sobrescribe el último dato bueno.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
CONFIG = RAIZ / "config"
UA = "enllano-datos/1.0 (+https://enllano.com/datos/)"


class FuenteNoDisponible(Exception):
    """La fuente no respondió o no hay clave: se conserva el dato anterior."""


def ahora_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def pedir(url: str, params: dict | None = None, cabeceras: dict | None = None,
          intentos: int = 3, timeout: int = 60, binario: bool = False):
    """GET con reintentos. Devuelve JSON (dict/list), texto o bytes."""
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    h = {"User-Agent": UA, "Accept": "application/json, */*"}
    h.update(cabeceras or {})
    ultimo = None
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                cuerpo = r.read()
            if binario:
                return cuerpo
            texto = cuerpo.decode("utf-8", "replace")
            try:
                return json.loads(texto)
            except json.JSONDecodeError:
                return texto
        except urllib.error.HTTPError as e:
            try:
                detalle = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                detalle = ""
            ultimo = f"{e} {detalle}".strip()
            if e.code in (400, 401, 403, 404):
                break  # no tiene sentido reintentar
            time.sleep(2 ** i * 3)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            ultimo = e
            time.sleep(2 ** i * 3)
    raise FuenteNoDisponible(f"{url.split('?')[0]}: {ultimo}")


def secreto(nombre: str) -> str:
    v = os.environ.get(nombre, "").strip()
    if not v:
        raise FuenteNoDisponible(f"Falta el secreto {nombre} (Settings > Secrets and variables > Actions)")
    return v


def leer_previo(nombre: str) -> dict | None:
    f = DATOS / f"{nombre}.json"
    if f.exists():
        try:
            return json.loads(f.read_text("utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def guardar(nombre: str, datos, *, titulo: str, descripcion: str, fuente: str, url_fuente: str,
            licencia: str, filas_csv: list[dict] | None = None, campos_csv: list[str] | None = None,
            nota: str = "") -> None:
    """Escribe datos/{nombre}.json (y .csv) de forma atómica."""
    DATOS.mkdir(exist_ok=True)
    doc = {
        "titulo": titulo,
        "descripcion": descripcion,
        "fuente": fuente,
        "url_fuente": url_fuente,
        "licencia": licencia,
        "generado": ahora_iso(),
        "nota": nota,
        "datos": datos,
    }
    tmp = DATOS / f".{nombre}.json.tmp"
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(DATOS / f"{nombre}.json")
    if filas_csv is not None:
        campos = campos_csv or (list(filas_csv[0].keys()) if filas_csv else [])
        tmp = DATOS / f".{nombre}.csv.tmp"
        with tmp.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
            w.writeheader()
            w.writerows(filas_csv)
        tmp.replace(DATOS / f"{nombre}.csv")
    print(f"OK {nombre}: guardado")


def ejecutar(fn) -> None:
    """Lanza el script; si la fuente falla, avisa y deja el dato anterior intacto."""
    try:
        fn()
    except FuenteNoDisponible as e:
        print(f"AVISO: {e}. Se conserva el último dato bueno.", file=sys.stderr)
        sys.exit(0 if os.environ.get("ENLLANO_TOLERANTE", "1") == "1" else 1)
