"""Genera el sitio publicado en GitHub Pages: la portada (index.html) y el
informe de Evidently que compara las demoras del lote actual con enero.

Se ejecuta despues de que validador.py confirmo que referencia.csv y
actual.csv son validos. Si actual.csv trae el lote "control" (febrero) o
"nuevo" (julio), el nombre del informe generado identifica ambos meses
("informe_enero_vs_febrero.html" / "informe_enero_vs_julio.html"), tal
como pide la consigna, para que la portada enlace al informe correcto.
"""
import html
import os
from datetime import datetime, timezone

import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset

RUTA_REFERENCIA = "datos/referencia.csv"
RUTA_ACTUAL = "datos/actual.csv"
CARPETA_SITIO = "public"

COLUMNAS_DEMORA = ["demora_salida_min", "demora_llegada_min"]

MESES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre",
    12: "diciembre",
}

AUTOR = "Fabio Mavric"
FUENTE = "nycflights13 (vuelos que salieron de JFK, LGA o EWR en 2013)"


def _mes_de(ruta_csv):
    fecha = pd.read_csv(ruta_csv, usecols=["fecha"])["fecha"].iloc[0]
    anio, mes, _ = (int(p) for p in fecha.split("-"))
    return anio, mes


def _slug_mes(mes):
    return MESES[mes]


def resumen_lote(ruta_csv):
    df = pd.read_csv(ruta_csv)
    return {
        "n": len(df),
        "mediana_salida": df["demora_salida_min"].median(),
        "mediana_llegada": df["demora_llegada_min"].median(),
    }


def calcular_drift(ruta_referencia, ruta_actual):
    ref = pd.read_csv(ruta_referencia, usecols=COLUMNAS_DEMORA)
    act = pd.read_csv(ruta_actual, usecols=COLUMNAS_DEMORA)
    reporte = Report(
        metrics=[DataDriftPreset(columns=COLUMNAS_DEMORA, drift_share=0.5, num_threshold=0.05)]
    )
    snapshot = reporte.run(current_data=act, reference_data=ref)
    return snapshot


def generar_portada(
    anio_actual,
    mes_actual,
    resumen_actual,
    nombre_informe,
    commit,
    fecha_generacion,
):
    mes_nombre = _slug_mes(mes_actual).capitalize()
    titulo_mes = f"{mes_nombre} {anio_actual}"

    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Monitoreo de demoras de vuelos NYC</title>
<style>
:root {{
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #33322f;
  --ink-muted: #6b6b66; --border: rgba(11,11,11,0.10); --series-1: #2a78d6;
  --series-3: #1baf7a; --tint-1: rgba(42,120,214,0.08); --tint-3: rgba(27,175,122,0.08);
  --shadow: 0 1px 2px rgba(11,11,11,0.06), 0 8px 24px rgba(11,11,11,0.05);
}}
:root:where(:not([data-theme="light"])) {{
  @media (prefers-color-scheme: dark) {{
    --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #d7d5cf;
    --ink-muted: #9a988f; --border: rgba(255,255,255,0.10); --series-1: #3987e5;
    --series-3: #199e70; --tint-1: rgba(57,135,229,0.14); --tint-3: rgba(25,158,112,0.14);
    --shadow: 0 1px 2px rgba(0,0,0,0.3), 0 8px 24px rgba(0,0,0,0.3);
  }}
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--page); color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  padding: 32px 16px;
}}
main {{
  max-width: 880px; margin: 0 auto; background: var(--surface);
  border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--shadow);
  padding: 32px clamp(20px, 5vw, 48px);
}}
h1 {{ font-size: 1.6rem; margin: 0 0 4px; }}
.subtitulo {{ color: var(--ink-muted); margin: 0 0 24px; }}
.indicadores {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px; margin: 24px 0;
}}
.indicador {{
  background: var(--tint-1); border-radius: 12px; padding: 14px 16px;
}}
.indicador .valor {{ font-size: 1.4rem; font-weight: 700; font-variant-numeric: tabular-nums; }}
.indicador .etiqueta {{ font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--ink-muted); }}
.meta {{ color: var(--ink-muted); font-size: 0.9rem; line-height: 1.7; margin-top: 24px; }}
.meta code {{ background: var(--tint-1); padding: 1px 6px; border-radius: 4px; }}
a.boton {{
  display: inline-block; margin-top: 20px; padding: 10px 18px; border-radius: 10px;
  background: var(--series-1); color: white; text-decoration: none; font-weight: 600;
}}
.chip {{
  display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px;
  border-radius: 999px; font-size: 0.82rem; font-weight: 600;
}}
.chip .punto {{ width: 8px; height: 8px; border-radius: 50%; }}
.chip.ok {{ background: var(--tint-3); color: var(--series-3); }}
.chip.ok .punto {{ background: var(--series-3); }}
</style>
</head>
<body>
<main>
  <h1>Monitoreo de demoras de vuelos &mdash; NYC 2013</h1>
  <p class="subtitulo">Ultimo lote publicado: <strong>{html.escape(titulo_mes)}</strong></p>

  <div class="indicadores">
    <div class="indicador">
      <div class="valor">{resumen_actual['n']:,}</div>
      <div class="etiqueta">Vuelos analizados</div>
    </div>
    <div class="indicador">
      <div class="valor">{resumen_actual['mediana_salida']:.0f} min</div>
      <div class="etiqueta">Mediana demora salida</div>
    </div>
    <div class="indicador">
      <div class="valor">{resumen_actual['mediana_llegada']:.0f} min</div>
      <div class="etiqueta">Mediana demora llegada</div>
    </div>
  </div>

  <a class="boton" href="{html.escape(nombre_informe)}">Ver informe de Evidently (enero vs. {_slug_mes(mes_actual)})</a>

  <p class="meta">
    autor <strong>{html.escape(AUTOR)}</strong> &middot;
    fuente {html.escape(FUENTE)} &middot;
    generado el {fecha_generacion} &middot;
    commit <code>{html.escape(commit)}</code>
  </p>
</main>
</body>
</html>
"""


def main():
    os.makedirs(CARPETA_SITIO, exist_ok=True)

    anio_actual, mes_actual = _mes_de(RUTA_ACTUAL)
    resumen_actual = resumen_lote(RUTA_ACTUAL)

    nombre_informe = f"informe_enero_vs_{_slug_mes(mes_actual)}.html"
    ruta_informe = os.path.join(CARPETA_SITIO, nombre_informe)

    snapshot = calcular_drift(RUTA_REFERENCIA, RUTA_ACTUAL)
    snapshot.save_html(ruta_informe)

    commit = os.environ.get("GITHUB_SHA", "local")[:7] if os.environ.get("GITHUB_SHA") else "local"
    fecha_generacion = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    portada = generar_portada(
        anio_actual=anio_actual,
        mes_actual=mes_actual,
        resumen_actual=resumen_actual,
        nombre_informe=nombre_informe,
        commit=commit,
        fecha_generacion=fecha_generacion,
    )
    with open(os.path.join(CARPETA_SITIO, "index.html"), "w", encoding="utf-8") as f:
        f.write(portada)

    print(f"OK: {CARPETA_SITIO}/index.html generado (lote: {_slug_mes(mes_actual)} {anio_actual}).")
    print(f"OK: {ruta_informe} generado (comparacion enero vs. {_slug_mes(mes_actual)}).")


if __name__ == "__main__":
    main()
