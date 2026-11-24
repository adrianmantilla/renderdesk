"""Fase 1: prueba del panel de RenderDesk dentro de Maya con interfaz (herramienta de desarrollo).

Se lanza así, con preferencias de Maya aparte para no tocar las del usuario:

    export MAYA_APP_DIR=/carpeta/prefs_de_prueba RENDERDESK_SALIDA=/carpeta/salida
    maya -command "python(\\"exec(open('/ruta/herramientas/prueba_panel.py').read())\\")"

Carga el plugin desde este repositorio, abre el panel junto al visor de Arnold y
recorre la fase 1: presets, niveles, Probar, Región, Instantánea, cambios desde
fuera, Ctrl+Z, cámara y tamaño, «Modo render» y Restaurar. Guarda capturas e
``informe_panel.json`` en RENDERDESK_SALIDA y cierra Maya si RENDERDESK_CERRAR=1.
"""

import json
import os
import sys
import traceback

from maya import cmds
import maya.OpenMayaUI as omui

try:
    from PySide6 import QtCore, QtWidgets
    from shiboken6 import wrapInstance
except ImportError:                                   # Maya 2024 y anteriores
    from PySide2 import QtCore, QtWidgets
    from shiboken2 import wrapInstance

RAIZ = os.environ.get("RENDERDESK_RAIZ") or os.path.dirname(os.path.dirname(os.path.abspath(
    globals().get("__file__", os.path.join(os.getcwd(), "herramientas", "x.py")))))
SALIDA = os.environ.get("RENDERDESK_SALIDA", os.path.expanduser("~/renderdesk_prueba_panel"))
CERRAR = os.environ.get("RENDERDESK_CERRAR", "1") == "1"
os.makedirs(SALIDA, exist_ok=True)
INFORME = {"raiz": RAIZ, "pasos": []}
M = {}                                                # módulos de renderdesk, tras cargar el plugin


def guardar():
    with open(os.path.join(SALIDA, "informe_panel.json"), "w", encoding="utf-8") as f:
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
                r["error"] = traceback.format_exc()[-2000:]
            INFORME["pasos"].append(r)
            guardar()
            print("RENDERDESK PRUEBA", nombre, "OK" if r["ok"] else "FALLO")
        return envuelta
    return deco


def captura(w, archivo):
    if w is None:
        return "sin widget"
    ruta = os.path.join(SALIDA, archivo)
    return {"archivo": archivo, "guardado": w.grab().save(ruta), "tam": [w.width(), w.height()]}


def principal():
    return wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)


def ventana_del_panel():
    """La ventana de primer nivel que contiene el panel (la de Maya o una flotante)."""
    p = M["interfaz"].ventana()
    return p.window() if p is not None else None


def panel():
    return M["interfaz"].ventana()


def controles():
    c = M["interfaz"].CONTROL
    v = M["visor"].CONTROL
    r = {}
    for nombre in (c, v):
        if cmds.workspaceControl(nombre, exists=True):
            r[nombre] = {"visible": cmds.workspaceControl(nombre, query=True, visible=True),
                         "flotante": cmds.workspaceControl(nombre, query=True, floating=True)}
        else:
            r[nombre] = None
    return r


def valores_escena():
    v, faltan = M["ajustes"].leer()
    return {"valores": v, "faltan": faltan}


# ---------- pasos ----------

@paso("escena")
def p_escena():
    cmds.file(new=True, force=True)
    if not cmds.pluginInfo("mtoa", query=True, loaded=True):
        cmds.loadPlugin("mtoa")
    import mtoa.core
    mtoa.core.createOptions()
    cmds.setAttr("defaultRenderGlobals.currentRenderer", "arnold", type="string")
    bola = cmds.polySphere(radius=4, name="bola")[0]
    cmds.move(0, 4, 0, bola)
    copa = cmds.polyCylinder(radius=2, height=6, name="vaso")[0]
    cmds.move(7, 3, 0, copa)
    cmds.polyPlane(width=60, height=60, name="suelo")
    vidrio = cmds.shadingNode("aiStandardSurface", asShader=True, name="vidrio_MAT")
    cmds.setAttr(vidrio + ".transmission", 1)
    cmds.setAttr(vidrio + ".specularRoughness", 0.05)
    cmds.select(copa)
    cmds.hyperShade(assign=vidrio)
    cmds.shadingNode("aiSkyDomeLight", asLight=True, name="cielo")
    cam = cmds.rename(cmds.camera()[0], "camara_prueba")
    cmds.viewPlace(cam, eye=(0, 10, 30), lookAt=(2, 3, 0), perspective=True)
    for c in cmds.ls(type="camera"):
        cmds.setAttr(c + ".renderable", c.startswith("camara_prueba"))
    cmds.setAttr("defaultResolution.width", 960)
    cmds.setAttr("defaultResolution.height", 540)
    cmds.setAttr("defaultResolution.deviceAspectRatio", 960 / 540.0)
    cmds.select(clear=True)
    return {"maya": cmds.about(version=True), "mtoa": cmds.pluginInfo("mtoa", query=True, version=True),
            "qt": QtCore.qVersion(), "espacio": cmds.workspaceLayoutManager(query=True, current=True),
            "espacios": cmds.workspaceLayoutManager(listLayouts=True)}


