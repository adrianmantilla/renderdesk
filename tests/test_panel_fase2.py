"""Panel, fase 2: historial, comparar, recuperar, pestaña Salida y render final (Qt sin pantalla)."""

import os
import shutil
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:  # pragma: no cover
    QtWidgets = None

if QtWidgets is not None:
    from renderdesk import presets, salida
    from renderdesk.panel import PanelRenderDesk, Servicios
    APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@unittest.skipIf(QtWidgets is None, "sin PySide6")
class Fase2(unittest.TestCase):
    def setUp(self):
        self.s = Servicios()
        self.p = PanelRenderDesk(self.s)

    def tearDown(self):
        if self.p.render_en_marcha():
            self.p.lanzamiento.cancelar()
            self.p.lanzamiento.proceso.waitForFinished(3000)
        self.p.detener()
        self.p.deleteLater()
        shutil.rmtree(self.s.carpeta, ignore_errors=True)

    def _preset(self, calidad="revision"):
        self.p.botones_calidad[calidad].click()
        self.p.aplicar_pendiente()

    # ----- historial -----

    def test_instantanea_guarda_imagen_tiempo_y_ajustes(self):
        self.assertTrue(self.p.tira.vacio.isVisibleTo(self.p))
        self._preset("revision")
        self.p.boton_probar.click()
        self.p._desde -= 14                          # como si llevara 14 s renderizando
        self.p.boton_instantanea.click()
        entradas = self.p.historial().entradas()
        self.assertEqual(len(entradas), 1)
        e = entradas[0]
        self.assertEqual(self.s.instantaneas, 1)     # también la del visor de Arnold
        self.assertTrue(os.path.isfile(e["ruta_imagen"]))
        self.assertAlmostEqual(e["segundos"], 14, delta=1)
        self.assertEqual(e["seleccion"]["calidad"], "revision")
        self.assertEqual(e["valores"]["aa"], presets.combinar("revision")["aa"])
        self.assertEqual(e["camara"], "persp")
        self.assertEqual(self.p.tira.lista.count(), 1)
        self.assertIn("14 s", self.p.tira.lista.item(0).text())
        self.assertIn("Final estimado", self.p.pestana_salida.estimado.text())

    def test_instantanea_sin_probar_no_tiene_tiempo(self):
        self.p.instantanea()
        self.assertIsNone(self.p.historial().entradas()[0]["segundos"])
        self.assertIn("haz una prueba", self.p.pestana_salida.estimado.text())

    def test_cambiar_ajustes_reinicia_el_tiempo(self):
        self._preset("revision")
        self.p.boton_probar.click()
        self.p._desde -= 30
        self.p.botones_calidad["final"].click()
        self.p.aplicar_pendiente()
        self.assertLess(self.p.instantanea()["segundos"], 2)

    def test_recuperar_vuelve_a_la_prueba(self):
        self._preset("borrador")
        self.p.instantanea()
        self.p.botones_calidad["final"].click()
        self.p.combo_camara.setCurrentIndex(0)
        self.p._al_elegir_camara(0)                  # camara_final
        self.p.aplicar_pendiente()
        self.assertEqual(self.s.valores["aa"], presets.combinar("final")["aa"])
        self.p.tira.lista.item(0).setSelected(True)
        self.assertTrue(self.p.tira.boton_recuperar.isEnabled())
        self.p.tira.boton_recuperar.click()
        self.assertEqual(self.s.valores["aa"], presets.combinar("borrador")["aa"])
        self.assertEqual(self.p.sel.calidad, "borrador")
        self.assertEqual(self.s.camara_actual, "persp")
        self.assertIn("#1", self.p.estado.text())

    def test_comparar_y_borrar(self):
        self.p.instantanea()
        self.s.valores["aa"] = 5
        self.p.instantanea()
        lista = self.p.tira.lista
        self.assertEqual(lista.count(), 2)
        lista.item(0).setSelected(True)
        self.assertEqual(self.p.tira.boton_comparar.text(), "Comparar con ahora")
        dialogo = self.p._al_comparar(self.p.tira.seleccionadas())
        self.assertEqual(dialogo.vista.texto_b, "Ahora")
        self.assertFalse(dialogo.vista.a.isNull())
        self.assertFalse(dialogo.vista.b.isNull())
        dialogo.vista.poner_corte(0)
        dialogo.vista.grab()                         # que pinte sin errores
        dialogo.close()
        lista.item(1).setSelected(True)
        self.assertEqual(self.p.tira.boton_comparar.text(), "Comparar las dos")
        self.assertFalse(self.p.tira.boton_recuperar.isEnabled())
        dialogo = self.p._al_comparar(self.p.tira.seleccionadas())
        self.assertTrue(dialogo.vista.texto_a.startswith("#1"))
        dialogo.close()
        self.p.tira.boton_borrar.click()
        self.assertEqual(self.p.historial().entradas(), [])
        self.assertTrue(self.p.tira.vacio.isVisibleTo(self.p))

    # ----- salida -----

    def test_giro_pone_120_fotogramas_y_fija_el_ruido(self):
        self._preset("final")
        self.p.pestanas.setCurrentIndex(1)
        ps = self.p.pestana_salida
        self.s.datos_salida["fin"] = 10                # el rango de fábrica de Maya
        self.assertFalse(ps.fila_fotogramas.isVisibleTo(self.p))
        ps.botones_que["giro"].click()
        self.p.aplicar_pendiente()
        self.assertEqual((self.s.datos_salida["inicio"], self.s.datos_salida["fin"]), (1, 120))
        self.assertTrue(self.s.datos_salida["animacion"])
        self.assertEqual(self.p.sel.salida, "giro")
        self.assertEqual(self.s.valores["lock"], 1)
        self.assertTrue(ps.boton_giro.isVisibleTo(self.p))
        self.assertIn("120 fotogramas", ps.texto_fotogramas.text())
        self.assertIn("escena_persp.0001.png", ps.ejemplo.text())
        ps.boton_giro.click()
        self.assertEqual(self.s.giros, 1)
        self.assertEqual(self.p.combo_camara.currentText(), "camara_giro")
        self.assertIn("camara_giro", ps.texto_giro.text())

    def test_formato_nombre_y_pasadas(self):
        self.p.pestanas.setCurrentIndex(1)
        ps = self.p.pestana_salida
        ps.botones_aov["composicion"].click()
        self.assertEqual(self.s.datos_salida["aovs"], list(salida.aovs_de("composicion")))
        self.assertTrue(ps.aviso_aov.isVisibleTo(self.p))     # pasadas en PNG
        ps.botones_formato["exr"].click()
        self.assertEqual(self.s.datos_salida["formato"], "exr")
        self.assertFalse(ps.aviso_aov.isVisibleTo(self.p))
        ps.combo_nombre.setCurrentIndex(ps.combo_nombre.findData("camara"))
        ps._al_nombre(ps.combo_nombre.currentIndex())
        self.assertEqual(self.s.datos_salida["prefijo"], "<Scene>/<Camera>")
        self.assertIn("escena/persp.exr", ps.ejemplo.text())
        self.s.datos_salida["prefijo"] = "otra/cosa"
        ps.refrescar()
        self.assertEqual(ps.combo_nombre.currentData(), "otro")
        ps.casilla_autotx.click()
        self.assertFalse(self.s.datos_salida["autotx"])
        ps.combo_nucleos.setCurrentIndex(2)
        ps._al_nucleos(2)
        self.assertEqual(self.s.prefs["nucleos"], "mitad")

    # ----- render final -----

    def _esperar(self, condicion, ms=20000):
        reloj = QtCore.QElapsedTimer()
        reloj.start()
        while not condicion() and reloj.elapsed() < ms:
            APP.processEvents(QtCore.QEventLoop.AllEvents, 50)
        return condicion()

    def test_render_final_en_segundo_plano(self):
        self._preset("borrador")
        ps = self.p.pestana_salida
        ps.botones_que["giro"].click()
        self.s.poner_salida(fin=12)
        ps.refrescar()
        self.assertIn("no Final", ps.aviso_calidad.text())
        ps.boton_final.click()
        self.assertTrue(self.p.render_en_marcha())
        self.assertFalse(ps.boton_final.isEnabled())
        self.assertTrue(self.p.tarjeta_render.isVisibleTo(self.p))
        # Mientras renderiza se puede seguir trabajando con el panel.
        self.p.botones_calidad["revision"].click()
        self.p.aplicar_pendiente()
        self.assertTrue(self._esperar(lambda: "Fotograma" in self.p.tarjeta_render.texto.text()))
        self.assertTrue(self._esperar(lambda: not self.p.render_en_marcha()))
        self._esperar(lambda: bool(self.s.avisos), 2000)
        self.assertEqual(self.p.lanzamiento.hechos, 12)
        self.assertIn("terminado", self.p.tarjeta_render.titulo.text())
        self.assertIn("12 de 12", self.s.avisos[-1])
        self.assertTrue(ps.boton_final.isEnabled())
        self.p.tarjeta_render.boton_carpeta.click()
        self.assertEqual(self.s.carpetas_abiertas, [self.p.lanzamiento.carpeta])

    def test_cancelar_render(self):
        self.s.segundos_por_fotograma = 1.0
        ps = self.p.pestana_salida
        ps.botones_que["secuencia"].click()
        self.s.poner_salida(fin=50)
        ps.refrescar()
        ps.boton_final.click()
        self.assertTrue(self._esperar(lambda: self.p.lanzamiento.lineas))
        self.p.tarjeta_render.boton_cancelar.click()
        self.assertTrue(self._esperar(lambda: not self.p.render_en_marcha(), 5000))
        self._esperar(lambda: bool(self.s.avisos), 2000)
        self.assertIn("Cancelado", self.p.tarjeta_render.texto.text())
        self.assertIn("no terminó", self.s.avisos[-1])

    def test_fallo_al_preparar(self):
        def falla(que, nucleos):
            raise OSError("disco lleno")
        self.s.preparar_render = falla
        self.p.pestana_salida.boton_final.click()
        self.assertIn("disco lleno", self.p.tarjeta_render.texto.text())
        self.assertFalse(self.p.render_en_marcha())


if __name__ == "__main__":
    unittest.main()
