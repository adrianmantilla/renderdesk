"""Fase 0: ¿se puede manejar el Arnold RenderView desde fuera? (herramienta de desarrollo)

Se ejecuta dentro de Maya CON interfaz, por ejemplo:

    maya -command "python(\"exec(open('/ruta/sonda_visor.py').read())\")"

con la variable RENDERDESK_SALIDA apuntando a una carpeta. Hace una serie de
pruebas espaciadas en el tiempo (el render interactivo necesita unos segundos),
guarda capturas e informe_visor.json, y cierra Maya al terminar si
RENDERDESK_CERRAR=1.
"""

import json
import os
import traceback

from maya import cmds, mel
import maya.OpenMayaUI as omui

try:
    from PySide6 import QtCore, QtWidgets
    from shiboken6 import wrapInstance
except ImportError:                                   # Maya 2024 y anteriores
    from PySide2 import QtCore, QtWidgets
    from shiboken2 import wrapInstance

SALIDA = os.environ.get("RENDERDESK_SALIDA", os.path.expanduser("~/renderdesk_sonda"))
CERRAR = os.environ.get("RENDERDESK_CERRAR", "1") == "1"
os.makedirs(SALIDA, exist_ok=True)
INFORME = {"pasos": []}


def guardar():
    with open(os.path.join(SALIDA, "informe_visor.json"), "w", encoding="utf-8") as f:
        json.dump(INFORME, f, ensure_ascii=False, indent=1, default=str)


def paso(nombre):
    def deco(fn):
        def envuelta():
            r = {"paso": nombre}
            try:
                r["resultado"] = fn()
                r["ok"] = True
            except Exception:  # noqa: BLE001
                r["ok"] = False
                r["error"] = traceback.format_exc()[-1500:]
            INFORME["pasos"].append(r)
            guardar()
        return envuelta
    return deco


def probar(etiqueta, fn):
    """Ejecuta fn y devuelve (ok, valor o error) sin romper la sonda."""
    try:
        return {"llamada": etiqueta, "ok": True, "valor": fn()}
    except Exception as e:  # noqa: BLE001
        return {"llamada": etiqueta, "ok": False, "error": str(e)[:400]}


def widget(nombre):
    ptr = omui.MQtUtil.findControl(nombre)
    return wrapInstance(int(ptr), QtWidgets.QWidget) if ptr else None


def captura(nombre_widget, archivo):
    w = widget(nombre_widget) if isinstance(nombre_widget, str) else nombre_widget
    if w is None:
        return "sin widget"
    ruta = os.path.join(SALIDA, archivo)
    ok = w.grab().save(ruta)
    return {"archivo": ruta, "guardado": ok, "tam": [w.width(), w.height()]}


def controles_arnold():
    todos = cmds.lsUI(type="workspaceControl") or []
    return [c for c in todos if "arnold" in c.lower() or "render" in c.lower()]


# ---------- pasos ----------

@paso("escena")
def p_escena():
    cmds.file(new=True, force=True)
    if not cmds.pluginInfo("mtoa", query=True, loaded=True):
        cmds.loadPlugin("mtoa")
    import mtoa.core
    mtoa.core.createOptions()
    cmds.setAttr("defaultRenderGlobals.currentRenderer", "arnold", type="string")
    e = cmds.polySphere(radius=5, name="bola")[0]
    cmds.move(0, 5, 0, e)
    cmds.polyPlane(width=60, height=60, name="suelo")
    cmds.shadingNode("aiSkyDomeLight", asLight=True, name="cielo")
    cam = cmds.rename(cmds.camera()[0], "camara_sonda")
    cmds.viewPlace(cam, eye=(0, 12, 30), lookAt=(0, 4, 0), perspective=True)
    for c in cmds.ls(type="camera"):
        cmds.setAttr(c + ".renderable", 0)
    cmds.setAttr(cmds.listRelatives(cam, shapes=True)[0] + ".renderable", 1)
    return {"maya": cmds.about(version=True), "mtoa": cmds.pluginInfo("mtoa", query=True, version=True),
            "qt": QtCore.qVersion()}


@paso("ayuda_comando")
def p_ayuda():
    r = {"whatIs": mel.eval("whatIs arnoldRenderView")}
    r["help"] = probar("help", lambda: cmds.help("arnoldRenderView"))
    r["controles_antes"] = controles_arnold()
    return r


