"""Valida los lotes de vuelos antes de publicar el sitio.

Reglas (ver consigna de la Practica 5):
  - El archivo debe tener los ocho encabezados exactos y al menos una fila.
  - vuelo_id: entero positivo, unico dentro del archivo.
  - fecha: fecha valida (AAAA-MM-DD) y debe corresponder al mes/anio del lote.
  - origen: JFK, LGA o EWR.
  - destino: tres letras mayusculas.
  - demora_salida_min / demora_llegada_min: enteros (cero y negativos validos).
  - distancia_millas: entero positivo.
  - referencia.csv solo debe contener el lote "referencia".
  - actual.csv solo debe contener el lote "control" o el lote "nuevo"
    (uniforme: no se mezclan ambos en el mismo archivo).

Ante cualquier error se identifica archivo, fila y campo cuando corresponde,
se acumulan TODOS los errores encontrados y el programa termina con error
(exit code != 0).
"""
import csv
import re
import sys
from datetime import date

RUTA_REFERENCIA = "datos/referencia.csv"
RUTA_ACTUAL = "datos/actual.csv"

COLUMNAS_OBLIGATORIAS = [
    "vuelo_id",
    "fecha",
    "origen",
    "destino",
    "demora_salida_min",
    "demora_llegada_min",
    "distancia_millas",
    "lote",
]

AEROPUERTOS_VALIDOS = {"JFK", "LGA", "EWR"}
RE_DESTINO = re.compile(r"^[A-Z]{3}$")
RE_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Mes y anio que le corresponde a cada lote, segun la consigna.
MES_POR_LOTE = {
    "referencia": (2013, 1),
    "control": (2013, 2),
    "nuevo": (2013, 7),
}

# Que valores de "lote" se aceptan en cada archivo (referencia vs. actual).
LOTES_REFERENCIA = {"referencia"}
LOTES_ACTUAL = {"control", "nuevo"}


class DatosInvalidos(Exception):
    """Agrupa todos los errores de validacion encontrados."""

    def __init__(self, errores):
        self.errores = errores
        super().__init__("\n".join(errores))


def _leer_filas(ruta, errores):
    """Lee el CSV y devuelve (encabezados_ok, lista_de_filas)."""
    try:
        with open(ruta, newline="", encoding="utf-8") as f:
            lector = csv.DictReader(f, restkey="__columnas_de_mas__")
            encabezados = lector.fieldnames
            if encabezados is None:
                errores.append(f"{ruta}: el archivo esta vacio (sin encabezados).")
                return False, []
            faltantes = [c for c in COLUMNAS_OBLIGATORIAS if c not in encabezados]
            if faltantes:
                errores.append(
                    f"{ruta}: faltan encabezados obligatorios: {', '.join(faltantes)}."
                )
                return False, []
            filas = list(lector)
    except FileNotFoundError:
        errores.append(f"{ruta}: no se encontro el archivo.")
        return False, []

    if not filas:
        errores.append(f"{ruta}: el archivo no tiene ninguna fila de datos.")
        return True, []

    return True, filas


def _validar_fecha(valor, lote_fila, ruta, num_fila, errores):
    if not RE_FECHA.match(valor or ""):
        errores.append(
            f"{ruta}, fila {num_fila}, campo 'fecha': '{valor}' no tiene formato AAAA-MM-DD."
        )
        return
    try:
        anio, mes, dia = (int(p) for p in valor.split("-"))
        fecha_obj = date(anio, mes, dia)
    except ValueError:
        errores.append(
            f"{ruta}, fila {num_fila}, campo 'fecha': '{valor}' no es una fecha calendario valida."
        )
        return

    esperado = MES_POR_LOTE.get(lote_fila)
    if esperado is not None and (fecha_obj.year, fecha_obj.month) != esperado:
        anio_e, mes_e = esperado
        errores.append(
            f"{ruta}, fila {num_fila}, campo 'fecha': '{valor}' no corresponde al mes/anio "
            f"del lote '{lote_fila}' (se esperaba {anio_e}-{mes_e:02d})."
        )


