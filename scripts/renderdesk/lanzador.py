"""Render final en segundo plano: lanza «Render» de Maya en otro proceso y sigue su progreso.

Usa QProcess, así Maya no se bloquea: se puede seguir trabajando mientras renderiza.
El progreso sale de dos sitios:

* las imágenes que van apareciendo en la carpeta de salida (fotogramas terminados);
* las líneas «35% done» que escribe Arnold (progreso del fotograma en curso).
"""

import os
import signal
import subprocess
import sys
import time

from .qt import QtCore
from . import salida

INTERVALO_MS = 1500
LINEAS_GUARDADAS = 400


class Lanzamiento(QtCore.QObject):
    progreso = QtCore.Signal(int, int, int)      # fotogramas hechos, total, % del fotograma en curso
    terminado = QtCore.Signal(bool, str)         # bien, texto para el usuario
    linea = QtCore.Signal(str)

    def __init__(self, comando, carpeta, extension, total, registro=None, entorno=None, padre=None):
        super(Lanzamiento, self).__init__(padre)
        self.comando = list(comando)
        self.carpeta = carpeta
        self.extension = extension.lower()
        self.total = max(1, int(total))
        self.registro = registro
        self.entorno = entorno
        self.lineas = []
        self.hechos = 0
        self.porcentaje = 0
        self.inicio = None
        self.fin = None
        self.cancelado = False
        self._previas = {}
        self._terminados_log = 0        # fotogramas que el registro de Arnold ya dio por acabados
        self._resto = ""
        self.proceso = QtCore.QProcess(self)
        self.proceso.setProcessChannelMode(QtCore.QProcess.MergedChannels)
        self.proceso.readyReadStandardOutput.connect(self._leer)
        self.proceso.finished.connect(self._al_terminar)
        self.proceso.errorOccurred.connect(self._al_error)
        self._reloj = QtCore.QTimer(self)
        self._reloj.timeout.connect(self._contar)

    # ----- estado -----

    def en_marcha(self):
        return self.proceso.state() != QtCore.QProcess.NotRunning

    def segundos(self):
        if self.inicio is None:
            return 0.0
        return (self.fin or time.time()) - self.inicio

    def restante(self):
        """Segundos que faltan, sacados de lo que han tardado los fotogramas hechos."""
        hecho = self.hechos + self.porcentaje / 100.0
        if hecho <= 0:
            return None
        return self.segundos() / hecho * max(0.0, self.total - hecho)

    # ----- marcha -----

    def empezar(self):
        if not os.path.isdir(self.carpeta):
            os.makedirs(self.carpeta)
        self._previas = self._fechas()
        if self.entorno:
            entorno = QtCore.QProcessEnvironment.systemEnvironment()
            for clave, valor in self.entorno.items():
                entorno.insert(clave, valor)
            self.proceso.setProcessEnvironment(entorno)
        self.inicio = time.time()
        self.proceso.start(self.comando[0], self.comando[1:])
        self._reloj.start(INTERVALO_MS)

    def cancelar(self):
        """Para el render. «Render» lanza a su vez Maya en modo lotes: se para el árbol entero."""
        if self.en_marcha():
            self.cancelado = True
            matar_arbol(int(self.proceso.processId()))
            self.proceso.kill()

    # ----- seguimiento -----

    def _imagenes(self):
        encontradas = []
        for raiz, _, archivos in os.walk(self.carpeta):
            for nombre in archivos:
                if nombre.lower().endswith(self.extension):
                    encontradas.append(os.path.join(raiz, nombre))
        return encontradas

    def _fechas(self):
        fechas = {}
        for ruta in self._imagenes():
            try:
                fechas[ruta] = os.path.getmtime(ruta)
            except OSError:
                pass
        return fechas

    def _contar(self):
        # Nuevas o reescritas: si se vuelve a lanzar lo mismo, los nombres coinciden pero la fecha no.
        nuevas = [r for r, fecha in self._fechas().items() if self._previas.get(r) != fecha]
        hechos = min(self.total, len(nuevas))
        if hechos != self.hechos:
            self.hechos = hechos
            self.porcentaje = 0
        self.progreso.emit(self.hechos, self.total, self.porcentaje)

    def _leer(self):
        datos = bytes(self.proceso.readAllStandardOutput()).decode("utf-8", "replace")
        texto = self._resto + datos
        partes = texto.splitlines(True)
        self._resto = partes.pop() if partes and not partes[-1].endswith(("\n", "\r")) else ""
        for parte in partes:
            linea = parte.rstrip("\r\n")
            self.lineas.append(linea)
            self.linea.emit(linea)
            pct = salida.progreso_de_linea(linea)
            if pct is None:
                continue
            if pct >= 100:
                self._terminados_log += 1
            elif self._terminados_log == self.hechos:
                # Solo vale si es del fotograma en curso: con fotogramas rápidos las líneas llegan
                # en tandas y la última puede ser de uno que ya está guardado.
                self.porcentaje = pct
                self.progreso.emit(self.hechos, self.total, self.porcentaje)
        del self.lineas[:-LINEAS_GUARDADAS]

    def _guardar_registro(self):
        if not self.registro:
            return
        try:
            with open(self.registro, "w", encoding="utf-8") as f:
                f.write("\n".join(self.lineas))
        except OSError:
            pass

    def _al_terminar(self, codigo, _estado=None):
        self._reloj.stop()
        self.fin = time.time()
        if self._resto:
            self.lineas.append(self._resto)
            self._resto = ""
        self._contar()
        self._guardar_registro()
        bien = codigo == 0 and not self.cancelado and self.hechos > 0
        if self.cancelado:
            texto = "cancelado"
        elif bien:
            texto = "bien"
        else:
            texto = "fallo"
        self.terminado.emit(bien, texto)

    def _al_error(self, error):
        if error == QtCore.QProcess.FailedToStart:
            self._reloj.stop()
            self.fin = time.time()
            self.lineas.append("No se pudo arrancar: " + " ".join(self.comando))
            self._guardar_registro()
            self.terminado.emit(False, "no_arranca")


def _hijos(pid):
    try:
        salida = subprocess.check_output(["pgrep", "-P", str(pid)], universal_newlines=True)
    except (OSError, subprocess.CalledProcessError):
        return []
    return [int(x) for x in salida.split() if x.strip().isdigit()]


def matar_arbol(pid):
    """Termina ``pid`` y todos sus descendientes (el proceso de Maya en lotes que lanza «Render»)."""
    if not pid:
        return
    if sys.platform.startswith("win"):
        subprocess.call(["taskkill", "/T", "/F", "/PID", str(pid)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    pendientes, todos = [pid], []
    while pendientes:
        actual = pendientes.pop()
        todos.append(actual)
        pendientes.extend(_hijos(actual))
    for hijo in reversed(todos):
        try:
            os.kill(hijo, signal.SIGKILL)
        except OSError:
            pass
