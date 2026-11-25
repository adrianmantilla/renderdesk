"""Fase 0: mide los presets con renders reales de Arnold (herramienta de desarrollo).

    mayapy herramientas/medir_presets.py /ruta/de/salida [ancho]

Construye una escena de prueba difícil (interior con ventana, vidrio, piel,
cromo y hojas recortadas), la renderiza con varias combinaciones y deja:

* un PNG por combinación;
* informe.json con tiempos, ajustes aplicados, atributos que faltan y
  datos de la instalación de Arnold (versión, atributos, tipos de imager);
* el resultado de comprobar aplicar / leer / restaurar.
"""

import glob
import json
import os
import sys
import time
import traceback

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

EXTRAS_PRUEBA = ["vidrio", "sss", "hojas"]
COMBINACIONES = [
    # nombre, calidad, cambios encima
    ("fabrica", None, {}),
    ("borrador", "borrador", {}),
    ("revision", "revision", {}),
    ("final", "final", {}),
    ("final_oidn", "final", {"den": 1}),
]


def iniciar():
    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds
    if not cmds.pluginInfo("mtoa", query=True, loaded=True):
        cmds.loadPlugin("mtoa")
    return cmds


def material(cmds, nombre, **valores):
    m = cmds.shadingNode("aiStandardSurface", asShader=True, name=nombre)
    for attr, v in valores.items():
        if isinstance(v, (tuple, list)):
            cmds.setAttr("{}.{}".format(m, attr), *v, type="double3")
        else:
            cmds.setAttr("{}.{}".format(m, attr), v)
    grupo = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=nombre + "SG")
    cmds.connectAttr(m + ".outColor", grupo + ".surfaceShader")
    return m, grupo


def asignar(cmds, objetos, grupo):
    cmds.sets(objetos, edit=True, forceElement=grupo)


def caja(cmds, nombre, tam, pos):
    c = cmds.polyCube(width=tam[0], height=tam[1], depth=tam[2], name=nombre)[0]
    cmds.move(pos[0], pos[1], pos[2], c)
    return c