def validar_archivo(ruta, lotes_permitidos, errores):
    ok_encabezados, filas = _leer_filas(ruta, errores)
    if not ok_encabezados or not filas:
        return

    ids_vistos = {}
    lotes_vistos = set()

    for i, fila in enumerate(filas, start=2):  # fila 1 = encabezado
        if fila.get("__columnas_de_mas__"):
            errores.append(f"{ruta}, fila {i}: tiene mas columnas de las esperadas.")

        for campo in COLUMNAS_OBLIGATORIAS:
            if fila.get(campo) is None or fila.get(campo) == "":
                errores.append(f"{ruta}, fila {i}, campo '{campo}': falta el valor.")

        # vuelo_id: entero positivo y unico
        vuelo_id = fila.get("vuelo_id")
        if vuelo_id:
            try:
                vuelo_id_num = int(vuelo_id)
                if vuelo_id_num <= 0:
                    errores.append(
                        f"{ruta}, fila {i}, campo 'vuelo_id': '{vuelo_id}' debe ser positivo."
                    )
                elif vuelo_id in ids_vistos:
                    errores.append(
                        f"{ruta}, fila {i}, campo 'vuelo_id': '{vuelo_id}' esta duplicado "
                        f"(ya aparece en la fila {ids_vistos[vuelo_id]})."
                    )
                else:
                    ids_vistos[vuelo_id] = i
            except ValueError:
                errores.append(
                    f"{ruta}, fila {i}, campo 'vuelo_id': '{vuelo_id}' no es un entero."
                )

        # lote
        lote_fila = fila.get("lote")
        if lote_fila:
            if lote_fila not in lotes_permitidos:
                errores.append(
                    f"{ruta}, fila {i}, campo 'lote': '{lote_fila}' no es valido aqui "
                    f"(se esperaba uno de: {', '.join(sorted(lotes_permitidos))})."
                )
            else:
                lotes_vistos.add(lote_fila)

            # fecha (solo si el lote de la fila es uno reconocido globalmente)
            if lote_fila in MES_POR_LOTE:
                fecha_valor = fila.get("fecha")
                if fecha_valor:
                    _validar_fecha(fecha_valor, lote_fila, ruta, i, errores)

        # origen
        origen = fila.get("origen")
        if origen and origen not in AEROPUERTOS_VALIDOS:
            errores.append(
                f"{ruta}, fila {i}, campo 'origen': '{origen}' no es JFK, LGA ni EWR."
            )

        # destino
        destino = fila.get("destino")
        if destino and not RE_DESTINO.match(destino):
            errores.append(
                f"{ruta}, fila {i}, campo 'destino': '{destino}' debe ser tres letras mayusculas."
            )

        # demoras: enteros (incluye cero y negativos)
        for campo in ("demora_salida_min", "demora_llegada_min"):
            valor = fila.get(campo)
            if valor:
                try:
                    int(valor)
                except ValueError:
                    errores.append(
                        f"{ruta}, fila {i}, campo '{campo}': '{valor}' no es un entero."
                    )

        # distancia_millas: entero positivo
        distancia = fila.get("distancia_millas")
        if distancia:
            try:
                distancia_num = int(distancia)
                if distancia_num <= 0:
                    errores.append(
                        f"{ruta}, fila {i}, campo 'distancia_millas': '{distancia}' debe ser "
                        "un entero positivo."
                    )
            except ValueError:
                errores.append(
                    f"{ruta}, fila {i}, campo 'distancia_millas': '{distancia}' no es un entero."
                )

    if len(lotes_vistos) > 1:
        errores.append(
            f"{ruta}: mezcla mas de un lote ({', '.join(sorted(lotes_vistos))}); "
            "debe contener un unico lote."
        )


def validar(ruta_referencia=RUTA_REFERENCIA, ruta_actual=RUTA_ACTUAL):
    errores = []
    validar_archivo(ruta_referencia, LOTES_REFERENCIA, errores)
    validar_archivo(ruta_actual, LOTES_ACTUAL, errores)
    if errores:
        raise DatosInvalidos(errores)


def main():
    try:
        validar()
    except DatosInvalidos as exc:
        print("Validacion fallida. Se encontraron los siguientes errores:")
        for error in exc.errores:
            print(f"  - {error}")
        sys.exit(1)
    print(f"OK: {RUTA_REFERENCIA} y {RUTA_ACTUAL} son validos.")


if __name__ == "__main__":
    main()
