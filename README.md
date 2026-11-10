# Monitoreo de demoras de vuelos NYC 2013 — CI/CD + Evidently

Práctica 5 (Unidad de Aprendizaje 5): un sistema que valida lotes de vuelos,
compara las demoras de salida y de llegada con **Evidently** contra un mes de
referencia (enero de 2013) y publica el informe del último lote válido en
**GitHub Pages**, automatizado con **GitHub Actions**.

## El caso

Un equipo de operaciones quiere saber si cambió el patrón de demoras entre
meses. Con cada lote válido, el sitio se actualiza y permite consultar la
comparación con enero. Si Evidently detecta un cambio (drift), el equipo
puede investigar en qué aeropuertos o rutas se concentra.

## Fuente y preparación de los lotes

El CSV `datos/vuelos_nyc_2013.csv` contiene 36.000 vuelos reales de 2013
(fuente: `nycflights13`) que salieron de JFK, LGA o EWR, con 12.000 registros
de cada uno de tres meses mediante muestreo reproducible. Cada fila ya trae
una columna `lote` que indica a qué grupo pertenece:

| Lote | Mes | Archivo | Uso |
|---|---|---|---|
| `referencia` | Enero 2013 | `datos/referencia.csv` | Se mantiene fijo, es la base de comparación |
| `control` | Febrero 2013 | `datos/control.csv` | Primera publicación (`actual.csv` = copia de este) |
| `nuevo` | Julio 2013 | `datos/nuevo.csv` | Actualización válida (`actual.csv` = copia de este) |

`preparar_datos.py` hace esta división una sola vez (ya está corrida; los
cuatro CSV de `datos/` ya existen en este entrega). Si alguna vez necesitás
rehacerla desde cero:

```bash
python preparar_datos.py
```

Esto filtra `vuelos_nyc_2013.csv` por la columna `lote`, exporta cada grupo
con sus ocho encabezados (`vuelo_id, fecha, origen, destino,
demora_salida_min, demora_llegada_min, distancia_millas, lote`) y deja
`datos/actual.csv` como copia de `control.csv` (febrero), listo para la
primera publicación.

## Reglas de validación (`validador.py`)

Se valida **completo** `datos/referencia.csv` y `datos/actual.csv` (no una
muestra). Un archivo es inválido si:

- Le faltan encabezados obligatorios, o no tiene ninguna fila de datos.
- `vuelo_id` no es un entero positivo, o está repetido dentro del archivo.
- `fecha` no tiene formato `AAAA-MM-DD`, no es una fecha calendario válida, o
  no corresponde al mes/año que le toca a su lote (enero para `referencia`,
  febrero para `control`, julio para `nuevo`).
- `origen` no es `JFK`, `LGA` ni `EWR`.
- `destino` no son tres letras mayúsculas.
- `demora_salida_min` o `demora_llegada_min` no son enteros (cero y
  negativos **sí** son válidos: un vuelo puede salir o llegar antes de lo
  previsto).
- `distancia_millas` no es un entero positivo.
- `referencia.csv` trae un lote distinto de `referencia`.
- `actual.csv` mezcla `control` y `nuevo` en el mismo archivo, o trae un
  valor de lote que no es ninguno de los dos.

Ante cualquier error se identifica el archivo, la fila y el campo, se juntan
**todos** los errores encontrados (no se corta en el primero) y el programa
termina con código de salida distinto de cero — así, en CI, el job falla y
la publicación queda bloqueada.

```bash
python validador.py
```

### Pruebas automatizadas (`test_validador.py`)

Diez pruebas con datos chicos e independientes (no dependen de los CSV
reales), más una que corre la validación contra los CSV del proyecto:

- registro válido (pasa)
- demora negativa válida (pasa)
- encabezado faltante (falla)
- fecha inválida / no corresponde al mes del lote (falla)
- identificador duplicado (falla)
- distancia inválida — cero no es positivo (falla)
- origen inválido (falla)
- mezcla de lotes en `actual.csv` (falla)
- archivo sin filas de datos (falla)
- validación contra `datos/referencia.csv` y `datos/actual.csv` reales (pasa)

```bash
python -m unittest discover -v
```

