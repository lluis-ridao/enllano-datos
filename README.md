# enllano-datos

Datos abiertos de [enllano.com](https://enllano.com/datos/) que se actualizan solos cada día con GitHub Actions.
Cada cifra lleva su fuente. Puedes descargarlo todo en JSON o CSV y reutilizarlo citando a enllano.com.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24165630.svg)](https://doi.org/10.5281/zenodo.24165630)

Una selección (alternativas libres, demanda eléctrica y rastreadores en webs públicas) también está publicada en [Zenodo](https://doi.org/10.5281/zenodo.24165630), [Kaggle](https://www.kaggle.com/datasets/llusridao/spain-free-software-electricity-demand-trackers) y [Hugging Face](https://huggingface.co/datasets/lluisridao/enllano-datos) con licencia CC BY-NC-SA 4.0.

## Qué hay

| Archivo | Qué es | Fuente | Se actualiza |
|---|---|---|---|
| `datos/ransomware-espana` | Reivindicaciones de ransomware contra organizaciones de España, por mes y sector (24 meses). Solo recuentos, nunca nombres. | [Ransomware.live](https://www.ransomware.live) | Cada día |
| `datos/caidas-internet` | Caídas de internet en España y nº de caídas por país europeo (52 semanas). | [Cloudflare Radar](https://radar.cloudflare.com/outage-center) | Cada día |
| `datos/demanda-electrica` | Demanda eléctrica diaria y mensual del último año y % renovable de los últimos 30 días. | [Red Eléctrica](https://www.ree.es/es/datos/apidatos) | Cada día |
| `datos/alternativas-libres` | Programas libres frente a los de pago: estrellas en GitHub y descargas en Flathub (total, mes y España). | GitHub y [Flathub](https://flathub.org/statistics) | Cada día |
| `datos/eurepoc-espana` | Ciberataques con víctimas en España desde el año 2000, por año, tipo, sector y autoría. | [EuRepoC](https://eurepoc.eu) | Cada lunes |
| `datos/rastreadores-webs-publicas` | Rastreadores que cargan las portadas de webs públicas españolas **antes** de aceptar cookies. | Análisis propio + lista de [Disconnect](https://github.com/disconnectme/disconnect-tracking-protection) | Cada lunes |
| `datos/catalogo.json` | Índice de todo lo anterior (lo usa la página /datos/ de la web). | — | Con cada cambio |
| `mapas/` | Mapas de ciberataques confirmados de España, Europa y el mundo. La web los descarga cada día. | Medios y fuentes oficiales | A mano |

## Licencias

- **Código** (`scripts/`): MIT.
- **Datos propios** (rastreadores, alternativas libres, recopilaciones y recuentos): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.es). Cita: «enllano.com (Lluís Ridao), enllano-datos».
- **Datos de terceros**: mantienen su licencia, indicada en el campo `licencia` de cada JSON (EuRepoC: CC BY 4.0; Cloudflare Radar: CC BY-NC 4.0; Red Eléctrica: reutilización citando la fuente; Ransomware.live: uso no comercial con atribución).

## Puesta en marcha (una sola vez)

1. **Settings → Secrets and variables → Actions → New repository secret** y añade:
   - `RWL_API_KEY`: clave gratuita de [my.ransomware.live](https://my.ransomware.live) (la misma que pusiste en WordPress).
   - `CLOUDFLARE_API_TOKEN`: en [dash.cloudflare.com](https://dash.cloudflare.com/profile/api-tokens) → *Create Token* → *Custom token* → permiso **Account · Radar · Read**. Es gratis.
2. **Actions → Datos diarios → Run workflow** para la primera carga (y lo mismo con **Datos semanales**).
3. Opcional, para que te citen como un trabajo académico: conecta el repositorio en [zenodo.org/account/settings/github](https://zenodo.org/account/settings/github) y publica una *release*. Zenodo le dará un DOI a cada versión.

Sin secretos funcionan igual Red Eléctrica, EuRepoC, alternativas libres y rastreadores.

## Cómo funciona

- Cada script está en `scripts/` y solo usa la biblioteca estándar de Python (salvo los rastreadores, que usan Playwright).
- Si una fuente falla, **no se toca** el último dato bueno: la web nunca se queda vacía.
- Las listas editables están en `config/`: añade una web pública a `webs-publicas.json` o un programa a `alternativas.json` y saldrá en la siguiente actualización.

## Probar en tu ordenador

```bash
pip install -r requirements.txt && python -m playwright install chromium
python scripts/electricidad_ree.py
python scripts/rastreadores.py
python scripts/catalogo.py
```
