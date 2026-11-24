"""Importa Qt (PySide6 en Maya 2025 y posteriores, PySide2 en versiones antiguas)."""

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    import shiboken6 as shiboken
except ImportError:  # pragma: no cover - Maya 2024 o anterior
    from PySide2 import QtCore, QtGui, QtWidgets
    import shiboken2 as shiboken

try:
    from PySide6 import QtSvg
except ImportError:  # pragma: no cover
    try:
        from PySide2 import QtSvg
    except ImportError:
        QtSvg = None

__all__ = ["QtCore", "QtGui", "QtWidgets", "QtSvg", "shiboken", "posicion_global", "posicion_local", "sigue_vivo",
           "destruir", "ventana_maya"]


def posicion_global(evento):
    """Posición del ratón en pantalla de un evento de ratón, como QPoint."""
    if hasattr(evento, "globalPosition"):
        return evento.globalPosition().toPoint()
    return evento.globalPos()  # pragma: no cover - PySide2


def posicion_local(evento):
    """Posición del ratón dentro del widget de un evento de ratón, como QPoint."""
    if hasattr(evento, "position"):
        return evento.position().toPoint()
    return evento.pos()  # pragma: no cover - PySide2


def sigue_vivo(objeto):
    """False si el widget de Qt ya se destruyó por dentro."""
    try:
        return objeto is not None and shiboken.isValid(objeto)
    except Exception:
        return False


def destruir(objeto):
    """Borra ya el objeto de Qt (no con deleteLater, que puede llegar tarde y romper Maya)."""
    if sigue_vivo(objeto):
        try:
            shiboken.delete(objeto)
        except Exception:
            pass


def ventana_maya():
    """La ventana principal de Maya como QWidget, o None fuera de Maya."""
    try:
        from maya import OpenMayaUI as omui
    except ImportError:
        return None
    puntero = omui.MQtUtil.mainWindow()
    if not puntero:
        return None
    return shiboken.wrapInstance(int(puntero), QtWidgets.QWidget)