## El informe de Evidently (`generar_informe.py`)

Compara `demora_salida_min` y `demora_llegada_min` de `actual.csv` contra
`referencia.csv` (enero), con la **misma configuración** en ambas
comparaciones: `DataDriftPreset(columns=[...], drift_share=0.5,
num_threshold=0.05)`. Evidently eligió automáticamente la distancia de
Wasserstein normalizada como método para estas dos columnas numéricas: una
columna se marca con drift cuando esa distancia supera 0.05, y el dataset
completo se marca con drift cuando la proporción de columnas con drift
alcanza 0.5 (es decir, con solo 2 columnas, basta con que 1 de las 2 tenga
drift).

Resultados reales obtenidos en esta entrega (podés volver a generarlos
corriendo `generar_informe.py` con cada `actual.csv`):

| Comparación | Mediana demora salida (ref. / actual) | Mediana demora llegada (ref. / actual) | Distancia Wasserstein (salida / llegada) | ¿Drift? |
|---|---|---|---|---|
| Enero vs. Febrero | −2 / −2 min | −3 / −3 min | 0.032 / 0.029 | No (0 de 2 columnas, share 0.0) |
| Enero vs. Julio | −2 / 0 min | −3 / −2 min | 0.326 / 0.295 | Sí (2 de 2 columnas, share 1.0) |

Esto tiene sentido: febrero se parece a enero (ambos son meses de invierno
boreal, con clima parecido en los tres aeropuertos), mientras que julio —
temporada alta de vuelos y tormentas de verano en el noreste de EE.UU. —
muestra demoras bastante mayores en ambas métricas.

```bash
python generar_informe.py
```

Genera `public/index.html` (la portada) y
`public/informe_enero_vs_<mes>.html` (el informe completo de Evidently),
donde `<mes>` es `febrero` o `julio` según el lote que tenga `actual.csv` en
ese momento. La portada muestra el último mes publicado, el número de
vuelos analizados, la mediana de cada demora, la fecha de generación, el
commit (toma `GITHUB_SHA` cuando corre en Actions, o `local` si lo corrés
en tu máquina), el autor, la fuente de los datos y un botón que enlaza al
informe correcto.

## Estructura del repositorio

```
vuelos-cicd/
├── datos/
│   ├── vuelos_nyc_2013.csv   (CSV original, no tocar)
│   ├── referencia.csv         (enero — fijo)
│   ├── control.csv             (febrero)
│   ├── nuevo.csv                (julio)
│   └── actual.csv              (el lote publicado ahora mismo: copia de control.csv o nuevo.csv)
├── preparar_datos.py
├── validador.py
├── test_validador.py
├── generar_informe.py
├── requirements.txt
├── .gitignore
├── githooks/post-commit
├── .github/workflows/vuelos-cicd.yml
└── README.md
```

## Instalación y ejecución local

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows (PowerShell: .venv\Scripts\Activate.ps1)
# source .venv/bin/activate    # macOS / Linux

pip install -r requirements.txt

python -m unittest discover -v   # pruebas
python validador.py                # validación
python generar_informe.py          # portada + informe (queda en public/)
```

Abrí `public/index.html` en el navegador para ver la portada publicada.

## Git hook opcional (push automático tras cada commit)

```bash
git config core.hooksPath githooks
```

Con esto, cada `git commit` intenta un `git push` inmediatamente después.
Si el push falla (sin conexión, sin permisos), el commit ya quedó guardado
igual — el hook solo avisa, nunca bloquea el commit.

## CI/CD (`.github/workflows/vuelos-cicd.yml`)

- **`ci`**: en cada push a `main`, instala dependencias, corre las pruebas,
  valida `referencia.csv` y `actual.csv`, y si todo pasa genera
  `public/index.html` y el informe de Evidently, subiendo esa carpeta como
  artefacto de GitHub Pages.
- **`cd`** (`needs: ci`): publica ese artefacto en GitHub Pages. Si `ci`
  falla (por ejemplo, un dato inválido), `cd` **no se ejecuta** y GitHub
  Pages conserva automáticamente el sitio del último commit que sí pasó.

## Pasos para crear el repositorio y publicarlo

1. Creá un repositorio público nuevo en GitHub (por ejemplo `vuelos-cicd`).
2. En esta carpeta:
   ```bash
   git init
   git add .
   git commit -m "Primera version: monitoreo de demoras de vuelos NYC"
   git branch -M main
   git remote add origin https://github.com/<tu-usuario>/vuelos-cicd.git
   git push -u origin main
   ```
3. En GitHub: **Settings → Pages → Source → GitHub Actions**. Hacé esto
   *antes* de que corra el primer workflow (si ya corrió y falló con
   "Error: Not Found" en el paso de Pages, configurá la fuente ahora y
   volvé a correr ese mismo workflow con "Re-run all jobs").
4. Mirá la pestaña **Actions**: el job `ci` y después `cd` deberían
   terminar en verde, y el sitio queda publicado en
   `https://<tu-usuario>.github.io/vuelos-cicd/`.

