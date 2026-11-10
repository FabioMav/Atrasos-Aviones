# Propuesta (sección 2 de la consigna)

> Este texto está pensado para pegarse, casi tal cual, en la sección
> "Planifica el trabajo y redacta la propuesta" del PDF final. Ajustalo con
> tus propias palabras si querés, pero el contenido ya responde todo lo que
> pide la consigna.

## Quién consultaría el sitio y qué decisión apoya

El equipo de operaciones de los aeropuertos de Nueva York (JFK, LGA, EWR)
consultaría el sitio publicado cada vez que se incorpora un mes nuevo de
vuelos. La portada les dice de un vistazo si el patrón de demoras de salida
y de llegada cambió respecto a enero (el mes de referencia). Si el informe
de Evidently marca un cambio importante (drift), el equipo sabe que vale la
pena investigar más a fondo —por ejemplo, revisar en qué aeropuertos o
rutas se concentra el aumento de demoras— antes de tomar decisiones
operativas (refuerzos de personal, ajustes de horarios, comunicación a
pasajeros). Si no hay drift, no hace falta ninguna acción adicional: el
patrón de demoras se mantiene estable.

## Tareas priorizadas

1. Preparar los lotes de datos (referencia, control, nuevo) a partir del
   CSV original, verificando que cada uno tenga 12.000 filas y los ocho
   encabezados correctos.
2. Implementar el validador y sus pruebas automatizadas, para que ningún
   dato corrupto llegue a publicarse.
3. Implementar la comparación con Evidently y la generación de la portada
   del sitio.
4. Armar el workflow de GitHub Actions (CI que valida y genera el sitio, CD
   que lo publica solo si CI pasó).
5. Demostrar los cuatro escenarios (primera publicación, actualización
   válida, error controlado, recuperación) con commits y capturas reales.
6. Documentar todo en el PDF final.

## Criterios de aceptación

- `referencia.csv` y `actual.csv` pasan el validador si y solo si cumplen
  todas las reglas (encabezados, tipos, rangos, unicidad de `vuelo_id`,
  coherencia entre `fecha` y `lote`, lote permitido en cada archivo).
- Un commit con datos inválidos hace fallar el job `ci` y evita que `cd`
  se ejecute; GitHub Pages sigue mostrando la última versión que sí pasó.
- Un commit con datos válidos hace que `ci` y `cd` terminen en verde y que
  la portada se actualice con el mes y el commit correctos.
- La portada siempre muestra el mes publicado, el número de vuelos
  analizados, la mediana de cada demora, la fecha de generación, el commit,
  el autor, la fuente y un enlace al informe de Evidently que identifica
  los dos meses comparados.

## Diagrama: del push a la publicación

```
git push a main
      │
      ▼
┌─────────────┐   falla   ┌────────────────────────────┐
│   job: ci   │ ────────▶ │ cd NO se ejecuta.          │
│ (valida +   │           │ GitHub Pages conserva el   │
│  prueba +   │           │ ultimo sitio valido.       │
│  genera)    │           └────────────────────────────┘
└──────┬──────┘
       │ pasa
       ▼
┌─────────────┐
│   job: cd   │  publica el artefacto de ESTA ejecucion
│ (needs: ci) │  en GitHub Pages
└─────────────┘
```

## Errores que bloquean la publicación vs. cambios que ameritan revisión

Son dos cosas distintas y el sistema las trata distinto:

- **Errores que bloquean la publicación**: problemas estructurales de los
  datos que detecta `validador.py` (un encabezado faltante, un `vuelo_id`
  duplicado, una fecha que no corresponde al mes del lote, una distancia en
  cero o negativa, etc.). Estos **sí** impiden que el sitio se actualice:
  el job `ci` falla, `cd` queda omitido y Pages conserva la última versión
  válida.
- **Cambios de distribución que ameritan revisión**: el dato es
  estructuralmente correcto, pero Evidently detecta que las demoras de un
  mes se distribuyen distinto a las de enero (drift). Esto **no** bloquea
  nada — el sitio se publica igual — pero es una señal para que el equipo
  de operaciones revise manualmente qué puede estar causando el cambio.

## Qué variables revisaría, cuándo y quién actuaría

Las variables monitoreadas son `demora_salida_min` y `demora_llegada_min`.
Se revisan en cada publicación (cada vez que se incorpora un mes nuevo como
`actual.csv`). El equipo de operaciones (o quien haga de analista de datos
del equipo) actuaría cuando el informe de Evidently marque drift en al
menos una de las dos columnas (en esta configuración, con `drift_share`
0.5 y solo dos columnas, alcanza con que una sola tenga drift para que el
dataset completo se marque como "con drift").

## Cómo identificar el último commit válido y verificar una recuperación

El commit válido más reciente es el que aparece en la portada publicada en
GitHub Pages (`index.html` muestra el hash del commit que generó esa
versión) — también se puede confirmar mirando, en la pestaña Actions, cuál
fue la última ejecución donde tanto `ci` como `cd` terminaron en verde.

Para verificar una recuperación: después de corregir el dato que causó el
error y volver a hacer push, hay que comprobar que (a) el nuevo workflow
run tiene `ci` y `cd` en verde, (b) la portada publicada ahora muestra ese
commit nuevo (no el anterior, fallido, ni el válido-pero-viejo de antes del
error) y (c) el contenido del sitio vuelve a corresponder al mes que se
esperaba publicar.
