"""Servicios del panel sobre la escena de Maya (cámaras, tamaño, ajustes y visor).

El panel no llama a Maya directamente: todo pasa por aquí, y las pruebas sin
Maya usan ``panel.Servicios`` en su lugar.
"""

import os
import sys
import time

from maya import cmds, mel

from . import maya_ajustes, presets, salida, visor
from .historial import nombre_seguro

PREFIJO_PREFERENCIA = "renderDesk_"
GLOBALES = "defaultRenderGlobals"
GRUPO_GIRO = "renderDesk_giro"
# Atributos de las opciones de Arnold que usa la pestaña Salida (de más nuevo a más antiguo).
ATRIBUTOS_SALIDA = {
    "autotx": ("autotx", "autoTx"),
    "usar_tx": ("use_existing_tiled_textures", "useExistingTiledTextures"),
    "hilos_auto": ("threads_autodetect", "threadsAutodetect"),
    "hilos": ("threads",),
}


class _Deshacer(object):
    """Agrupa varios setAttr en un solo paso de Ctrl+Z."""

    def __init__(self, nombre):
        self.nombre = nombre

    def __enter__(self):
        cmds.undoInfo(openChunk=True, chunkName=self.nombre)

    def __exit__(self, *args):
        cmds.undoInfo(closeChunk=True)
        return False


