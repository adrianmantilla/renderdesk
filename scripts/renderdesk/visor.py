"""Control del Arnold RenderView (el visor de Arnold) desde Python.

Solo se usan nombres de opción comprobados en la fase 0 con MtoA 5.6 (Maya 2027).
Un nombre que no existe no da error: el visor devuelve "" y escribe
«ARV: Couldn't find option» en el log, así que aquí no se inventan nombres.

En MtoA para Maya 2025 no existen ``opt`` ni ``get``: ``controlable()`` lo dice
y el panel deja esos botones al propio visor.
"""

CONTROL = "ArnoldRenderView"
RESOLUCIONES_PRUEBA = (100, 50, 25, 10)


def _cmds():
    from maya import cmds
    return cmds


def disponible():
    cmds = _cmds()
    try:
        return bool(cmds.pluginInfo("mtoa", query=True, loaded=True)) and hasattr(cmds, "arnoldRenderView")
    except RuntimeError:
        return False


def _opt(nombre, valor):
    try:
        _cmds().arnoldRenderView(opt=(nombre, str(valor)))
        return True
    except (TypeError, RuntimeError):
        return False


def _get(nombre):
    try:
        return _cmds().arnoldRenderView(get=nombre)
    except (TypeError, RuntimeError):
        return None


def controlable():
    """True si este MtoA deja manejar el visor desde fuera (opt/get).

    En MtoA 5.6 ``get`` devuelve None mientras el visor no ha renderizado nada, así
    que no sirve mirar el valor: lo que falla en las versiones sin control es el
    propio parámetro (Maya lanza TypeError por parámetro desconocido).
    """
    if not disponible():
        return False
    try:
        _cmds().arnoldRenderView(get="Run IPR")
    except TypeError:
        return False
    except RuntimeError:
        pass
    return True


def abierto():
    cmds = _cmds()
    return bool(cmds.workspaceControl(CONTROL, exists=True)
                and cmds.workspaceControl(CONTROL, query=True, visible=True))


def abrir():
    """Abre el visor (o lo trae delante). Devuelve True si queda abierto."""
    if not disponible():
        return False
    cmds = _cmds()
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.workspaceControl(CONTROL, edit=True, restore=True, visible=True)
    else:
        try:
            cmds.arnoldRenderView(mode="open")
        except RuntimeError:
            return False
    return cmds.workspaceControl(CONTROL, exists=True)


def probando():
    return _get("Run IPR") == "1"


def probar(activo):
    """Arranca o para el render interactivo."""
    if activo and not abierto():
        abrir()
    return _opt("Run IPR", "1" if activo else "0")


def region(activo):
    """Activa o quita el recorte por región (el rectángulo se dibuja en el visor)."""
    return _opt("Crop Region", "1" if activo else "0")


def en_region():
    return _get("Crop Region") == "1"


def instantanea():
    return _opt("Store Snapshot", "1")


def guardar_imagen(ruta):
    return _opt("Save Image", ruta)


def camara():
    return _get("Camera") or ""


def poner_camara(transformada):
    return _opt("Camera", transformada)


def resolucion_prueba_cercana(porcentaje):
    """El paso del visor (100, 50, 25 o 10 %) más cercano a ``porcentaje``."""
    return min(RESOLUCIONES_PRUEBA, key=lambda p: (abs(p - int(porcentaje)), -p))


def poner_resolucion_prueba(porcentaje):
    return _opt("Test Resolution", "{}%".format(resolucion_prueba_cercana(porcentaje)))


def resolucion_prueba():
    return _get("Test Resolution") or ""
