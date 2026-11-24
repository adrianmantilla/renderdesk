"""Historial de pruebas: cada instantánea guarda la imagen, el tiempo y los ajustes (Python puro).

Vive en la carpeta del proyecto de Maya, así sobrevive al cerrar Maya:

    <proyecto>/renderDesk/historial/<escena>/0001.png
    <proyecto>/renderDesk/historial/<escena>/0001.json

El JSON lleva lo necesario para volver exactamente a esa prueba: los valores de
render, lo elegido en el panel, la cámara y el tamaño, además de cuánto llevaba
renderizando y a qué hora se hizo.
"""

import json
import os
import re
import time

_NUMERO = re.compile(r"^(\d{4,})\.json$")


def nombre_seguro(texto):
    """Nombre de carpeta sin caracteres raros: «Mi escena v2.ma» -> «Mi_escena_v2»."""
    base = os.path.splitext(os.path.basename(texto or ""))[0] or "sin_titulo"
    return re.sub(r"[^\w\-]+", "_", base, flags=re.UNICODE).strip("_") or "sin_titulo"


class Historial(object):
    def __init__(self, carpeta):
        self.carpeta = carpeta

    def _numeros(self):
        if not os.path.isdir(self.carpeta):
            return []
        return sorted(int(m.group(1)) for m in (_NUMERO.match(n) for n in os.listdir(self.carpeta)) if m)

    def ruta_imagen(self, numero, extension=".png"):
        return os.path.join(self.carpeta, "{:04d}{}".format(numero, extension))

    def ruta_datos(self, numero):
        return os.path.join(self.carpeta, "{:04d}.json".format(numero))

    def siguiente(self):
        numeros = self._numeros()
        return (numeros[-1] + 1) if numeros else 1

    def reservar(self):
        """Número y ruta de imagen para la próxima instantánea (crea la carpeta)."""
        if not os.path.isdir(self.carpeta):
            os.makedirs(self.carpeta)
        numero = self.siguiente()
        return numero, self.ruta_imagen(numero)

    def guardar(self, numero, datos):
        """Escribe los datos de la instantánea ``numero``. Devuelve la entrada completa."""
        entrada = dict(datos)
        entrada.setdefault("hora", time.strftime("%H:%M"))
        entrada.setdefault("fecha", time.strftime("%Y-%m-%d"))
        entrada["numero"] = numero
        imagen = self.ruta_imagen(numero)
        entrada["imagen"] = os.path.basename(imagen) if os.path.isfile(imagen) else ""
        with open(self.ruta_datos(numero), "w", encoding="utf-8") as f:
            json.dump(entrada, f, ensure_ascii=False, indent=1)
        return self._completar(entrada)

    def _completar(self, entrada):
        entrada = dict(entrada)
        entrada["ruta_imagen"] = os.path.join(self.carpeta, entrada["imagen"]) if entrada.get("imagen") else ""
        return entrada

    def leer(self, numero):
        try:
            with open(self.ruta_datos(numero), encoding="utf-8") as f:
                return self._completar(json.load(f))
        except (OSError, ValueError):
            return None

    def entradas(self):
        """Todas las instantáneas, de la más nueva a la más antigua."""
        return [e for e in (self.leer(n) for n in reversed(self._numeros())) if e]

    def ultima_con_tiempo(self):
        """La instantánea más nueva que tiene tiempo medido (para estimar el final)."""
        for e in self.entradas():
            if e.get("segundos"):
                return e
        return None

    def borrar(self, numero):
        for ruta in (self.ruta_datos(numero), self.ruta_imagen(numero)):
            if os.path.isfile(ruta):
                os.remove(ruta)
