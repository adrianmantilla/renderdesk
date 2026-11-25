"""Plugin de Maya para RenderDesk.

Aparece en el Plug-in Manager como «renderdesk_plugin». Al cargarlo crea el menú
RenderDesk y las órdenes para el Editor de atajos; al descargarlo lo quita todo.
"""

import maya.api.OpenMaya as om
from maya import cmds


def maya_useNewAPI():
    pass


def initializePlugin(objeto):
    import renderdesk
    plugin = om.MFnPlugin(objeto, "RenderDesk", renderdesk.__version__, "Any")
    try:
        from renderdesk import interfaz_maya
        cmds.evalDeferred(interfaz_maya.iniciar, lowestPriority=True)
    except Exception as error:
        cmds.warning("RenderDesk no se pudo cargar: {}".format(error))
    return plugin


def uninitializePlugin(objeto):
    try:
        from renderdesk import interfaz_maya
        interfaz_maya.detener()
    except Exception:
        pass
