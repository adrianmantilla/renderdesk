"""Fase 2: prueba del historial, la pestaña Salida y el render final dentro de Maya (herramienta de desarrollo).

Se lanza igual que ``prueba_panel.py``, con preferencias de Maya aparte:

    export MAYA_APP_DIR=/carpeta/prefs_de_prueba RENDERDESK_SALIDA=/carpeta/salida
    maya -command "python(\\"exec(open('/ruta/herramientas/prueba_fase2.py').read())\\")"

Crea un proyecto y una escena de prueba en RENDERDESK_SALIDA, prueba con el visor de
Arnold, guarda instantáneas, compara y recupera, prepara un giro de 120 fotogramas
con su cámara y lo lanza en segundo plano mientras sigue trabajando en la escena.
Guarda capturas e ``informe_fase2.json`` y cierra Maya si RENDERDESK_CERRAR=1.
"""

import glob
import json
import os
import sys
import time
import traceback

from maya import cmds
import maya.OpenMayaUI as omui

try:
    from PySide6 import QtCore, QtGui, QtWidgets
    from shiboken6 import wrapInstance
except ImportError:                                   # Maya 2024 y anteriores
    from PySide2 import QtCore, QtGui, QtWidgets
    from shiboken2 import wrapInstance

RAIZ = os.environ.get("RENDERDESK_RAIZ") or os.path.dirname(os.path.dirname(os.path.abspath(
    globals().get("__file__", os.path.join(os.getcwd(), "herramientas", "x.py")))))
SALIDA = os.environ.get("RENDERDESK_SALIDA", os.path.expanduser("~/renderdesk_prueba_fase2"))
CERRAR = os.environ.get("RENDERDESK_CERRAR", "1") == "1"
ESPERA_RENDER_S = int(os.environ.get("RENDERDESK_ESPERA_RENDER", "420"))
PROYECTO = os.path.join(SALIDA, "proyecto")
os.makedirs(SALIDA, exist_ok=True)
INFORME = {"raiz": RAIZ, "pasos": []}
M = {}
OTRA_VEZ = "otra_vez"


def guardar():
    with open(os.path.join(SALIDA, "informe_fase2.json"), "w", encoding="utf-8") as f:
        json.dump(INFORME, f, ensure_ascii=False, indent=1, default=str)


def paso(nombre):
    def deco(fn):
        def envuelta():
            r = {"paso": nombre, "t": round(time.time() - INFORME.get("t0", time.time()), 1)}
            try:
                r["resultado"] = fn()
                r["ok"] = True
            except Exception:  # noqa: BLE001
                r["ok"] = False
                r["error"] = traceback.format_exc()[-2000:]
            if r.get("resultado") == OTRA_VEZ:
                return OTRA_VEZ
            INFORME["pasos"].append(r)
            guardar()
            print("RENDERDESK PRUEBA", nombre, "OK" if r["ok"] else "FALLO")
            return None
        return envuelta
    return deco


def captura(w, archivo):
    if w is None:
        return "sin widget"
    ruta = os.path.join(SALIDA, archivo)
    return {"archivo": archivo, "guardado": w.grab().save(ruta), "tam": [w.width(), w.height()]}


def principal():
    return wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)


def panel():
    return M["interfaz"].ventana()


def opcion(nombre):
    plug = "defaultArnoldRenderOptions." + nombre
    return cmds.getAttr(plug) if cmds.objExists(plug) else "no existe"


