"""Pruebas automatizadas de validador.py con datos pequenos e independientes."""
import os
import shutil
import tempfile
import unittest

from validador import DatosInvalidos, validar

ENCABEZADO = "vuelo_id,fecha,origen,destino,demora_salida_min,demora_llegada_min,distancia_millas,lote\n"


def _fila_referencia(vuelo_id=1, fecha="2013-01-01", demora_salida="4", demora_llegada="20"):
    return f"{vuelo_id},{fecha},LGA,IAH,{demora_salida},{demora_llegada},1416,referencia\n"


def _fila_actual(vuelo_id=1, fecha="2013-02-01", distancia="529"):
    return f"{vuelo_id},{fecha},EWR,CLT,-4,4,{distancia},control\n"


class TestValidador(unittest.TestCase):
    def setUp(self):
        self.dir_temp = tempfile.mkdtemp()
        self.ruta_referencia = os.path.join(self.dir_temp, "referencia.csv")
        self.ruta_actual = os.path.join(self.dir_temp, "actual.csv")

    def tearDown(self):
        shutil.rmtree(self.dir_temp, ignore_errors=True)

    def _escribir(self, ruta, contenido):
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)

    def _validar(self):
        validar(ruta_referencia=self.ruta_referencia, ruta_actual=self.ruta_actual)

    # 1. Registro valido: no debe lanzar ninguna excepcion.
    def test_registro_valido_pasa(self):
        self._escribir(self.ruta_referencia, ENCABEZADO + _fila_referencia())
        self._escribir(self.ruta_actual, ENCABEZADO + _fila_actual())
        self._validar()  # no debe lanzar

    # 2. Demora negativa valida: un vuelo que llego/salio antes de tiempo.
    def test_demora_negativa_es_valida(self):
        self._escribir(
            self.ruta_referencia,
            ENCABEZADO + _fila_referencia(demora_salida="-7", demora_llegada="-15"),
        )
        self._escribir(self.ruta_actual, ENCABEZADO + _fila_actual())
        self._validar()  # no debe lanzar, cero y negativos son validos

    # 3. Encabezado faltante.
    def test_encabezado_faltante_falla(self):
        encabezado_incompleto = (
            "vuelo_id,fecha,origen,destino,demora_salida_min,demora_llegada_min,distancia_millas\n"
        )
        self._escribir(self.ruta_referencia, encabezado_incompleto + "1,2013-01-01,LGA,IAH,4,20,1416\n")
        self._escribir(self.ruta_actual, ENCABEZADO + _fila_actual())
        with self.assertRaises(DatosInvalidos) as ctx:
            self._validar()
        mensaje = "\n".join(ctx.exception.errores)
        self.assertIn("faltan encabezados", mensaje)
        self.assertIn("lote", mensaje)

    # 4. Fecha invalida (no corresponde al mes del lote).
    def test_fecha_invalida_falla(self):
        self._escribir(
            self.ruta_referencia,
            ENCABEZADO + _fila_referencia(fecha="2013-03-15"),  # referencia debe ser enero
        )
        self._escribir(self.ruta_actual, ENCABEZADO + _fila_actual())
        with self.assertRaises(DatosInvalidos) as ctx:
            self._validar()
        mensaje = "\n".join(ctx.exception.errores)
        self.assertIn("campo 'fecha'", mensaje)
        self.assertIn("2013-03-15", mensaje)

    # 5. Identificador duplicado.
    def test_id_duplicado_falla(self):
        self._escribir(
            self.ruta_referencia,
            ENCABEZADO + _fila_referencia(vuelo_id=1) + _fila_referencia(vuelo_id=1),
        )
        self._escribir(self.ruta_actual, ENCABEZADO + _fila_actual())
        with self.assertRaises(DatosInvalidos) as ctx:
            self._validar()
        mensaje = "\n".join(ctx.exception.errores)
        self.assertIn("vuelo_id", mensaje)
        self.assertIn("duplicado", mensaje)

    # 6. Distancia invalida (cero no es un entero positivo).
    def test_distancia_invalida_falla(self):
        self._escribir(self.ruta_referencia, ENCABEZADO + _fila_referencia())
        self._escribir(self.ruta_actual, ENCABEZADO + _fila_actual(distancia="0"))
        with self.assertRaises(DatosInvalidos) as ctx:
            self._validar()
        mensaje = "\n".join(ctx.exception.errores)
        self.assertIn("distancia_millas", mensaje)
        self.assertIn("'0'", mensaje)

    # Pruebas extra, utiles para la demo en clase.
    def test_origen_invalido_falla(self):
        fila = _fila_referencia().replace("LGA", "XYZ")
        self._escribir(self.ruta_referencia, ENCABEZADO + fila)
        self._escribir(self.ruta_actual, ENCABEZADO + _fila_actual())
        with self.assertRaises(DatosInvalidos) as ctx:
            self._validar()
        self.assertIn("origen", "\n".join(ctx.exception.errores))

    def test_mezcla_de_lotes_en_actual_falla(self):
        self._escribir(self.ruta_referencia, ENCABEZADO + _fila_referencia())
        self._escribir(
            self.ruta_actual,
            ENCABEZADO + _fila_actual(vuelo_id=1) + "2,2013-07-01,JFK,MCO,-3,-8,944,nuevo\n",
        )
        with self.assertRaises(DatosInvalidos) as ctx:
            self._validar()
        self.assertIn("mezcla mas de un lote", "\n".join(ctx.exception.errores))

    def test_archivo_vacio_sin_filas_falla(self):
        self._escribir(self.ruta_referencia, ENCABEZADO)
        self._escribir(self.ruta_actual, ENCABEZADO + _fila_actual())
        with self.assertRaises(DatosInvalidos) as ctx:
            self._validar()
        self.assertIn("no tiene ninguna fila", "\n".join(ctx.exception.errores))


class TestValidadorContraProyecto(unittest.TestCase):
    """Corre la validacion sobre los CSV reales del proyecto (datos/)."""

    def test_csv_del_proyecto_son_validos(self):
        validar()  # usa datos/referencia.csv y datos/actual.csv por defecto


if __name__ == "__main__":
    unittest.main()
