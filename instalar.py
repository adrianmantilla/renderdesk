"""Instalador de RenderDesk.

Arrastra este archivo desde el explorador de archivos hasta el visor de Maya.
Crea el módulo «renderdesk.mod» en tu carpeta de Maya apuntando a esta carpeta,
carga el plugin y lo marca para que se cargue siempre.

Para desinstalar, borra ese archivo .mod (la ruta se muestra en el Script Editor
al instalar). No muevas la carpeta del plugin después de instalar; si lo haces,
vuelve a arrastrar este archivo.
"""

import os
import sys

PLUGIN = "renderdesk_plugin"


def _raiz():
    return os.path.dirname(os.path.abspath(__file__))


def contenido_mod(raiz, version):
    raiz = raiz.replace("\\", "/")
    return ("+ RenderDesk {version} {raiz}\n"
            "scripts: scripts\n"
            "plug-ins: plug-ins\n").format(version=version, raiz=raiz)


def _version(raiz):
    ruta = os.path.join(raiz, "scripts", "renderdesk", "__init__.py")
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            if linea.startswith("__version__"):
                return linea.split("=")[1].strip().strip("\"'")
    return "0.0.0"


def instalar():
    from maya import cmds

    raiz = _raiz()
    print("RenderDesk | instalando desde " + raiz)
    version = _version(raiz)
    carpeta_modulos = os.path.join(cmds.internalVar(userAppDir=True), "modules")
    os.makedirs(carpeta_modulos, exist_ok=True)
    ruta_mod = os.path.join(carpeta_modulos, "renderdesk.mod")
    with open(ruta_mod, "w", encoding="utf-8") as f:
        f.write(contenido_mod(raiz, version))
    print("RenderDesk | módulo escrito en " + ruta_mod)

    scripts = os.path.join(raiz, "scripts")
    sys.path[:] = [p for p in sys.path
                   if os.path.normpath(p) == os.path.normpath(scripts)
                   or not os.path.isfile(os.path.join(p, "renderdesk", "__init__.py"))]
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    for nombre in [m for m in sys.modules if m == "renderdesk" or m.startswith("renderdesk.")]:
        del sys.modules[nombre]

    ruta_plugin = os.path.join(raiz, "plug-ins", PLUGIN + ".py")
    if cmds.pluginInfo(PLUGIN, query=True, loaded=True):
        cmds.unloadPlugin(PLUGIN, force=True)
    cmds.loadPlugin(ruta_plugin)
    cmds.pluginInfo(PLUGIN, edit=True, autoload=True)

    from renderdesk.i18n import t
    cmds.confirmDialog(title=t("instalado.titulo"), message=t("instalado.texto", version=version),
                       button=[t("boton.aceptar")])


def onMayaDroppedPythonFile(*_):
    """Maya llama a esta función al soltar el archivo en el visor."""
    try:
        instalar()
    except Exception as error:
        from maya import cmds
        cmds.confirmDialog(title="RenderDesk", message="No se pudo instalar RenderDesk: {}".format(error),
                           button=["OK"])
        raise
    finally:
        sys.modules.pop(__name__, None)