@paso("abrir")
def p_abrir():
    r = [probar("mode=open", lambda: cmds.arnoldRenderView(mode="open"))]
    r.append({"controles_despues": controles_arnold()})
    return r


@paso("arrancar_ipr")
def p_ipr():
    intentos = [probar("opt Run IPR 1", lambda: cmds.arnoldRenderView(opt=("Run IPR", "1")))]
    for nombre in ("Run IPR", "Crop Region", "Region", "AOVs", "Camera", "Show Status Bar", "Display Settings",
                   "Test Resolution", "Progressive Refinement", "Snapshot", "Debug Shading", "Isolate Selected"):
        intentos.append(probar("get " + nombre, lambda n=nombre: cmds.arnoldRenderView(get=n)))
    return intentos


@paso("captura_ipr")
def p_captura():
    r = {}
    for c in controles_arnold():
        r[c] = captura(c, "visor_{}.png".format(c.replace("|", "_")))
    return r


@paso("region_y_parar")
def p_region():
    r = []
    for opt in (("Crop Region", "1"), ("Region", "1"), ("Run IPR", "0")):
        r.append(probar("opt " + " ".join(opt), lambda o=opt: cmds.arnoldRenderView(opt=o)))
    r.append(probar("get Run IPR", lambda: cmds.arnoldRenderView(get="Run IPR")))
    return r


@paso("instantanea_y_guardar")
def p_instantanea():
    r = []
    ruta = os.path.join(SALIDA, "visor_guardado.png")
    for opt in (("Store Snapshot", "1"), ("Snapshot", "1"), ("Save Image", ruta), ("Save Final Images", ruta)):
        r.append(probar("opt " + opt[0], lambda o=opt: cmds.arnoldRenderView(opt=o)))
    r.append({"existe_guardado": os.path.exists(ruta)})
    return r


@paso("acoplar_panel")
def p_acoplar():
    destino = None
    for c in controles_arnold():
        if "arnold" in c.lower():
            destino = c
            break
    if cmds.workspaceControl("renderDeskPrueba", exists=True):
        cmds.deleteUI("renderDeskPrueba")
    cmds.workspaceControl("renderDeskPrueba", label="RenderDesk (prueba)", initialWidth=320, retain=False,
                          floating=destino is None)
    cmds.setParent("renderDeskPrueba")
    cmds.columnLayout(adjustableColumn=True)
    cmds.text(label="Panel de RenderDesk acoplado junto al visor")
    cmds.button(label="Probar")
    r = {"destino": destino}
    if destino:
        r["dock_derecha"] = probar("dockToControl right", lambda: cmds.workspaceControl(
            "renderDeskPrueba", edit=True, dockToControl=(destino, "right")))
        r["flotante_visor"] = probar("visor flotante", lambda: cmds.workspaceControl(destino, query=True,
                                                                                         floating=True))
    principal = wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)
    r["captura_maya"] = captura(principal, "maya_completo.png")
    for w in QtWidgets.QApplication.topLevelWidgets():
        if w.isVisible() and w is not principal and w.width() > 300:
            r.setdefault("ventanas", []).append(captura(w, "ventana_{}.png".format(len(r.get("ventanas", [])))))
    return r


@paso("historial_por_captura")
def p_historial():
    """Alternativa para el historial: leer los píxeles del visor con grab()."""
    r = {}
    for c in controles_arnold():
        w = widget(c)
        if w is None:
            continue
        img = w.grab().toImage()
        r[c] = {"tam": [img.width(), img.height()], "pixel_centro": img.pixelColor(img.width() // 2,
                                                                                    img.height() // 2).name()}
    return r


def fin():
    INFORME["fin"] = True
    guardar()
    print("RENDERDESK SONDA FIN", SALIDA)
    if CERRAR:
        cmds.quit(force=True)


PLAN = [(0, p_escena), (1500, p_ayuda), (2500, p_abrir), (6000, p_ipr), (16000, p_captura),
        (18000, p_region), (21000, p_instantanea), (24000, p_acoplar), (28000, p_historial), (30000, fin)]
for ms, fn in PLAN:
    QtCore.QTimer.singleShot(5000 + ms, fn)       # 5 s de margen para que Maya termine de arrancar
print("RENDERDESK SONDA programada; resultados en", SALIDA)
