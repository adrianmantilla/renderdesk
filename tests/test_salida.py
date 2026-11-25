"""Pruebas de historial, salida y lanzador (sin Maya)."""

import os
import shutil
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from renderdesk import salida  # noqa: E402
from renderdesk.historial import Historial, nombre_seguro  # noqa: E402

try:
    from PySide6 import QtCore
except ImportError:  # pragma: no cover
    QtCore = None


class PruebaHistorial(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        self.h = Historial(os.path.join(self.carpeta, "historial", "escena"))

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def test_nombre_seguro(self):
        self.assertEqual(nombre_seguro("/x/Mi escena v2.ma"), "Mi_escena_v2")
        self.assertEqual(nombre_seguro(""), "sin_titulo")

    def test_guardar_leer_y_borrar(self):
        n1, ruta = self.h.reservar()
        self.assertEqual(n1, 1)
        open(ruta, "wb").write(b"x")
        e1 = self.h.guardar(n1, {"segundos": 12.5, "valores": {"aa": 3}})
        self.assertEqual(e1["imagen"], "0001.png")
        self.assertTrue(e1["ruta_imagen"].endswith("0001.png"))
        n2, _ = self.h.reservar()
        self.h.guardar(n2, {"segundos": None})
        self.assertEqual([e["numero"] for e in self.h.entradas()], [2, 1])
        self.assertEqual(self.h.entradas()[0]["imagen"], "")
        self.assertEqual(self.h.ultima_con_tiempo()["numero"], 1)
        self.h.borrar(1)
        self.assertEqual([e["numero"] for e in self.h.entradas()], [2])
        self.assertEqual(self.h.siguiente(), 3)


class PruebaSalida(unittest.TestCase):
    def test_prefijos_y_paquetes(self):
        self.assertEqual(salida.clave_de_prefijo(salida.prefijo("camara")), "camara")
        self.assertIsNone(salida.clave_de_prefijo("render/<Scene>"))
        self.assertEqual(salida.paquete_de(salida.aovs_de("composicion")), "composicion")
        self.assertEqual(salida.paquete_de([]), "ninguno")
        self.assertIsNone(salida.paquete_de(["diffuse"]))

    def test_ejemplo(self):
        self.assertEqual(salida.ejemplo("<Scene>/<Scene>_<Camera>", "salon", "cam", "png"), "salon/salon_cam.png")
        self.assertEqual(salida.ejemplo("<Scene>/<Camera>", "salon", "cam", "exr", 7, True), "salon/cam.0007.exr")

    def test_hilos(self):
        self.assertEqual(salida.hilos("todos", 8), 0)
        self.assertEqual(salida.hilos("mitad", 8), 4)
        self.assertEqual(salida.hilos("menos2", 8), -2)
        self.assertEqual(salida.hilos("menos2", 2), 0)

    def test_fotogramas(self):
        self.assertEqual(salida.total_fotogramas("fija", 1, 120), 1)
        self.assertEqual(salida.total_fotogramas("giro", 1, 120), 120)
        self.assertEqual(salida.texto_fotogramas(1, 120), "120 fotogramas · 5 s a 24 fps")

    def test_comando_render(self):
        c = salida.comando_render("/maya/bin/Render", "/p/copia.ma", "/p/images", "cam", 1, 120, "/p")
        self.assertEqual(c[:3], ["/maya/bin/Render", "-r", "arnold"])
        self.assertIn("-proj", c)
        self.assertEqual(c[c.index("-s") + 1], "1")
        self.assertEqual(c[c.index("-e") + 1], "120")
        self.assertEqual(c[-1], "/p/copia.ma")
        self.assertEqual(salida.ejecutable_render("/maya", windows=True), os.path.join("/maya", "bin", "Render.exe"))

    def test_progreso_de_linea(self):
        self.assertEqual(salida.progreso_de_linea("00:00:03  1210MB         |    35% done - 120 rays/pixel"), 35)
        self.assertIsNone(salida.progreso_de_linea("render done"))

    def test_giro_cabe(self):
        fov = salida.fov_de_camara(35, 1.417, 1920, 1080)
        self.assertAlmostEqual(fov, 32.3, delta=0.2)   # vertical: 36 mm × 9/16 con focal 35
        d = salida.distancia_giro(1.0, fov)
        self.assertGreater(d, 1.0 / 0.27)


@unittest.skipIf(QtCore is None, "sin PySide6")
class PruebaLanzador(unittest.TestCase):
    def setUp(self):
        from renderdesk import lanzador
        self.lanzador = lanzador
        self.app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
        self.carpeta = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.carpeta, ignore_errors=True)

    def _lanzar(self, guion, total, espera_ms=15000):
        lanz = self.lanzador.Lanzamiento([sys.executable, "-c", guion, self.carpeta], self.carpeta, ".png", total,
                                         registro=os.path.join(self.carpeta, "r.log"))
        lanz._reloj.setInterval(50)
        resultado, progresos = [], []
        lanz.terminado.connect(lambda bien, texto: resultado.append((bien, texto)))
        lanz.progreso.connect(lambda h, t, p: progresos.append((h, t, p)))
        bucle = QtCore.QEventLoop()
        lanz.terminado.connect(lambda *a: bucle.quit())
        QtCore.QTimer.singleShot(espera_ms, bucle.quit)
        return lanz, resultado, progresos, bucle

    def test_cuenta_imagenes_y_porcentaje(self):
        # Una imagen de antes, reescrita por el render: también cuenta.
        with open(os.path.join(self.carpeta, "f.0001.png"), "wb") as f:
            f.write(b"viejo")
        os.utime(os.path.join(self.carpeta, "f.0001.png"), (1, 1))
        guion = ("import os, sys, time\n"
                 "for f in (1, 2, 3):\n"
                 "    print('50% done - 4 rays/pixel', flush=True); time.sleep(0.1)\n"
                 "    open(os.path.join(sys.argv[1], 'f.%04d.png' % f), 'wb').write(b'x')\n")
        lanz, resultado, progresos, bucle = self._lanzar(guion, 3)
        lanz.empezar()
        bucle.exec()
        self.assertEqual(resultado, [(True, "bien")])
        self.assertEqual(lanz.hechos, 3)
        self.assertTrue(any(p == 50 for _, _, p in progresos))
        with open(os.path.join(self.carpeta, "r.log")) as f:
            self.assertIn("50% done", f.read())

    def test_porcentaje_solo_del_fotograma_en_curso(self):
        lanz = self.lanzador.Lanzamiento(["x"], self.carpeta, ".png", 3)
        lanz.hechos = 1                      # la imagen del primero ya se contó...
        lanz._resto = ""

        class Falso(object):
            def __init__(self, texto): self.texto = texto
            def readAllStandardOutput(self): return self.texto.encode()
        # ...pero las líneas del primero llegan ahora, en tanda, y luego las del segundo.
        lanz.proceso = Falso("50% done\n90% done\n")
        lanz._leer()
        self.assertEqual(lanz.porcentaje, 0)
        lanz.proceso = Falso("100% done\n20% done\n")
        lanz._leer()
        self.assertEqual(lanz.porcentaje, 20)

    def test_fallo_y_no_arranca(self):
        lanz, resultado, _, bucle = self._lanzar("import sys; sys.exit(3)", 1)
        lanz.empezar()
        bucle.exec()
        self.assertEqual(resultado, [(False, "fallo")])
        lanz = self.lanzador.Lanzamiento(["/no/existe/Render"], self.carpeta, ".png", 1)
        resultado = []
        lanz.terminado.connect(lambda bien, texto: resultado.append(texto))
        lanz.empezar()
        lanz.proceso.waitForFinished(3000)
        self.app.processEvents()
        self.assertEqual(resultado, ["no_arranca"])

    def test_cancelar_para_tambien_los_hijos(self):
        guion = ("import subprocess, sys, time\n"
                 "hijo = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
                 "print('PID', hijo.pid, flush=True)\n"
                 "time.sleep(30)\n")
        lanz, resultado, _, bucle = self._lanzar(guion, 5)
        pids = []
        lanz.linea.connect(lambda l: pids.extend(int(x) for x in l.split()[1:] if l.startswith("PID")))
        lanz.empezar()
        QtCore.QTimer.singleShot(1500, lanz.cancelar)
        bucle.exec()
        self.assertEqual(resultado, [(False, "cancelado")])
        self.assertTrue(pids)
        import time
        time.sleep(0.3)
        vivo = True
        try:
            os.waitpid(pids[0], os.WNOHANG)
        except ChildProcessError:
            pass
        try:
            os.kill(pids[0], 0)
            estado = open("/proc/{}/stat".format(pids[0])).read().split()[2] if os.path.exists("/proc") else "Z"
            vivo = estado != "Z"
        except OSError:
            vivo = False
        self.assertFalse(vivo)


if __name__ == "__main__":
    unittest.main()
