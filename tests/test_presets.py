"""Pruebas del núcleo (sin Maya): python -m unittest discover tests"""

import itertools
import json
import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

from renderdesk import coste, presets  # noqa: E402
from renderdesk.i18n import claves, t  # noqa: E402


class Combinar(unittest.TestCase):
    def test_calidades_base(self):
        self.assertEqual(presets.combinar("borrador")["aa"], 2)
        self.assertEqual(presets.combinar("revision")["aa"], 3)
        self.assertEqual(presets.combinar("final")["aa"], 4)
        self.assertEqual(presets.combinar("borrador")["den"], 1)
        self.assertEqual(presets.combinar("final")["den"], 0)

    def test_interior_sube_difuso_y_limita(self):
        v = presets.combinar("final", "interior")
        self.assertEqual(v["diff"], 3)
        self.assertEqual(v["dD"], 3)
        self.assertLessEqual(v["clamp"], 5)

    def test_producto_no_toca_borrador(self):
        self.assertEqual(presets.combinar("borrador", "producto")["sD"], 1)
        self.assertEqual(presets.combinar("revision", "producto")["sD"], 2)

    def test_vidrio(self):
        v = presets.combinar("revision", "producto", ["vidrio"])
        self.assertEqual(v["tD"], 12)
        self.assertEqual(v["trans"], 3)
        self.assertEqual(v["sD"], 3)
        self.assertEqual(presets.combinar("borrador", "producto", ["vidrio"])["sD"], 2)

    def test_extras_sumables_y_orden_indiferente(self):
        a = presets.combinar("final", "interior", ["hojas", "movimiento"])
        b = presets.combinar("final", "interior", ["movimiento", "hojas"])
        self.assertEqual(a, b)
        self.assertEqual(a["aa"], 6)
        self.assertEqual(a["at"], 16)
        self.assertEqual(a["mb"], 1)

    def test_giro_fija_ruido(self):
        self.assertEqual(presets.combinar("final", salida="giro")["lock"], 1)
        self.assertEqual(presets.combinar("final")["lock"], 0)

    def test_total_nunca_recorta(self):
        for cal, esc in itertools.product(presets.calidades(), presets.escenas()):
            for n in range(len(presets.extras()) + 1):
                for ex in itertools.combinations(presets.extras(), n):
                    v = presets.combinar(cal, esc, ex)
                    self.assertGreaterEqual(v["total"], v["tD"])
                    self.assertGreaterEqual(v["total"], v["dD"] + v["sD"])

    def test_todo_dentro_de_limites(self):
        cat = presets.catalogo()
        for cal, esc in itertools.product(presets.calidades(), presets.escenas()):
            v = presets.combinar(cal, esc, presets.extras(), "giro")
            for clave, valor in v.items():
                d = cat[clave]
                if "min" in d:
                    self.assertGreaterEqual(valor, d["min"], clave)
                if "max" in d:
                    self.assertLessEqual(valor, d["max"], clave)

    def test_cambios_a_mano_encima(self):
        v = presets.combinar("final", cambios={"aa": 8, "diff": 99})
        self.assertEqual(v["aa"], 8)
        self.assertEqual(v["diff"], 8)       # encajado en el máximo

    def test_desconocidos(self):
        with self.assertRaises(KeyError):
            presets.combinar("ultra")
        with self.assertRaises(KeyError):
            presets.combinar("final", "luna")
        with self.assertRaises(KeyError):
            presets.combinar("final", "producto", ["purpurina"])

    def test_diferencias(self):
        dif = presets.diferencias(presets.fabrica(), presets.combinar("borrador"))
        claves_dif = [c for c, _, _ in dif]
        self.assertIn("aa", claves_dif)
        self.assertNotIn("adapt", claves_dif)
        self.assertEqual(claves_dif, sorted(claves_dif, key=presets.orden_ajustes().index))

    def test_reglas_validas(self):
        cat = presets.catalogo()
        for archivo, raiz in (("escenas", "escenas"), ("extras", "extras"), ("salidas", "salidas")):
            with open(os.path.join(RAIZ, "scripts", "renderdesk", "presets", archivo + ".json"), encoding="utf-8") as f:
                datos = json.load(f)
            self.assertEqual(sorted(datos["orden"]), sorted(datos[raiz]))
            for item in datos[raiz].values():
                for r in item["reglas"]:
                    self.assertIn(r["clave"], cat)
                    self.assertIn(r["op"], presets.OPERACIONES)
                    for c in r.get("salvo", []) + r.get("solo", []):
                        self.assertIn(c, presets.calidades())

    def test_orden_completo(self):
        self.assertEqual(sorted(presets.orden_ajustes()), sorted(presets.catalogo()))


class Coste(unittest.TestCase):
    def test_final_cuesta_mas(self):
        b = coste.coste_relativo(presets.combinar("borrador"))
        r = coste.coste_relativo(presets.combinar("revision"))
        f = coste.coste_relativo(presets.combinar("final"))
        self.assertLess(b, r)
        self.assertLess(r, f)

    def test_rayos_fabrica(self):
        self.assertAlmostEqual(coste.rayos_por_pixel(presets.fabrica()), 9 * (1 + 4 + 3), places=5)

    def test_estimar_final(self):
        prueba = presets.combinar("borrador")
        final = presets.combinar("final")
        est = coste.estimar_final(10, prueba, final)
        self.assertGreater(est, 10)
        self.assertAlmostEqual(coste.estimar_final(10, final, final, fraccion_area=0.25), 40)
        self.assertAlmostEqual(coste.estimar_final(10, final, final, fotogramas=120), 1200)
        self.assertEqual(coste.estimar_final(0, final, final), 0)

    def test_texto(self):
        self.assertEqual(coste.texto_duracion(45), "45 s")
        self.assertEqual(coste.texto_duracion(240), "4 min")
        self.assertEqual(coste.texto_duracion(4800), "1 h 20 min")
        self.assertEqual(coste.texto_duracion(7200), "2 h")


class Textos(unittest.TestCase):
    def test_cada_ajuste_tiene_textos(self):
        for clave in presets.catalogo():
            for parte in ("nombre", "detalle", "porque"):
                self.assertIn("ajuste.{}.{}".format(clave, parte), claves())

    def test_nombres_de_presets(self):
        for c in presets.calidades():
            self.assertIn("calidad." + c, claves())
        for e in presets.escenas():
            self.assertIn("escena." + e, claves())
        for x in presets.extras():
            self.assertIn("extra." + x, claves())
        for s in presets.salidas():
            self.assertIn("salida." + s, claves())
        self.assertEqual(presets.nombre("final", "interior", True), "Final · Interior (modificado)")
        self.assertEqual(t("calidad.revision"), "Revisión")


if __name__ == "__main__":
    unittest.main()
