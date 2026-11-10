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


def _grafico_comparacion(mes_actual_nombre, resumen_referencia, resumen_actual):
    """SVG de barras agrupadas: mediana de cada demora, enero vs. el mes
    publicado. Los valores pueden ser negativos (el vuelo llego/salio antes
    de lo previsto), asi que las barras parten de una linea base en cero.
    """
    grupos = [
        ("Demora de salida", resumen_referencia["mediana_salida"], resumen_actual["mediana_salida"]),
        ("Demora de llegada", resumen_referencia["mediana_llegada"], resumen_actual["mediana_llegada"]),
    ]

    ancho, alto_plot, alto_etiquetas = 460, 130, 34
    alto_total = alto_plot + alto_etiquetas
    margen = 20
    y_cero = alto_plot / 2
    max_abs = max(3.0, max(abs(v) for _, ref, act in grupos for v in (ref, act)) * 1.35)
    escala = (alto_plot / 2 - 20) / max_abs

    ancho_barra, separacion = 32, 10
    ancho_grupo = (ancho - 2 * margen) / len(grupos)

    piezas = [f'<line x1="{margen}" y1="{y_cero:.1f}" x2="{ancho - margen}" y2="{y_cero:.1f}" class="linea-base" />']

    for i, (nombre, v_ref, v_act) in enumerate(grupos):
        centro = margen + ancho_grupo * i + ancho_grupo / 2
        for x_offset, valor, serie in (
            (-separacion / 2 - ancho_barra, v_ref, "serie-1"),
            (separacion / 2, v_act, "serie-2"),
        ):
            x = centro + x_offset
            alto_barra = max(abs(valor) * escala, 1)
            y = y_cero - alto_barra if valor >= 0 else y_cero
            y_etiqueta = (y - 6) if valor >= 0 else (y + alto_barra + 14)
            piezas.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{ancho_barra}" height="{alto_barra:.1f}" '
                f'rx="4" class="barra {serie}"><title>{html.escape(nombre)}: {valor:.0f} min</title></rect>'
            )
            piezas.append(
                f'<text x="{x + ancho_barra / 2:.1f}" y="{y_etiqueta:.1f}" '
                f'text-anchor="middle" class="valor-barra">{valor:.0f}</text>'
            )
        piezas.append(
            f'<text x="{centro:.1f}" y="{alto_plot + 20}" text-anchor="middle" '
            f'class="etiqueta-grupo">{html.escape(nombre)}</text>'
        )

    svg_interior = "\n    ".join(piezas)
    return f"""<svg viewBox="0 0 {ancho} {alto_total}" role="img"
    aria-label="Comparacion de medianas de demora entre enero y {html.escape(mes_actual_nombre)}">
    {svg_interior}
  </svg>"""


