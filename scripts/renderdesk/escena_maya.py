"""Servicios del panel sobre la escena de Maya (cámaras, tamaño, ajustes y visor).

El panel no llama a Maya directamente: todo pasa por aquí, y las pruebas sin
Maya usan ``panel.Servicios`` en su lugar.
"""

from maya import cmds, mel

from . import maya_ajustes, presets, visor

PREFIJO_PREFERENCIA = "renderDesk_"


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