class ServiciosMaya(object):
    en_maya = True

    # ----- ajustes de render -----

    def preparar(self):
        try:
            maya_ajustes.preparar()
            return True
        except RuntimeError:
            return False

    def leer(self):
        if not cmds.objExists(maya_ajustes.OPCIONES):
            return presets.fabrica(), []
        return maya_ajustes.leer()

    def aplicar(self, valores, etiqueta="", seleccion=None):
        """Escribe los valores y lo elegido en el panel en un solo paso de Ctrl+Z."""
        with _Deshacer("RenderDesk"):
            resultado = maya_ajustes.aplicar(valores, etiqueta=etiqueta)
            maya_ajustes.guardar_seleccion(seleccion)
        if "res" in valores and visor.abierto():
            visor.poner_resolucion_prueba(valores["res"])
        return resultado

    def restaurar(self):
        with _Deshacer("RenderDesk: restaurar"):
            return maya_ajustes.restaurar()

    def hay_copia(self):
        return maya_ajustes.hay_copia()

    def seleccion(self):
        return maya_ajustes.seleccion()

    def guardar_seleccion(self, datos):
        maya_ajustes.guardar_seleccion(datos)

    def nombre_atributo(self, clave):
        d = presets.catalogo()[clave]
        if d.get("especial") == "oidn":
            return "aiImagerDenoiserOidn.enable"
        if d.get("especial") == "resolucion_prueba":
            return "Test Resolution"
        if cmds.objExists(maya_ajustes.OPCIONES):
            return maya_ajustes.atributo(clave) or ""
        return d["candidatos"][0]

    def abrir_render_settings(self):
        mel.eval("unifiedRenderGlobalsWindow")

    # ----- cámara y tamaño -----

    def _formas_camara(self):
        return cmds.ls(type="camera") or []

    @staticmethod
    def _transformada(forma):
        return (cmds.listRelatives(forma, parent=True) or [forma])[0]

    @staticmethod
    def _forma(transformada):
        """El visor de Arnold nombra las cámaras por su forma («perspShape»)."""
        formas = cmds.listRelatives(transformada, shapes=True, type="camera") or []
        return formas[0] if formas else transformada

    def camaras(self):
        """Cámaras que tiene sentido renderizar: las de perspectiva y las ortográficas marcadas como renderizables."""
        lista = []
        for forma in self._formas_camara():
            if cmds.getAttr(forma + ".orthographic") and not cmds.getAttr(forma + ".renderable"):
                continue
            lista.append(self._transformada(forma))
        propias = sorted(c for c in set(lista) if c != "persp")
        return propias + (["persp"] if "persp" in lista else [])

    def camara(self):
        for forma in self._formas_camara():
            if cmds.getAttr(forma + ".renderable"):
                return self._transformada(forma)
        return ""

    def poner_camara(self, transformada):
        """Deja ``transformada`` como la única cámara renderizable y la pone en el visor."""
        with _Deshacer("RenderDesk: cámara"):
            for forma in self._formas_camara():
                es = self._transformada(forma) == transformada
                if bool(cmds.getAttr(forma + ".renderable")) != es:
                    cmds.setAttr(forma + ".renderable", es)
        if visor.abierto():
            visor.poner_camara(self._forma(transformada))

    def resolucion(self):
        return (int(cmds.getAttr("defaultResolution.width")), int(cmds.getAttr("defaultResolution.height")))

    def poner_resolucion(self, ancho, alto):
        with _Deshacer("RenderDesk: tamaño"):
            cmds.setAttr("defaultResolution.lockDeviceAspectRatio", 0)
            cmds.setAttr("defaultResolution.width", int(ancho))
            cmds.setAttr("defaultResolution.height", int(alto))
            cmds.setAttr("defaultResolution.pixelAspect", 1.0)
            cmds.setAttr("defaultResolution.deviceAspectRatio", float(ancho) / float(alto))

    # ----- visor de Arnold -----

    def visor_disponible(self):
        return visor.disponible()

    def visor_controlable(self):
        return visor.controlable()

    def abrir_visor(self):
        return visor.abrir()

    def probando(self):
        return visor.probando()

    def probar(self, activo, resolucion_prueba=None):
        if activo:
            self.preparar()
            visor.abrir()
            camara = self.camara()
            if camara:
                visor.poner_camara(self._forma(camara))
            if resolucion_prueba:
                visor.poner_resolucion_prueba(resolucion_prueba)
        return visor.probar(activo)

    def region(self, activo):
        return visor.region(activo)

    def en_region(self):
        return visor.en_region()

    def instantanea(self):
        return visor.instantanea()

    # ----- espacio de trabajo -----

    def modo_render_activo(self):
        from . import espacio
        return espacio.activo()

    def modo_render(self, activo):
        from . import interfaz_maya
        interfaz_maya.modo_render(activo)

    # ----- preferencias del usuario (no van en la escena) -----

    def preferencia(self, clave, defecto=""):
        nombre = PREFIJO_PREFERENCIA + clave
        return cmds.optionVar(query=nombre) if cmds.optionVar(exists=nombre) else defecto

    def guardar_preferencia(self, clave, valor):
        cmds.optionVar(stringValue=(PREFIJO_PREFERENCIA + clave, str(valor)))

    # ----- proyecto e historial -----

    def proyecto(self):
        return cmds.workspace(query=True, rootDirectory=True) or os.path.expanduser("~")

    def nombre_escena(self):
        ruta = cmds.file(query=True, sceneName=True) or ""
        return nombre_seguro(ruta) if ruta else "sin_titulo"

    def carpeta_historial(self):
        return os.path.join(self.proyecto(), "renderDesk", "historial", self.nombre_escena())

    def guardar_imagen_visor(self, ruta):
        """Guarda lo que muestra ahora el visor de Arnold en ``ruta``."""
        if os.path.isfile(ruta):
            os.remove(ruta)
        visor.guardar_imagen(ruta)
        return os.path.isfile(ruta)

    # ----- salida -----

    def _atributo_opciones(self, clave):
        for nombre in ATRIBUTOS_SALIDA[clave]:
            if cmds.objExists(maya_ajustes.OPCIONES) and cmds.attributeQuery(
                    nombre, node=maya_ajustes.OPCIONES, exists=True):
                return "{}.{}".format(maya_ajustes.OPCIONES, nombre)
        return None

    def _aovs(self):
        try:
            import mtoa.aovs as aovs
            return [nombre for nombre, _ in aovs.AOVInterface().getAOVNodes(names=True)]
        except Exception:  # noqa: BLE001 - MtoA sin cargar o de otra versión
            return []

    def salida(self):
        datos = {
            "prefijo": cmds.getAttr(GLOBALES + ".imageFilePrefix") or "",
            "inicio": int(round(cmds.getAttr(GLOBALES + ".startFrame"))),
            "fin": int(round(cmds.getAttr(GLOBALES + ".endFrame"))),
            "fotograma": int(round(cmds.currentTime(query=True))),
            "formato": "png",
            "aovs": self._aovs(),
        }
        if cmds.objExists(maya_ajustes.DRIVER):
            datos["formato"] = cmds.getAttr(maya_ajustes.DRIVER + ".aiTranslator") or "png"
        for clave in ("autotx", "usar_tx"):
            plug = self._atributo_opciones(clave)
            datos[clave] = bool(cmds.getAttr(plug)) if plug else None
        return datos

    def poner_salida(self, **cambios):
        """Cambia la salida de la escena: prefijo, formato, inicio, fin, animacion, paquete, autotx, usar_tx."""
        self.preparar()
        with _Deshacer("RenderDesk: salida"):
            if "prefijo" in cambios:
                cmds.setAttr(GLOBALES + ".imageFilePrefix", cambios["prefijo"], type="string")
            if "formato" in cambios and cmds.objExists(maya_ajustes.DRIVER):
                cmds.setAttr(maya_ajustes.DRIVER + ".aiTranslator", cambios["formato"], type="string")
            if "inicio" in cambios:
                cmds.setAttr(GLOBALES + ".startFrame", float(cambios["inicio"]))
            if "fin" in cambios:
                cmds.setAttr(GLOBALES + ".endFrame", float(cambios["fin"]))
            if "animacion" in cambios:
                activa = bool(cambios["animacion"])
                cmds.setAttr(GLOBALES + ".animation", activa)
                if activa:
                    cmds.setAttr(GLOBALES + ".outFormatControl", 0)
                    cmds.setAttr(GLOBALES + ".putFrameBeforeExt", 1)
                    cmds.setAttr(GLOBALES + ".periodInExt", 1)
                    cmds.setAttr(GLOBALES + ".extensionPadding", 4)
            for clave in ("autotx", "usar_tx"):
                if clave in cambios:
                    plug = self._atributo_opciones(clave)
                    if plug:
                        cmds.setAttr(plug, bool(cambios[clave]))
        if "paquete" in cambios:
            self._poner_paquete(cambios["paquete"])

    def _poner_paquete(self, paquete):
        """Deja en la escena los AOV del paquete. Solo quita AOV de los paquetes; los demás no se tocan."""
        try:
            import mtoa.aovs as aovs
        except ImportError:
            return False
        interfaz = aovs.AOVInterface()
        queridos = set(salida.aovs_de(paquete))
        de_paquetes = set(n for _, nombres in salida.PAQUETES_AOV for n in nombres)
        actuales = set(self._aovs())
        sobran = sorted((actuales & de_paquetes) - queridos)
        if sobran:
            interfaz.removeAOVs(sobran)
        for nombre in salida.aovs_de(paquete):
            if nombre not in actuales:
                try:
                    interfaz.addAOV(nombre)
                except Exception as error:  # noqa: BLE001
                    cmds.warning("RenderDesk: no se pudo crear el AOV {} ({})".format(nombre, error))
        return True

    def ruta_imagenes(self):
        regla = cmds.workspace(fileRuleEntry="images") or "images"
        return regla if os.path.isabs(regla) else os.path.join(self.proyecto(), regla)

    # ----- giro -----

    def crear_giro(self, inicio, fin):
        """Crea una cámara que da una vuelta completa alrededor de la selección (o de toda la escena)."""
        objetos = cmds.ls(selection=True, type="transform") or []
        if not objetos:
            mallas = cmds.ls(type="mesh", noIntermediate=True) or []
            objetos = sorted(set(cmds.listRelatives(mallas, parent=True, fullPath=True) or []))
        if not objetos:
            return ""
        x0, y0, z0, x1, y1, z1 = cmds.exactWorldBoundingBox(objetos)
        centro = ((x0 + x1) / 2.0, (y0 + y1) / 2.0, (z0 + z1) / 2.0)
        radio = max(0.01, 0.5 * ((x1 - x0) ** 2 + (y1 - y0) ** 2 + (z1 - z0) ** 2) ** 0.5)
        with _Deshacer("RenderDesk: giro"):
            if cmds.objExists(GRUPO_GIRO):
                cmds.delete(GRUPO_GIRO)
            pivote = cmds.group(empty=True, name=GRUPO_GIRO)
            cmds.xform(pivote, worldSpace=True, translation=centro)
            camara, forma = cmds.camera(name="camara_giro")
            camara = cmds.parent(camara, pivote)[0]
            ancho, alto = self.resolucion()
            fov = salida.fov_de_camara(cmds.getAttr(forma + ".focalLength"),
                                       cmds.getAttr(forma + ".horizontalFilmAperture"), ancho, alto)
            distancia = salida.distancia_giro(radio, fov)
            altura = radio * 0.35
            cmds.xform(camara, objectSpace=True, translation=(0, altura, distancia))
            import math
            cmds.xform(camara, objectSpace=True, rotation=(-math.degrees(math.atan2(altura, distancia)), 0, 0))
            cmds.setAttr(forma + ".farClipPlane", max(1000.0, (distancia + radio) * 4))
            cmds.setAttr(forma + ".nearClipPlane", max(0.01, (distancia - radio) * 0.05))
            cmds.setKeyframe(pivote, attribute="rotateY", time=int(inicio), value=0)
            cmds.setKeyframe(pivote, attribute="rotateY", time=int(fin) + 1, value=360)
            cmds.keyTangent(pivote, attribute="rotateY", inTangentType="linear", outTangentType="linear")
        transformada = cmds.ls(camara)[0]
        self.poner_camara(transformada)
        return transformada

    # ----- render final en segundo plano -----

    def _render_exe(self):
        return salida.ejecutable_render(os.environ.get("MAYA_LOCATION", ""), windows=sys.platform.startswith("win"))

    def preparar_render(self, que, nucleos):
        """Guarda una copia de la escena para el render en segundo plano y devuelve cómo lanzarlo.

        La copia va en ``renderDesk/lanzados/<fecha>/<escena>.ma`` (con el mismo nombre que la escena
        para que <Scene> salga igual) y lleva los núcleos elegidos; la escena abierta no cambia.
        """
        self.preparar()
        datos = self.salida()
        nombre = self.nombre_escena()
        carpeta_copia = os.path.join(self.proyecto(), "renderDesk", "lanzados", time.strftime("%Y%m%d_%H%M%S"))
        os.makedirs(carpeta_copia)
        copia = os.path.join(carpeta_copia, nombre + ".ma")
        plug_auto, plug_hilos = self._atributo_opciones("hilos_auto"), self._atributo_opciones("hilos")
        antes = (cmds.getAttr(plug_auto) if plug_auto else None, cmds.getAttr(plug_hilos) if plug_hilos else None)
        modificada = cmds.file(query=True, modified=True)
        try:
            if plug_auto and plug_hilos:
                cmds.setAttr(plug_auto, False)
                cmds.setAttr(plug_hilos, salida.hilos(nucleos))
            cmds.file(copia, exportAll=True, type="mayaAscii", force=True, preserveReferences=True)
        finally:
            if plug_auto and plug_hilos:
                cmds.setAttr(plug_auto, antes[0])
                cmds.setAttr(plug_hilos, antes[1])
            cmds.file(modified=modificada)
        if que == "fija":
            inicio = fin = datos["fotograma"]
        else:
            inicio, fin = datos["inicio"], datos["fin"]
        carpeta = self.ruta_imagenes()
        camara = self.camara() or "persp"
        return {
            "comando": salida.comando_render(self._render_exe(), copia, carpeta, camara, inicio, fin, self.proyecto()),
            "carpeta": carpeta,
            "extension": salida.EXTENSIONES.get(datos["formato"], "." + datos["formato"]),
            "total": salida.total_fotogramas(que, inicio, fin),
            "registro": os.path.join(carpeta_copia, "render.log"),
            "copia": copia,
        }

    def aviso_terminado(self, texto):
        try:
            cmds.inViewMessage(assistMessage=texto, position="topCenter", fade=True, fadeStayTime=4000)
        except RuntimeError:
            pass
        print("RenderDesk | " + texto)

    def abrir_carpeta(self, ruta):
        from .qt import QtCore, QtGui
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(ruta))