def escena_prueba(cmds):
    """Habitación de 4 × 3 m con ventana a la izquierda y un bodegón sobre una mesa."""
    cmds.file(new=True, force=True)
    _, pared = material(cmds, "pared", baseColor=(0.75, 0.72, 0.68), specular=0.2, specularRoughness=0.6)
    _, suelo_m = material(cmds, "suelo_madera", baseColor=(0.35, 0.22, 0.13), specularRoughness=0.35)
    _, vidrio = material(cmds, "vidrio", baseColor=(1, 1, 1), transmission=1.0, specularRoughness=0.0,
                         specularIOR=1.5)
    _, piel = material(cmds, "cera", baseColor=(0.9, 0.6, 0.45), subsurface=1.0,
                       subsurfaceColor=(0.95, 0.55, 0.4), subsurfaceRadius=(1.0, 0.4, 0.2), subsurfaceScale=3.0)
    _, cromo = material(cmds, "metal_cepillado", baseColor=(0.9, 0.9, 0.9), metalness=1.0, specularRoughness=0.3)
    hoja_m, hoja = material(cmds, "hoja", baseColor=(0.2, 0.45, 0.12), specularRoughness=0.5,
                            thinWalled=1, subsurface=0.3)
    # opacidad recortada con un damero
    damero = cmds.shadingNode("checker", asTexture=True, name="recorte_hojas")
    lugar = cmds.shadingNode("place2dTexture", asUtility=True)
    cmds.connectAttr(lugar + ".outUV", damero + ".uv")
    cmds.connectAttr(lugar + ".outUvFilterSize", damero + ".uvFilterSize")
    cmds.setAttr(lugar + ".repeatU", 4)
    cmds.setAttr(lugar + ".repeatV", 4)
    cmds.connectAttr(damero + ".outColor", hoja_m + ".opacity")

    piezas = [caja(cmds, "suelo", (400, 4, 400), (0, -2, 0)),
              caja(cmds, "techo", (400, 4, 400), (0, 302, 0)),
              caja(cmds, "fondo", (400, 300, 4), (0, 150, -202)),
              caja(cmds, "derecha", (4, 300, 400), (202, 150, 0)),
              # pared izquierda con hueco de ventana entre z -80..80 y y 90..230
              caja(cmds, "izq_a", (4, 300, 120), (-202, 150, -140)),
              caja(cmds, "izq_b", (4, 300, 120), (-202, 150, 140)),
              caja(cmds, "izq_c", (4, 90, 160), (-202, 45, 0)),
              caja(cmds, "izq_d", (4, 70, 160), (-202, 265, 0))]
    asignar(cmds, piezas[1:], pared)
    asignar(cmds, piezas[0], suelo_m)
    mesa = caja(cmds, "mesa", (160, 75, 90), (20, 37.5, -60))
    asignar(cmds, mesa, suelo_m)

    def esfera(nombre, r, x, z, grupo):
        e = cmds.polySphere(radius=r, subdivisionsX=48, subdivisionsY=32, name=nombre)[0]
        cmds.move(x, 75 + r, z, e)
        asignar(cmds, e, grupo)
        return e
    esfera("copa", 16, -30, -50, vidrio)
    esfera("vela", 14, 10, -70, piel)
    esfera("cromo", 13, 45, -45, cromo)
    hojas = []
    for i in range(5):                    # hojas apiladas: pone a prueba las capas de transparencia
        p = cmds.polyPlane(width=50, height=50, subdivisionsX=1, subdivisionsY=1, name="hoja{}".format(i))[0]
        cmds.rotate(90, 0, 0, p)
        cmds.move(-80 + i * 6, 110, -120 + i * 8, p)
        forma = cmds.listRelatives(p, shapes=True)[0]
        cmds.setAttr(forma + ".aiOpaque", 0)
        hojas.append(p)
    asignar(cmds, hojas, hoja)

    cielo = cmds.shadingNode("aiSkyDomeLight", asLight=True, name="cielo")
    cmds.setAttr(cmds.listRelatives(cielo, shapes=True)[0] + ".color", 0.7, 0.82, 1.0, type="double3")
    sol = cmds.listRelatives(cmds.directionalLight(name="solShape", intensity=4.0), parent=True)[0]
    cmds.rotate(-35, -70, 0, sol)
    cmds.setAttr(cmds.listRelatives(sol, shapes=True)[0] + ".aiAngle", 0.5)

    camara = cmds.rename(cmds.camera()[0], "camara_prueba")
    cmds.viewPlace(camara, eye=(60, 140, 190), lookAt=(0, 95, -60), perspective=True)
    cmds.camera(camara, edit=True, horizontalFieldOfView=55)
    for c in cmds.ls(type="camera"):
        cmds.setAttr(c + ".renderable", 0)
    cmds.setAttr(cmds.listRelatives(camara, shapes=True)[0] + ".renderable", 1)
    return camara


def salida_png(cmds):
    cmds.setAttr("defaultArnoldDriver.ai_translator", "png", type="string")
    for ajuste in (dict(outputTransformEnabled=True), dict(outputUseViewTransform=True)):
        try:
            cmds.colorManagementPrefs(edit=True, **ajuste)
        except (RuntimeError, TypeError):
            pass
    if cmds.attributeQuery("abortOnLicenseFail", node="defaultArnoldRenderOptions", exists=True):
        cmds.setAttr("defaultArnoldRenderOptions.abortOnLicenseFail", 0)


def render(cmds, base, camara, ancho, alto):
    cmds.setAttr("defaultRenderGlobals.imageFilePrefix", base, type="string")
    cmds.setAttr("defaultResolution.width", ancho)
    cmds.setAttr("defaultResolution.height", alto)
    cmds.setAttr("defaultResolution.deviceAspectRatio", ancho / float(alto))
    inicio = time.time()
    cmds.arnoldRender(width=ancho, height=alto, camera=camara, batch=True)
    segundos = time.time() - inicio
    raiz = cmds.workspace(query=True, rootDirectory=True) or ""
    hechas = [r for r in glob.glob(base + "*.png") + glob.glob(os.path.join(raiz, "images", "**", "*.png"),
                                                                recursive=True) if os.path.getmtime(r) >= inicio - 1]
    return segundos, (sorted(hechas, key=os.path.getmtime)[-1] if hechas else None)