def generar_portada(
    anio_actual,
    mes_actual,
    resumen_referencia,
    resumen_actual,
    nombre_informe,
    commit,
    fecha_generacion,
):
    mes_nombre = _slug_mes(mes_actual).capitalize()
    titulo_mes = f"{mes_nombre} {anio_actual}"
    grafico = _grafico_comparacion(_slug_mes(mes_actual), resumen_referencia, resumen_actual)

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
  --series-2: #eb6834; --series-3: #1baf7a;
  --tint-1: rgba(42,120,214,0.08); --tint-3: rgba(27,175,122,0.08);
  --grid: #e1e0d9; --baseline: #c3c2b7;
  --header-start: #184f95; --header-end: #256abf; --header-ink: #ffffff;
  --header-ink-muted: rgba(255,255,255,0.82);
  --shadow: 0 1px 2px rgba(11,11,11,0.06), 0 8px 24px rgba(11,11,11,0.05);
}}
:root:where(:not([data-theme="light"])) {{
  @media (prefers-color-scheme: dark) {{
    --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #d7d5cf;
    --ink-muted: #9a988f; --border: rgba(255,255,255,0.10); --series-1: #3987e5;
    --series-2: #d95926; --series-3: #199e70;
    --tint-1: rgba(57,135,229,0.14); --tint-3: rgba(25,158,112,0.14);
    --grid: #2c2c2a; --baseline: #383835;
    --header-start: #0d366b; --header-end: #256abf; --header-ink: #ffffff;
    --header-ink-muted: rgba(255,255,255,0.80);
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
  overflow: hidden;
}}
.banda-header {{
  position: relative; overflow: hidden;
  background: linear-gradient(135deg, var(--header-start), var(--header-end));
  color: var(--header-ink);
  padding: 30px clamp(20px, 5vw, 48px) 26px;
}}
.banda-header::before {{
  content: ""; position: absolute; inset: 0;
  background:
    radial-gradient(520px 220px at 88% -20%, rgba(255,255,255,0.20), transparent 60%),
    radial-gradient(360px 200px at 102% 115%, rgba(255,255,255,0.12), transparent 65%);
  pointer-events: none;
}}
.banda-header > * {{ position: relative; }}
.banda-header h1 {{ font-size: 1.6rem; margin: 0 0 6px; letter-spacing: -0.01em; }}
.banda-header .subtitulo {{ color: var(--header-ink-muted); margin: 0; font-size: 0.95rem; }}
.banda-header .subtitulo strong {{ color: var(--header-ink); }}
.contenido {{ padding: 28px clamp(20px, 5vw, 48px) 32px; }}
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
  display: inline-block; margin-top: 20px; padding: 11px 20px; border-radius: 10px;
  background: linear-gradient(135deg, var(--header-start), var(--header-end));
  color: white; text-decoration: none; font-weight: 600;
  box-shadow: 0 4px 14px rgba(37,106,191,0.35);
}}
.chip {{
  display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px;
  border-radius: 999px; font-size: 0.82rem; font-weight: 600;
}}
.chip .punto {{ width: 8px; height: 8px; border-radius: 50%; }}
.chip.ok {{ background: var(--tint-3); color: var(--series-3); }}
.chip.ok .punto {{ background: var(--series-3); }}
.grafico-seccion {{ margin: 28px 0 8px; }}
.grafico-seccion h2 {{ font-size: 1rem; margin: 0 0 10px; color: var(--ink-2); }}
.grafico-seccion svg {{ width: 100%; height: auto; max-width: 460px; display: block; }}
.linea-base {{ stroke: var(--baseline); stroke-width: 1; }}
.barra.serie-1 {{ fill: var(--series-1); }}
.barra.serie-2 {{ fill: var(--series-2); }}
.valor-barra {{ font-size: 11px; fill: var(--ink-2); font-variant-numeric: tabular-nums; }}
.etiqueta-grupo {{ font-size: 11px; fill: var(--ink-muted); }}
.leyenda {{ display: flex; gap: 18px; margin-top: 6px; font-size: 0.82rem; color: var(--ink-2); }}
.leyenda-item {{ display: inline-flex; align-items: center; gap: 6px; }}
.leyenda-item .punto {{ width: 10px; height: 10px; border-radius: 3px; }}
</style>
</head>
<body>
<main>
  <div class="banda-header">
    <h1>Monitoreo de demoras de vuelos &mdash; NYC 2013</h1>
    <p class="subtitulo">Ultimo lote publicado: <strong>{html.escape(titulo_mes)}</strong></p>
  </div>

  <div class="contenido">
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

    <div class="grafico-seccion">
      <h2>Mediana de demora: enero vs. {html.escape(mes_nombre)}</h2>
      {grafico}
      <div class="leyenda">
        <span class="leyenda-item"><span class="punto" style="background: var(--series-1)"></span>Enero (referencia)</span>
        <span class="leyenda-item"><span class="punto" style="background: var(--series-2)"></span>{html.escape(mes_nombre)} (publicado)</span>
      </div>
    </div>

    <a class="boton" href="{html.escape(nombre_informe)}">Ver informe de Evidently (enero vs. {_slug_mes(mes_actual)})</a>

    <p class="meta">
      autor <strong>{html.escape(AUTOR)}</strong> &middot;
      fuente {html.escape(FUENTE)} &middot;
      generado el {fecha_generacion} &middot;
      commit <code>{html.escape(commit)}</code>
    </p>
  </div>
</main>
</body>
</html>
"""


def main():
    os.makedirs(CARPETA_SITIO, exist_ok=True)

    anio_actual, mes_actual = _mes_de(RUTA_ACTUAL)
    resumen_referencia = resumen_lote(RUTA_REFERENCIA)
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
        resumen_referencia=resumen_referencia,
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
