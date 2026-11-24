"""Modo MantiTools.

Si el pack MantiTools está cargado, el menú de esta herramienta va dentro del
menú «MantiTools» como un submenú, en vez de ir suelto en la barra de Maya.
Sin MantiTools todo funciona como siempre.

Este archivo es igual en todas las herramientas del pack salvo ``HERRAMIENTA``;
el original está en ``mantitools/plantillas/pack.py``.
"""

from maya import cmds

HERRAMIENTA = "renderdesk"


def _lugar():
    """{parent, insertAfter} dentro del menú MantiTools, o None si no hay MantiTools."""
    try:
        from mantitools import menu
    except ImportError:
        return None
    try:
        return menu.lugar_para(HERRAMIENTA)
    except Exception:
        return None


def existe_menu(nombre):
    return bool(cmds.menu(nombre, exists=True) or cmds.menuItem(nombre, exists=True))


def quitar_menu(nombre):
    if existe_menu(nombre):
        cmds.deleteUI(nombre)


def crear_menu(nombre, etiqueta, padre="MayaWindow"):
    """Crea el menú de la herramienta, o su submenú dentro de MantiTools.

    Lo que se añada después con ``cmds.menuItem`` va dentro, igual en los dos casos.
    """
    quitar_menu(nombre)
    lugar = _lugar()
    if lugar:
        return cmds.menuItem(nombre, label=etiqueta, subMenu=True, tearOff=True, **lugar)
    return cmds.menu(nombre, label=etiqueta, parent=padre, tearOff=True)


def en_pack():
    """True si la herramienta está dentro de MantiTools (para ocultar, p. ej., su propio botón de estante)."""
    return _lugar() is not None
