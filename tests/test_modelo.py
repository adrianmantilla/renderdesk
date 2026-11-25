"""Pruebas de lo que elige el panel (sin Maya ni Qt)."""

import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

from renderdesk import modelo, presets, visor  # noqa: E402
from renderdesk.modelo import Seleccion  # noqa: E402


class Seleccionar(unittest.TestCase):
    def test_sin_preset_usa_la_escena(self):
        base = dict(presets.fabrica(), aa=7)
        s = Seleccion(base=base)
        self.assertFalse(s.hay_preset())
        self.assertEqual(s.valores()["aa"], 7)
        self.assertEqual(s.nombre(), "Ajustes de la escena")

    def test_preset_y_nombre(self):
        s = Seleccion("final", "interior", ["vidrio"])
        self.assertEqual(s.valores(), presets.combinar("final", "interior", ["vidrio"]))
        self.assertEqual(s.nombre(), "Final · Interior")

    def test_retoque_y_volver(self):
        s = Seleccion("revision")
        s.retocar("diff", 4)
        self.assertEqual(s.valores()["diff"], 4)
        self.assertIn("diff", s.retocados())
        self.assertTrue(s.nombre().endswith("(modificado)"))
        s.retocar("diff", presets.combinar("revision")["diff"])   # vuelve al valor del preset
        self.assertFalse(s.modificado())
        s.retocar("aa", 6)
        s.volver_al_preset()
        self.assertEqual(s.valores(), presets.combinar("revision"))

    def test_retoque_sigue_al_cambiar_de_calidad(self):
        s = Seleccion("borrador")
        s.retocar("dD", 4)
        s.elegir_calidad("final")
        self.assertEqual(s.valores()["dD"], 4)

    def test_total_sigue_a_los_rebotes_retocados(self):
        s = Seleccion("revision")
        s.retocar("dD", 6)
        s.retocar("sD", 6)
        self.assertGreaterEqual(s.valores()["total"], 14)

    def test_extras_en_orden(self):
        s = Seleccion("final")
        s.poner_extra("hojas", True)
        s.poner_extra("vidrio", True)
        self.assertEqual(s.extras, ["vidrio", "hojas"])
        s.poner_extra("vidrio", False)
        self.assertEqual(s.extras, ["hojas"])

    def test_adoptar_cambios_de_fuera(self):
        s = Seleccion("revision")
        esperados = s.valores()
        escena = dict(esperados, spec=5)
        self.assertEqual(s.adoptar_de_escena(escena, esperados), ["spec"])
        self.assertEqual(s.valores()["spec"], 5)
        self.assertEqual(s.adoptar_de_escena(dict(escena), s.valores()), [])

    def test_guardar_y_leer(self):
        s = Seleccion("final", "exterior", ["niebla"], cambios={"aa": 6})
        otra = Seleccion.de_dict(s.a_dict())
        self.assertEqual(otra.valores(), s.valores())
        rara = Seleccion.de_dict({"calidad": "ultra", "escena": "luna", "cambios": {"xx": 1, "aa": 2}})
        self.assertFalse(rara.hay_preset())
        self.assertEqual(rara.escena, "producto")
        self.assertEqual(rara.cambios, {"aa": 2})


class Textos(unittest.TestCase):
    def test_tamanos(self):
        self.assertEqual(modelo.tamano_de(1920, 1080), "hd1080")
        self.assertIsNone(modelo.tamano_de(1500, 900))
        self.assertEqual(modelo.texto_tamano("uhd"), "4K UHD · 3840 × 2160")
        self.assertEqual(modelo.texto_tamano(None, 1500, 900), "Escena · 1500 × 900")

    def test_valores(self):
        self.assertEqual(modelo.texto_valor("den", 1), "sí")
        self.assertEqual(modelo.texto_valor("res", 50), "50 %")
        self.assertEqual(modelo.texto_valor("clamp", 5.0), "5")
        self.assertEqual(modelo.texto_valor("umbral", 0.015), "0,015")

    def test_cambios_frente_a_fabrica(self):
        self.assertEqual(modelo.cambios_frente_a_fabrica(presets.fabrica()), [])
        claves = [c for c, _, _ in modelo.cambios_frente_a_fabrica(presets.combinar("borrador"))]
        self.assertIn("aa", claves)

    def test_detalle_en_catalogo(self):
        for clave, tope in modelo.DETALLE:
            self.assertIn(clave, presets.catalogo())


class Visor(unittest.TestCase):
    def test_resolucion_de_prueba(self):
        self.assertEqual(visor.resolucion_prueba_cercana(50), 50)
        self.assertEqual(visor.resolucion_prueba_cercana(40), 50)
        self.assertEqual(visor.resolucion_prueba_cercana(75), 100)
        self.assertEqual(visor.resolucion_prueba_cercana(12), 10)


if __name__ == "__main__":
    unittest.main()
