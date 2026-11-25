"""Salida del render: nombres de archivo, formatos, paquetes de AOV, núcleos y la orden
del render en segundo plano (Python puro; ``escena_maya`` lo lleva a la escena).
"""

import math
import os
import re

from .i18n import t

# Nombres de archivo con las fichas de Maya (<Scene>, <Camera>). Cada render va a una
# subcarpeta con el nombre de la escena para no mezclar imágenes de escenas distintas.
NOMBRES = (
    ("escena_camara", "<Scene>/<Scene>_<Camera>"),
    ("escena", "<Scene>/<Scene>"),
    ("camara", "<Scene>/<Camera>"),
)

FORMATOS = ("png", "exr")
EXTENSIONES = {"png": ".png", "exr": ".exr"}

# Paquetes de AOV. Los nombres son los AOV de Arnold que crea MtoA.
PAQUETES_AOV = (
    ("ninguno", ()),
    ("basico", ("diffuse", "specular", "transmission", "sss", "emission")),
    ("composicion", ("diffuse", "specular", "transmission", "sss", "emission", "albedo", "Z", "N", "P",
                     "crypto_object", "crypto_material")),
)

# Núcleos para el render en segundo plano. En Arnold, threads negativo = todos menos N.
NUCLEOS = ("menos2", "todos", "mitad")

QUE = ("fija", "secuencia", "giro")
FPS = 24

_PROGRESO = re.compile(r"(\d{1,3})\s*% done")


def prefijo(clave):
    return dict(NOMBRES).get(clave, NOMBRES[0][1])


def clave_de_prefijo(texto):
    """Clave de ``NOMBRES`` para un prefijo de la escena, o None si es otro."""
    for clave, valor in NOMBRES:
        if valor == (texto or ""):
            return clave
    return None


def aovs_de(paquete):
    return tuple(dict(PAQUETES_AOV).get(paquete, ()))


def paquete_de(aovs):
    """El paquete que corresponde a una lista de AOV de la escena, o None si no coincide."""
    conjunto = set(aovs or ())
    for clave, nombres in PAQUETES_AOV:
        if conjunto == set(nombres):
            return clave
    return None


def hilos(nucleos, cpu=None):
    """Valor de ``threads`` de Arnold para cada opción de núcleos."""
    cpu = cpu or os.cpu_count() or 4
    if nucleos == "todos":
        return 0
    if nucleos == "mitad":
        return max(1, cpu // 2)
    return -2 if cpu > 2 else 0


def ejemplo(prefijo_maya, escena, camara, formato, fotograma=1, secuencia=False):
    """Ruta relativa de ejemplo: «salon/salon_camara_final.0001.png»."""
    nombre = (prefijo_maya or "<Scene>").replace("<Scene>", escena or "escena").replace(
        "<Camera>", camara or "camara").replace("<RenderLayer>", "masterLayer")
    extension = EXTENSIONES.get(formato, "." + (formato or "png"))
    if secuencia:
        return "{}.{:04d}{}".format(nombre, int(fotograma), extension)
    return nombre + extension


def texto_fotogramas(inicio, fin, fps=FPS):
    total = max(1, int(fin) - int(inicio) + 1)
    return t("salida.fotogramas_texto", total=total, segundos=("%g" % round(total / float(fps), 1)).replace(".", ","),
             fps=fps)


def total_fotogramas(que, inicio, fin):
    return 1 if que == "fija" else max(1, int(fin) - int(inicio) + 1)


def ejecutable_render(maya_location, windows=False):
    """Ruta de «Render» (el render por lotes de Maya) dentro de la instalación."""
    if not maya_location:
        return "Render.exe" if windows else "Render"
    return os.path.join(maya_location, "bin", "Render.exe" if windows else "Render")


def comando_render(ejecutable, escena, carpeta, camara, inicio, fin, proyecto=None):
    """Orden para renderizar ``escena`` con Arnold fuera de Maya.

    ``-ai:lve 2`` hace que Arnold escriba su progreso («35% done»), que el panel lee.
    ``-proj`` mantiene las rutas relativas de texturas aunque la copia viva en otra carpeta.
    """
    comando = [ejecutable, "-r", "arnold"]
    if proyecto:
        comando += ["-proj", proyecto]
    return comando + ["-rd", carpeta, "-cam", camara, "-s", str(int(inicio)), "-e", str(int(fin)), "-b", "1",
                      "-ai:lve", "2", escena]


def progreso_de_linea(linea):
    """Porcentaje del fotograma actual si la línea es de progreso de Arnold, o None."""
    m = _PROGRESO.search(linea or "")
    if not m:
        return None
    return max(0, min(100, int(m.group(1))))


def distancia_giro(radio, fov_grados, margen=1.15):
    """Distancia a la que una cámara con ese campo de visión ve entera una esfera de ``radio``."""
    mitad = math.radians(max(1.0, min(170.0, fov_grados)) / 2.0)
    return radio * margen / math.sin(mitad)


def fov_de_camara(focal_mm, apertura_horizontal_pulgadas, ancho, alto):
    """Campo de visión menor (horizontal o vertical) de una cámara de Maya, en grados."""
    apertura_h = apertura_horizontal_pulgadas * 25.4
    apertura_v = apertura_h * float(alto) / float(ancho)
    menor = min(apertura_h, apertura_v)
    return math.degrees(2 * math.atan(menor / 2.0 / focal_mm))