def imagen_info(ruta):
    """Tamaño y si la imagen tiene algo (no es de un solo color)."""
    if not ruta or not os.path.isfile(ruta):
        return {"existe": False}
    img = QtGui.QImage(ruta)
    if img.isNull():
        return {"existe": True, "bytes": os.path.getsize(ruta), "legible": False}
    colores = set()
    for x in range(0, img.width(), max(1, img.width() // 12)):
        for y in range(0, img.height(), max(1, img.height() // 12)):
            colores.add(img.pixel(x, y))
    return {"existe": True, "tam": [img.width(), img.height()], "colores_muestreados": len(colores)}


# ---------- pasos ----------

@paso("escena")
def p_escena():
    INFORME["t0"] = time.time()
    cmds.scriptEditorInfo(historyFilename=os.path.join(SALIDA, "script_editor.txt"), writeHistory=True)
    os.makedirs(os.path.join(PROYECTO, "scenes"), exist_ok=True)
    cmds.workspace(PROYECTO, openWorkspace=True)
    cmds.workspace(fileRule=["images", "images"])
    cmds.workspace(fileRule=["scene", "scenes"])
    cmds.workspace(saveWorkspace=True)
    cmds.file(new=True, force=True)
    if not cmds.pluginInfo("mtoa", query=True, loaded=True):
        cmds.loadPlugin("mtoa")
    import mtoa.core
    mtoa.core.createOptions()
    cmds.setAttr("defaultRenderGlobals.currentRenderer", "arnold", type="string")
    tetera = cmds.polyTorus(radius=3, sectionRadius=1.2, name="aro")[0]
    cmds.move(0, 3.5, 0, tetera)
    cmds.rotate(70, 20, 0, tetera)
    caja = cmds.polyCube(width=2.5, height=2.5, depth=2.5, name="caja")[0]
    cmds.move(4, 1.25, 1, caja)
    cmds.polyPlane(width=40, height=40, name="suelo")
    rojo = cmds.shadingNode("aiStandardSurface", asShader=True, name="rojo_MAT")
    cmds.setAttr(rojo + ".baseColor", 0.8, 0.15, 0.1, type="double3")
    cmds.select(tetera)
    cmds.hyperShade(assign=rojo)
    cmds.shadingNode("aiSkyDomeLight", asLight=True, name="cielo")
    luz = cmds.shadingNode("aiAreaLight", asLight=True, name="clave")
    cmds.setAttr(luz + ".intensity", 8)
    cmds.setAttr(luz + ".aiExposure", 6)
    cmds.xform(luz, translation=(6, 10, 6), rotation=(-50, 45, 0), scale=(4, 4, 4))
    cam = cmds.rename(cmds.camera()[0], "camara_prueba")
    cmds.viewPlace(cam, eye=(0, 9, 22), lookAt=(1, 2.5, 0), perspective=True)
    for c in cmds.ls(type="camera"):
        cmds.setAttr(c + ".renderable", c.startswith("camara_prueba"))
    cmds.setAttr("defaultResolution.width", 960)
    cmds.setAttr("defaultResolution.height", 540)
    cmds.setAttr("defaultResolution.deviceAspectRatio", 960 / 540.0)
    cmds.select(clear=True)
    escena = os.path.join(PROYECTO, "scenes", "giro_prueba.ma")
    cmds.file(rename=escena)
    cmds.file(save=True, type="mayaAscii", force=True)
    return {"maya": cmds.about(version=True), "mtoa": cmds.pluginInfo("mtoa", query=True, version=True),
            "proyecto": cmds.workspace(query=True, rootDirectory=True), "escena": cmds.file(query=True, sceneName=True),
            "MAYA_LOCATION": os.environ.get("MAYA_LOCATION"), "cpu": os.cpu_count(),
            "opciones": {n: opcion(n) for n in ("autotx", "use_existing_tiled_textures", "threads_autodetect",
                                                "threads", "lock_sampling_noise")}}


@paso("cargar_y_abrir")
def p_abrir():
    scripts = os.path.join(RAIZ, "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    cmds.loadPlugin(os.path.join(RAIZ, "plug-ins", "renderdesk_plugin.py"))
    from renderdesk import interfaz_maya, maya_ajustes, presets, salida, visor
    M.update(interfaz=interfaz_maya, visor=visor, ajustes=maya_ajustes, presets=presets, salida=salida)
    interfaz_maya.mostrar()
    p = panel()
    s = p.servicios
    return {"panel": p is not None, "carpeta_historial": s.carpeta_historial(), "nombre_escena": s.nombre_escena(),
            "salida": s.salida(), "ruta_imagenes": s.ruta_imagenes(), "render_exe": s._render_exe(),
            "render_exe_existe": os.path.isfile(s._render_exe()), "historial_vacio": p.tira.vacio.isVisible(),
            "captura": captura(p, "f2_0_panel.png")}


@paso("probar_borrador")
def p_probar():
    p = panel()
    tiempos = {}
    t = time.time()
    p.botones_calidad["borrador"].click()
    p.aplicar_pendiente()
    tiempos["preset"] = round(time.time() - t, 2)
    s = p.servicios
    originales = {}
    for nombre in ("abrir_visor", "probar", "poner_camara"):
        originales[nombre] = getattr(s, nombre)

        def medido(*a, _n=nombre, **k):
            t0 = time.time()
            try:
                return originales[_n](*a, **k)
            finally:
                tiempos.setdefault(_n, []).append(round(time.time() - t0, 2))
        setattr(s, nombre, medido)
    t = time.time()
    p.boton_probar.click()
    tiempos["boton_probar"] = round(time.time() - t, 2)
    for nombre, fn in originales.items():
        setattr(s, nombre, fn)
    return {"probando": M["visor"].probando(), "aa": opcion("AASamples"), "tiempos": tiempos}


@paso("instantanea_1")
def p_inst1():
    p = panel()
    e = p.instantanea()
    return {"entrada": {k: e.get(k) for k in ("numero", "segundos", "preset", "camara", "tamano", "imagen", "region")},
            "imagen": imagen_info(e.get("ruta_imagen")), "lista": p.tira.lista.count(),
            "json": os.path.isfile(p.historial().ruta_datos(e["numero"]))}


@paso("revision")
def p_revision():
    p = panel()
    p.botones_calidad["revision"].click()
    p.aplicar_pendiente()
    return {"aa": opcion("AASamples"), "probando": M["visor"].probando()}


@paso("instantanea_2")
def p_inst2():
    p = panel()
    e = p.instantanea()
    return {"entrada": {k: e.get(k) for k in ("numero", "segundos", "preset")},
            "imagen": imagen_info(e.get("ruta_imagen")), "lista": p.tira.lista.count(),
            "estimado": p.pestana_salida.estimado.text(), "captura": captura(p, "f2_1_historial.png")}


@paso("comparar")
def p_comparar():
    p = panel()
    entradas = p.historial().entradas()
    dos = p._al_comparar(entradas[:2])
    QtWidgets.QApplication.processEvents()
    r = {"dos": [dos.vista.texto_a, dos.vista.texto_b, dos.vista.a.isNull(), dos.vista.b.isNull()],
         "captura_dos": captura(dos, "f2_2_comparar.png")}
    dos.close()
    uno = p._al_comparar(entradas[:1])
    QtWidgets.QApplication.processEvents()
    r["con_ahora"] = [uno.vista.texto_a, uno.vista.texto_b, uno.vista.b.isNull(),
                      imagen_info(os.path.join(p.servicios.carpeta_historial(), "ahora.png"))]
    uno.close()
    return r


@paso("recuperar_1")
def p_recuperar():
    p = panel()
    primera = [e for e in p.historial().entradas() if e["numero"] == 1][0]
    p._al_recuperar(primera)
    return {"chip": p.chip.text(), "aa": opcion("AASamples"),
            "aa_borrador": M["presets"].combinar("borrador")["aa"],
            "estado": p.estado.text(), "probando": M["visor"].probando()}


@paso("parar_prueba")
def p_parar():
    p = panel()
    if p.boton_probar.isChecked():
        p.boton_probar.click()
    return {"probando": M["visor"].probando()}


@paso("salida_giro")
def p_giro():
    p = panel()
    p.pestanas.setCurrentIndex(1)
    ps = p.pestana_salida
    ps.botones_que["giro"].click()
    p.aplicar_pendiente()
    g = "defaultRenderGlobals."
    r = {"que": ps.que, "sel_salida": p.sel.salida, "lock": opcion("lock_sampling_noise"),
         "globales": {a: cmds.getAttr(g + a) for a in ("animation", "startFrame", "endFrame", "outFormatControl",
                                                         "putFrameBeforeExt", "periodInExt", "extensionPadding")},
         "prefijo": cmds.getAttr(g + "imageFilePrefix"), "ejemplo": ps.ejemplo.text()}
    cmds.select("aro")
    ps.boton_giro.click()
    camara = p.servicios.camara()
    r["camara"] = camara
    r["texto_giro"] = ps.texto_giro.text()
    r["claves"] = cmds.keyframe("renderDesk_giro", attribute="rotateY", query=True, valueChange=True, timeChange=True)
    r["renderizables"] = [cmds.listRelatives(c, parent=True)[0] for c in cmds.ls(type="camera")
                          if cmds.getAttr(c + ".renderable")]
    r["combo_camara"] = p.combo_camara.currentText()
    cmds.select(clear=True)
    return r


@paso("salida_formato_y_aov")
def p_aov():
    p = panel()
    ps = p.pestana_salida
    r = {}
    ps.botones_aov["composicion"].click()
    r["composicion"] = p.servicios.salida()["aovs"]
    r["aviso_png"] = ps.aviso_aov.isVisible()
    ps.botones_formato["exr"].click()
    r["exr"] = cmds.getAttr("defaultArnoldDriver.aiTranslator")
    r["captura"] = captura(p, "f2_3_salida.png")
    ps.botones_aov["basico"].click()
    r["basico"] = p.servicios.salida()["aovs"]
    ps.botones_aov["ninguno"].click()
    r["ninguno"] = p.servicios.salida()["aovs"]
    ps.botones_formato["png"].click()
    r["png"] = cmds.getAttr("defaultArnoldDriver.aiTranslator")
    antes = (opcion("autotx"), opcion("use_existing_tiled_textures"))
    ps.casilla_autotx.click()
    r["autotx"] = [antes[0], opcion("autotx")]
    ps.casilla_autotx.click()
    r["usar_tx"] = antes[1]
    r["casillas_activas"] = [ps.casilla_autotx.isEnabled(), ps.casilla_usar_tx.isEnabled()]
    i = ps.combo_nombre.findData("camara")
    ps.combo_nombre.setCurrentIndex(i)
    ps._al_nombre(i)
    r["prefijo_camara"] = cmds.getAttr("defaultRenderGlobals.imageFilePrefix")
    i = ps.combo_nombre.findData("escena_camara")
    ps.combo_nombre.setCurrentIndex(i)
    ps._al_nombre(i)
    r["ejemplo"] = ps.ejemplo.text()
    return r


@paso("lanzar_giro_120")
def p_lanzar():
    p = panel()
    p.botones_calidad["borrador"].click()
    p.aplicar_pendiente()
    p.servicios.poner_resolucion(320, 180)           # pequeño: la prueba es del lanzamiento, no de la calidad
    p._refrescar_barra()
    cmds.file(save=True, force=True)
    modificada_antes = cmds.file(query=True, modified=True)
    hilos_antes = (opcion("threads_autodetect"), opcion("threads"))
    lanz = p._al_render_final()
    INFORME["lanzado_en"] = time.time()
    INFORME["progreso"] = []
    copia = lanz.comando[-1] if lanz else ""
    hilos_copia = []
    if copia and os.path.isfile(copia):
        with open(copia, encoding="utf-8", errors="replace") as f:
            hilos_copia = [l.strip() for l in f if '".thr' in l or "thread" in l][:8]
    return {"lanzado": lanz is not None, "comando": lanz.comando if lanz else None,
            "en_marcha": p.render_en_marcha(), "total": lanz.total if lanz else None,
            "copia": copia, "copia_bytes": os.path.getsize(copia) if copia and os.path.isfile(copia) else 0,
            "lineas_hilos_en_copia": hilos_copia, "hilos_escena_antes": hilos_antes,
            "hilos_escena_despues": (opcion("threads_autodetect"), opcion("threads")),
            "modificada_antes": modificada_antes, "modificada_despues": cmds.file(query=True, modified=True),
            "boton_final": p.pestana_salida.boton_final.text(), "estimado": p.pestana_salida.estimado.text()}


@paso("seguir_trabajando")
def p_trabajar():
    """Mientras renderiza: se mueve, crea y prueba en la escena, y se mide cuánto responde Maya."""
    p = panel()
    t0 = time.time()
    esfera = cmds.polySphere(radius=1, name="esfera_nueva")[0]
    for i in range(20):
        cmds.move(i * 0.2, 1, -3, esfera)
        cmds.refresh()
    p.botones_calidad["revision"].click()
    p.aplicar_pendiente()
    p.botones_calidad["borrador"].click()
    p.aplicar_pendiente()
    duracion = time.time() - t0
    return {"operaciones_s": round(duracion, 2), "en_marcha": p.render_en_marcha(),
            "texto": p.tarjeta_render.texto.text(), "captura": captura(principal(), "f2_4_renderizando.png")}


@paso("esperar_render")
def p_esperar():
    p = panel()
    lanz = p.lanzamiento
    ahora = time.time() - INFORME["lanzado_en"]
    marca = {"s": round(ahora), "hechos": lanz.hechos, "pct": lanz.porcentaje,
             "restante": round(lanz.restante() or 0), "texto": p.tarjeta_render.texto.text()}
    if not INFORME["progreso"] or INFORME["progreso"][-1]["hechos"] != lanz.hechos or ahora - INFORME[
            "progreso"][-1]["s"] > 30:
        INFORME["progreso"].append(marca)
        guardar()
    if len(INFORME["progreso"]) == 3 and not INFORME.get("captura_media"):
        INFORME["captura_media"] = captura(p, "f2_5_progreso.png")
    if p.render_en_marcha() and ahora < ESPERA_RENDER_S:
        return OTRA_VEZ
    if p.render_en_marcha():
        p._al_cancelar_render()
        return {"aviso": "no terminó a tiempo; cancelado", "hechos": lanz.hechos}
    return "terminado"


@paso("render_terminado")
def p_terminado():
    p = panel()
    lanz = p.lanzamiento
    imagenes = sorted(glob.glob(os.path.join(lanz.carpeta, "**", "*" + lanz.extension), recursive=True))
    nuevas = [i for i in imagenes if os.path.getmtime(i) >= INFORME["lanzado_en"] - 1]
    return {"hechos": lanz.hechos, "total": lanz.total, "segundos": round(lanz.segundos(), 1),
            "titulo": p.tarjeta_render.titulo.text(), "texto": p.tarjeta_render.texto.text(),
            "imagenes": len(nuevas), "primera": nuevas[0] if nuevas else None,
            "ultima": nuevas[-1] if nuevas else None,
            "muestra": [imagen_info(nuevas[i]) for i in (0, len(nuevas) // 2) if nuevas],
            "registro_cola": lanz.lineas[-25:], "lineas_pct": sum(1 for l in lanz.lineas if "% done" in l),
            "boton_final": p.pestana_salida.boton_final.isEnabled(),
            "captura": captura(p, "f2_6_terminado.png")}


@paso("descargar_plugin")
def p_descargar():
    cmds.unloadPlugin("renderdesk_plugin", force=True)
    return {"menu": cmds.menu("RenderDeskMenu", exists=True)}


def fin():
    INFORME["fin"] = True
    guardar()
    print("RENDERDESK PRUEBA FIN", SALIDA)
    if CERRAR:
        cmds.file(modified=False)
        cmds.quit(force=True)


PLAN = [(8000, p_escena), (1000, p_abrir), (3000, p_probar), (12000, p_inst1), (1000, p_revision),
        (12000, p_inst2), (1000, p_comparar), (1000, p_recuperar), (3000, p_parar), (1000, p_giro),
        (1000, p_aov), (1000, p_lanzar), (4000, p_trabajar), (5000, p_esperar), (1000, p_terminado),
        (2000, p_descargar), (1000, fin)]


def _lanzar(i=0, espera=None):
    if i >= len(PLAN):
        return
    pausa, fn = PLAN[i]

    def correr():
        if fn() == OTRA_VEZ:
            _lanzar(i, 5000)
        else:
            _lanzar(i + 1)
    QtCore.QTimer.singleShot(pausa if espera is None else espera, correr)


_lanzar()
print("RENDERDESK PRUEBA FASE 2 programada; resultados en", SALIDA)