@paso("cargar_plugin")
def p_plugin():
    scripts = os.path.join(RAIZ, "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    cmds.loadPlugin(os.path.join(RAIZ, "plug-ins", "renderdesk_plugin.py"))
    return {"cargado": cmds.pluginInfo("renderdesk_plugin", query=True, loaded=True)}


@paso("abrir_panel")
def p_abrir():
    from renderdesk import espacio, interfaz_maya, maya_ajustes, modelo, presets, visor
    M.update(interfaz=interfaz_maya, visor=visor, ajustes=maya_ajustes, espacio=espacio, presets=presets,
             modelo=modelo)
    r = {"menu": cmds.menu(interfaz_maya.MENU, exists=True) or cmds.menuItem(interfaz_maya.MENU, exists=True),
         "ordenes": [n for n in interfaz_maya.COMANDOS if cmds.runTimeCommand(n, exists=True)]}
    interfaz_maya.mostrar()
    r["controles"] = controles()
    r["visor_controlable"] = visor.controlable()
    p = panel()
    r["chip"] = p.chip.text() if p else None
    r["camaras"] = [p.combo_camara.itemText(i) for i in range(p.combo_camara.count())] if p else None
    r["tamano"] = p.combo_tamano.currentText() if p else None
    r["captura_panel"] = captura(p, "f1_0_panel_escena.png")
    r["captura_ventana"] = captura(ventana_del_panel(), "f1_0_ventana.png")
    return r


@paso("elegir_preset")
def p_preset():
    p = panel()
    p.botones_calidad["revision"].click()
    p.botones_escena["interior"].click()
    p.casillas_extra["vidrio"].click()
    p.aplicar_pendiente()
    v = valores_escena()
    esperado = M["presets"].combinar("revision", "interior", ["vidrio"])
    distintos = {c: (v["valores"].get(c), esperado[c]) for c in esperado if v["valores"].get(c) != esperado[c]}
    return {"chip": p.chip.text(), "distintos": distintos, "hay_copia": M["ajustes"].hay_copia(),
            "seleccion": M["ajustes"].seleccion(), "captura": captura(p, "f1_1_sencillo.png")}


@paso("probar")
def p_probar():
    p = panel()
    p.boton_probar.click()
    return {"boton": p.boton_probar.text(), "camara_visor": M["visor"].camara(),
            "res_prueba": M["visor"].resolucion_prueba()}


@paso("probando")
def p_probando():
    p = panel()
    return {"probando": M["visor"].probando(), "estado": p.estado.text(), "controles": controles(),
            "captura": captura(ventana_del_panel(), "f1_2_probando.png")}


@paso("retocar_en_detalle")
def p_detalle():
    p = panel()
    p.poner_nivel("detalle")
    p.controles_detalle["diff"].caja.setValue(4)
    p.aplicar_pendiente()
    return {"GIDiffuseSamples": cmds.getAttr(M["ajustes"].OPCIONES + ".GIDiffuseSamples"),
            "chip": p.chip.text(), "probando": M["visor"].probando(),
            "captura": captura(p, "f1_3_detalle.png")}


@paso("experto")
def p_experto():
    p = panel()
    p.poner_nivel("experto")
    nombres = {c: e.text() for c, e in p.nombres_experto.items()}
    return {"nombres": nombres, "captura": captura(p, "f1_4_experto.png")}


@paso("region_e_instantanea")
def p_region():
    p = panel()
    p.boton_region.click()
    r = {"en_region": M["visor"].en_region()}
    p.boton_region.click()
    r["tras_quitar"] = M["visor"].en_region()
    p.boton_instantanea.click()
    r["instantanea"] = "sin error"
    r["guardar_imagen"] = M["visor"].guardar_imagen(os.path.join(SALIDA, "f1_visor_guardado.png"))
    return r


@paso("cambio_desde_fuera")
def p_fuera():
    cmds.setAttr(M["ajustes"].OPCIONES + ".GISpecularSamples", 5)
    return "puesto GISpecularSamples=5 desde fuera; se mira en el siguiente paso"


@paso("cambio_desde_fuera_visto")
def p_fuera_visto():
    p = panel()
    return {"cambios": dict(p.sel.cambios), "chip": p.chip.text()}


@paso("deshacer")
def p_deshacer():
    p = panel()
    p.poner_nivel("sencillo")
    antes = cmds.getAttr(M["ajustes"].OPCIONES + ".AASamples")
    p.botones_calidad["final"].click()
    p.aplicar_pendiente()
    con_final = cmds.getAttr(M["ajustes"].OPCIONES + ".AASamples")
    cmds.undo()
    return {"aa_antes": antes, "aa_final": con_final,
            "aa_tras_deshacer": cmds.getAttr(M["ajustes"].OPCIONES + ".AASamples")}


@paso("deshacer_visto")
def p_deshacer_visto():
    p = panel()
    return {"chip": p.chip.text(), "cambios": dict(p.sel.cambios), "calidad": p.sel.calidad}


@paso("camara_y_tamano")
def p_camara():
    p = panel()
    camaras = [p.combo_camara.itemText(i) for i in range(p.combo_camara.count())]
    i = camaras.index("persp")
    p.combo_camara.setCurrentIndex(i)
    p.combo_camara.activated.emit(i)
    renderizables = [cmds.listRelatives(c, parent=True)[0] for c in cmds.ls(type="camera")
                     if cmds.getAttr(c + ".renderable")]
    textos = [p.combo_tamano.itemText(k) for k in range(p.combo_tamano.count())]
    k = next(n for n, x in enumerate(textos) if x.startswith("HD 720"))
    p.combo_tamano.activated.emit(k)
    r = {"camaras": camaras, "renderizables": renderizables, "camara_visor": M["visor"].camara(),
         "resolucion": [cmds.getAttr("defaultResolution.width"), cmds.getAttr("defaultResolution.height")],
         "tamano": p.combo_tamano.currentText()}
    i = camaras.index("camara_prueba")
    p.combo_camara.setCurrentIndex(i)
    p.combo_camara.activated.emit(i)
    r["camara_visor_despues"] = M["visor"].camara()
    return r


@paso("entrar_modo_render")
def p_modo():
    INFORME["espacio_antes"] = M["espacio"].actual()
    panel().boton_modo.click()
    return {"espacio_antes": INFORME["espacio_antes"]}


@paso("en_modo_render")
def p_en_modo():
    p = panel()
    return {"espacio": M["espacio"].actual(), "activo": M["espacio"].activo(),
            "espacios": cmds.workspaceLayoutManager(listLayouts=True), "controles": controles(),
            "panel_vivo": p is not None, "boton": p.boton_modo.text() if p else None,
            "probando": M["visor"].probando(), "captura": captura(principal(), "f1_5_modo_render.png")}


@paso("salir_modo_render")
def p_salir():
    p = panel()
    if p is not None:
        p.boton_modo.click()
    else:
        M["interfaz"].modo_render(False)
    return "pedido"


@paso("fuera_de_modo_render")
def p_fuera_modo():
    return {"espacio": M["espacio"].actual(), "esperado": INFORME.get("espacio_antes"),
            "controles": controles(), "panel_vivo": panel() is not None,
            "captura": captura(principal(), "f1_6_vuelta.png")}


@paso("volver_a_entrar")
def p_otra_vez():
    M["interfaz"].modo_render(True)
    return "pedido"


@paso("otra_vez_dentro")
def p_otra_vez_dentro():
    return {"espacio": M["espacio"].actual(), "controles": controles(),
            "captura": captura(principal(), "f1_7_modo_render_2.png")}


@paso("restaurar")
def p_restaurar():
    M["visor"].probar(False)
    M["interfaz"].modo_render(False)
    p = panel()
    copia = M["ajustes"]._datos().get("copia")
    p.boton_restaurar.click()
    v = valores_escena()["valores"]
    distintos = {c: (v.get(c), copia[c]) for c in copia if v.get(c) != copia[c]}
    return {"distintos_de_la_copia": distintos, "chip": p.chip.text(), "hay_copia": M["ajustes"].hay_copia(),
            "captura": captura(p, "f1_8_restaurado.png")}


@paso("descargar_plugin")
def p_descargar():
    cmds.unloadPlugin("renderdesk_plugin", force=True)
    return {"controles": controles(), "menu": cmds.menu("RenderDeskMenu", exists=True)}


def fin():
    INFORME["fin"] = True
    guardar()
    print("RENDERDESK PRUEBA FIN", SALIDA)
    if CERRAR:
        cmds.quit(force=True)


PLAN = [(0, p_escena), (1000, p_plugin), (3000, p_abrir), (6000, p_preset), (8000, p_probar),
        (16000, p_probando), (18000, p_detalle), (22000, p_experto), (23000, p_region), (26000, p_fuera),
        (29000, p_fuera_visto), (30000, p_deshacer), (33000, p_deshacer_visto), (34000, p_camara),
        (37000, p_modo), (43000, p_en_modo), (45000, p_salir), (50000, p_fuera_modo), (52000, p_otra_vez),
        (57000, p_otra_vez_dentro), (59000, p_restaurar), (64000, p_descargar), (66000, fin)]
for ms, fn in PLAN:
    QtCore.QTimer.singleShot(8000 + ms, fn)       # margen para que Maya termine de arrancar
print("RENDERDESK PRUEBA programada; resultados en", SALIDA)