def datos_instalacion(cmds):
    from renderdesk import maya_ajustes, presets
    info = {"maya": cmds.about(version=True), "mtoa": cmds.pluginInfo("mtoa", query=True, version=True)}
    try:
        import arnold
        info["arnold"] = arnold.AiGetVersionString()
    except Exception as e:  # noqa: BLE001
        info["arnold"] = "?? " + str(e)
    info["atributos_opciones"] = sorted(cmds.listAttr(maya_ajustes.OPCIONES) or [])
    info["atributos_driver"] = sorted(cmds.listAttr(maya_ajustes.DRIVER) or [])
    info["tipos_imager"] = sorted(t for t in (cmds.allNodeTypes() or []) if t.lower().startswith("aiimager"))
    info["claves_resueltas"] = {c: maya_ajustes.atributo(c) for c, d in presets.catalogo().items()
                                if not d.get("especial")}
    info["oidn_conexiones"] = maya_ajustes.donde_oidn()
    info["atributos_imager_opciones"] = [a for a in (cmds.listAttr(maya_ajustes.OPCIONES) or []) if "imager" in a.lower()]
    leidos, faltan = maya_ajustes.leer()
    info["valores_de_fabrica_leidos"] = leidos
    info["faltan"] = faltan
    return info


def comprobar_aplicar(cmds):
    """aplicar -> leer -> restaurar, sobre una escena vacía."""
    from renderdesk import maya_ajustes, presets
    cmds.file(new=True, force=True)
    maya_ajustes.preparar()
    antes, _ = maya_ajustes.leer()
    v = presets.combinar("final", "interior", ["vidrio"], cambios={"den": 1})
    cambiados, saltados = maya_ajustes.aplicar(v, etiqueta="Final · Interior")
    leidos, _ = maya_ajustes.leer()
    distintos = {c: (v[c], leidos.get(c)) for c in v if c not in saltados and leidos.get(c) != v[c]}
    restaurado = maya_ajustes.restaurar()
    despues, _ = maya_ajustes.leer()
    vuelta = {c: (antes[c], despues.get(c)) for c in antes if despues.get(c) != antes[c]}
    return {"cambiados": len(cambiados), "saltados": saltados, "no_coinciden_al_leer": distintos,
            "restaurado": restaurado, "no_vuelven_al_restaurar": vuelta,
            "ok": not distintos and restaurado and not vuelta}


def main():
    carpeta = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "medidas")
    ancho = int(sys.argv[2]) if len(sys.argv) > 2 else 960
    alto = int(round(ancho * 9 / 16.0))
    os.makedirs(carpeta, exist_ok=True)
    informe = {"ancho": ancho, "alto": alto, "extras": EXTRAS_PRUEBA, "renders": []}
    cmds = iniciar()
    from renderdesk import coste, maya_ajustes, presets
    try:
        maya_ajustes.preparar()
        informe["instalacion"] = datos_instalacion(cmds)
    except Exception:  # noqa: BLE001
        informe["error_instalacion"] = traceback.format_exc()
    try:
        informe["aplicar_restaurar"] = comprobar_aplicar(cmds)
    except Exception:  # noqa: BLE001
        informe["aplicar_restaurar"] = {"ok": False, "error": traceback.format_exc()}

    for nombre, calidad, cambios in COMBINACIONES:
        registro = {"nombre": nombre}
        try:
            camara = escena_prueba(cmds)
            maya_ajustes.preparar()
            salida_png(cmds)
            if calidad:
                v = presets.combinar(calidad, "interior", EXTRAS_PRUEBA, cambios=cambios)
            else:
                v = presets.fabrica()
            _, saltados = maya_ajustes.aplicar(v, guardar_copia=False)
            escala = v.get("res", 100) / 100.0
            segundos, imagen = render(cmds, os.path.join(carpeta, "rd_" + nombre), camara,
                                      int(ancho * escala), int(alto * escala))
            registro.update(segundos=round(segundos, 1), imagen=imagen, saltados=saltados, valores=v,
                            coste_estimado=round(coste.coste_relativo(v, EXTRAS_PRUEBA, "interior"), 1))
        except Exception:  # noqa: BLE001
            registro["error"] = traceback.format_exc()
        informe["renders"].append(registro)
        with open(os.path.join(carpeta, "informe.json"), "w", encoding="utf-8") as f:
            json.dump(informe, f, ensure_ascii=False, indent=1, default=str)
        print("RENDERDESK", nombre, registro.get("segundos"), registro.get("error", "")[-300:])
    print("RENDERDESK FIN", os.path.join(carpeta, "informe.json"))


if __name__ == "__main__":
    main()
