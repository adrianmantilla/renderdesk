"""Pruebas del panel con Qt sin pantalla y la escena de mentira de ``panel.Servicios``.

Necesitan PySide6 (``pip install PySide6-Essentials``); si no está, se saltan.
"""

import os
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6 import QtWidgets
except ImportError:  # pragma: no cover
    QtWidgets = None

if QtWidgets is not None:
    from renderdesk import presets
    from renderdesk.panel import PanelRenderDesk, Servicios
    APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@unittest.skipIf(QtWidgets is None, "sin PySide6")
class Panel(unittest.TestCase):
    def setUp(self):
        self.s = Servicios()
        self.p = PanelRenderDesk(self.s)

    def tearDown(self):
        self.p.detener()
        self.p.deleteLater()

    def test_arranca_con_la_escena(self):
        self.assertEqual(self.p.chip.text(), "Ajustes de la escena")
        self.assertFalse(self.p.boton_restaurar.isEnabled())
        self.assertTrue(self.p.aviso_sin_preset.isVisibleTo(self.p))
        self.assertFalse(self.p.botones_escena["interior"].isEnabled())

    def test_elegir_preset_escribe_en_la_escena(self):
        self.p.botones_calidad["final"].click()
        self.p.botones_escena["interior"].click()
        self.p.casillas_extra["vidrio"].click()
        self.p.aplicar_pendiente()
        self.assertEqual(self.s.valores, dict(self.s.valores, **presets.combinar("final", "interior", ["vidrio"])))
        self.assertEqual(self.p.chip.text(), "Final · Interior")
        self.assertTrue(self.p.boton_restaurar.isEnabled())
        self.assertEqual(self.s.datos_seleccion["extras"], ["vidrio"])
        self.assertIn("Capas de vidrio", self.p.lista_cambios.text())

    def test_cambios_seguidos_se_escriben_una_vez(self):
        self.p.botones_calidad["revision"].click()
        self.p.casillas_extra["sss"].click()
        self.p.casillas_extra["hojas"].click()
        self.assertEqual(self.s.aplicaciones, 0)       # todavía en el retardo
        self.p.aplicar_pendiente()
        self.assertEqual(self.s.aplicaciones, 1)

    def test_detalle_retoca_y_marca(self):
        self.p.botones_calidad["revision"].click()
        self.p.poner_nivel("detalle")
        self.p.controles_detalle["diff"].caja.setValue(5)
        self.p.aplicar_pendiente()
        self.assertEqual(self.s.valores["diff"], 5)
        self.assertEqual(self.p.chip.text(), "Revisión · Producto (modificado)")
        self.assertEqual(self.p.marcas_detalle["diff"].text(), "●")
        self.assertEqual(self.p.controles_experto["diff"].valor(), 5)      # el mismo valor en Experto
        self.assertTrue(self.p.boton_volver_detalle.isEnabled())
        self.p.boton_volver_detalle.click()
        self.p.aplicar_pendiente()
        self.assertEqual(self.s.valores["diff"], presets.combinar("revision")["diff"])
        self.assertEqual(self.p.marcas_detalle["diff"].text(), "")

    def test_experto_casilla(self):
        self.p.botones_calidad["final"].click()
        self.p.poner_nivel("experto")
        self.p.controles_experto["den"].click()
        self.p.aplicar_pendiente()
        self.assertEqual(self.s.valores["den"], 1)
        self.assertEqual(self.p.nombres_experto["aa"].text(), "AASamples")

    def test_cambiar_de_nivel_no_cambia_el_render(self):
        self.p.botones_calidad["final"].click()
        self.p.aplicar_pendiente()
        antes = dict(self.s.valores)
        for nivel in ("detalle", "experto", "sencillo"):
            self.p.poner_nivel(nivel)
        self.p.aplicar_pendiente()
        self.assertEqual(self.s.valores, antes)
        self.assertEqual(self.s.prefs["nivel"], "sencillo")

    def test_nivel_recordado(self):
        self.s.prefs["nivel"] = "experto"
        otro = PanelRenderDesk(self.s)
        self.assertEqual(otro.nivel(), "experto")
        otro.detener()

    def test_restaurar(self):
        self.s.valores["aa"] = 7
        self.p.al_cambiar_escena()
        self.p.botones_calidad["borrador"].click()
        self.p.aplicar_pendiente()
        self.assertEqual(self.s.valores["aa"], 2)
        self.p.boton_restaurar.click()
        self.assertEqual(self.s.valores["aa"], 7)
        self.assertEqual(self.p.chip.text(), "Ajustes de la escena")
        self.assertFalse(self.p.boton_restaurar.isEnabled())

    def test_cambio_desde_fuera_sale_como_retoque(self):
        self.p.botones_calidad["revision"].click()
        self.p.aplicar_pendiente()
        self.s.valores["spec"] = 6                     # alguien lo cambia en Render Settings
        self.p.vigilar()
        self.assertEqual(self.p.sel.cambios, {"spec": 6})
        self.assertTrue(self.p.chip.text().endswith("(modificado)"))

    def test_deshacer_vuelve_a_leer_la_escena(self):
        self.p.botones_calidad["revision"].click()
        self.p.aplicar_pendiente()
        guardado, valores = dict(self.s.datos_seleccion), dict(self.s.valores)
        self.p.botones_calidad["final"].click()
        self.p.aplicar_pendiente()
        self.s.datos_seleccion, self.s.valores = guardado, valores      # como un Ctrl+Z en Maya
        self.p.vigilar()
        self.assertEqual(self.p.chip.text(), "Revisión · Producto")
        self.assertEqual(self.p.sel.cambios, {})

    def test_seleccion_guardada_en_la_escena(self):
        self.p.botones_calidad["final"].click()
        self.p.botones_escena["exterior"].click()
        self.p.aplicar_pendiente()
        otro = PanelRenderDesk(self.s)                  # como al volver a abrir la escena
        self.assertEqual(otro.chip.text(), "Final · Exterior")
        self.assertTrue(otro.botones_calidad["final"].isChecked())
        otro.detener()

    def test_barra(self):
        self.assertEqual(self.p.combo_camara.currentText(), "persp")
        self.p.combo_camara.setCurrentIndex(0)
        self.p.combo_camara.activated.emit(0)
        self.assertEqual(self.s.camara_actual, "camara_final")
        self.assertTrue(self.p.combo_tamano.itemText(0).startswith("Escena · 960"))
        indice = [self.p.combo_tamano.itemText(i) for i in range(self.p.combo_tamano.count())].index(
            "Cuadrado · 1080 × 1080")
        self.p.combo_tamano.activated.emit(indice)
        self.assertEqual(self.s.tamano, (1080, 1080))
        self.assertEqual(self.p.combo_tamano.currentText(), "Cuadrado · 1080 × 1080")

    def test_probar_region_instantanea(self):
        self.p.boton_probar.click()
        self.assertTrue(self.s.ipr)
        self.assertEqual(self.p.boton_probar.text(), "■ Parar")
        self.p.boton_region.click()
        self.assertTrue(self.s.recorte)
        self.p.boton_instantanea.click()
        self.assertEqual(self.s.instantaneas, 1)
        self.s.ipr = False                              # lo para el propio visor
        self.p.vigilar()
        self.assertFalse(self.p.boton_probar.isChecked())
        self.assertEqual(self.p.boton_probar.text(), "▶ Probar")

    def test_modo_render(self):
        self.p.boton_modo.click()
        self.assertTrue(self.s.modo)
        self.p.vigilar()
        self.assertEqual(self.p.boton_modo.text(), "Volver")


if __name__ == "__main__":
    unittest.main()