## Los cuatro escenarios de la demostración

Hacé un commit y push por escenario, y guardá el enlace de Actions y las
capturas de cada uno antes de pasar al siguiente.

### 1. Primera publicación (ya viene lista en esta entrega)

`datos/actual.csv` ya es una copia de `control.csv` (febrero). Solo falta
subir:

```bash
git add .
git commit -m "Primera publicacion: febrero 2013 vs enero"
git push
```

Verificá: la portada muestra **Febrero 2013**, y el informe
(`informe_enero_vs_febrero.html`) compara febrero con enero — en nuestra
prueba local, sin drift (0 de 2 columnas).

### 2. Actualización válida (julio)

```bash
copy datos\nuevo.csv datos\actual.csv     # Windows
# cp datos/nuevo.csv datos/actual.csv     # macOS / Linux

git add datos/actual.csv
git commit -m "Actualizacion: julio 2013 vs enero"
git push
```

Verificá: la portada muestra **Julio 2013** con un commit nuevo, y el
informe (`informe_enero_vs_julio.html`) compara julio con enero — en
nuestra prueba local, **con drift** en las dos columnas (demoras bastante
mayores que en febrero y que en enero).

### 3. Error controlado

Abrí `datos/actual.csv`, elegí cualquier fila y anotá su `distancia_millas`
original (para poder restaurarla después). Cambiá ese valor a `0` y subí el
cambio a propósito:

```bash
git add datos/actual.csv
git commit -m "Error intencional: distancia en cero"
git push
```

Verificá: el job `ci` falla en el paso "Validar referencia.csv y
actual.csv" señalando exactamente el archivo, la fila y el campo
(`distancia_millas`); `cd` queda omitido (aparece gris, no se ejecuta); y
GitHub Pages sigue mostrando la última versión válida (julio).
(Confirmado localmente: con `distancia_millas` en 0, `validador.py` termina
con código de salida 1 y el mensaje identifica el archivo, la fila y el
campo exactos.)

### 4. Recuperación

Restaurá el valor original de `distancia_millas` que anotaste en el paso
anterior:

```bash
git add datos/actual.csv
git commit -m "Correccion: distancia restaurada"
git push
```

Verificá: `ci` y `cd` vuelven a quedar en verde, y la portada vuelve a
publicar julio, ahora con este nuevo commit.

## Evidencias a entregar (PDF único)

Según la consigna, el PDF final debe incluir: portada y enlaces, la
propuesta (quién consultaría el sitio, qué decisión apoya, tareas
priorizadas, criterios de aceptación, diagrama push→publicación), la fuente
y preparación de los lotes, la estructura del repositorio, las reglas y
pruebas de validación, el funcionamiento de CI/CD, las dos comparaciones de
Evidently, una tabla con los cuatro escenarios (cambio, resultado esperado
y observado, estado de CI y CD, commit visible en Pages, enlace a la
ejecución de Actions) y una conclusión sobre la utilidad del monitoreo.
También hay que adjuntar capturas (pruebas locales, portadas de febrero y
julio, los dos informes de Evidently, el fallo con CD omitido, el sitio
bloqueado y después de la recuperación) y los enlaces al repositorio
público y a GitHub Pages, verificando que abran, dejando `main` con datos
válidos al final.
