"""Monta la lámina de la fase 0 a partir de medidas/informe.json (herramienta de desarrollo).

    mayapy herramientas/componer_lamina.py /ruta/medidas

Usa Qt de Maya (sin abrir Maya). Deja lamina.jpg: los renders en fila con su
nombre, su tiempo y un recorte ampliado de la copa y la cera para ver el ruido.
"""

import json
import os
import sys

try:
    from PySide6 import QtCore, QtGui
except ImportError:
    from PySide2 import QtCore, QtGui

NOMBRES = {"fabrica": "Fábrica", "borrador": "Borrador", "revision": "Revisión", "final": "Final",
           "final_oidn": "Final + OIDN"}


def main():
    carpeta = os.path.abspath(sys.argv[1])
    with open(os.path.join(carpeta, "informe.json"), encoding="utf-8") as f:
        informe = json.load(f)
    app = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication(["x", "-platform", "offscreen"])  # noqa: F841
    renders = [r for r in informe["renders"] if r.get("imagen") and os.path.exists(r["imagen"])]
    ancho_col, alto_img, alto_rec = 640, 360, 240
    lienzo = QtGui.QImage(ancho_col * len(renders), 40 + alto_img + alto_rec + 50, QtGui.QImage.Format_RGB32)
    lienzo.fill(QtGui.QColor("#202020"))
    p = QtGui.QPainter(lienzo)
    p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
    fuente = QtGui.QFont("Helvetica", 18)
    p.setFont(fuente)
    for i, r in enumerate(renders):
        img = QtGui.QImage(r["imagen"])
        x = i * ancho_col
        p.setPen(QtGui.QColor("#f0c27e"))
        p.drawText(x + 12, 28, "{}  ·  {} s".format(NOMBRES.get(r["nombre"], r["nombre"]), r.get("segundos")))
        p.drawImage(QtCore.QRect(x, 40, ancho_col, alto_img), img)
        # recorte ampliado (copa y cera, centro-izquierda de la imagen), x2 sobre la imagen a tamaño completo
        w, h = img.width(), img.height()
        rec = QtCore.QRect(int(w * 0.30), int(h * 0.42), int(w * 0.25), int(h * 0.25))
        p.drawImage(QtCore.QRect(x, 40 + alto_img, ancho_col, alto_rec), img.copy(rec))
        v = r.get("valores", {})
        p.setPen(QtGui.QColor("#bbbbbb"))
        p.setFont(QtGui.QFont("Helvetica", 13))
        p.drawText(x + 12, 40 + alto_img + alto_rec + 30, "AA {} · dif {} · tra {} · sss {} · OIDN {} · {} %".format(
            v.get("aa"), v.get("diff"), v.get("trans"), v.get("sss"), "sí" if v.get("den") else "no", v.get("res")))
        p.setFont(fuente)
    p.end()
    salida = os.path.join(carpeta, "lamina.jpg")
    lienzo.save(salida, "JPG", 80)
    print("RENDERDESK LAMINA", salida)


if __name__ == "__main__":
    main()
