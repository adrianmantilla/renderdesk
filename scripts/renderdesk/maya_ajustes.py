"""Leer y escribir los ajustes de RenderDesk en la escena de Maya.

* Cada ajuste se busca por su lista de nombres candidatos y se salta, con aviso,
  si la versión de Arnold no lo tiene.
* Antes de aplicar se guarda en la escena una copia de lo que había, para poder
  restaurarlo aunque se cierre Maya.
"""

import json

from . import presets

OPCIONES = "defaultArnoldRenderOptions"
DRIVER = "defaultArnoldDriver"
NODO_DATOS = "renderDesk_datos"
TIPO_OIDN = "aiImagerDenoiserOidn"
NODO_OIDN = "renderDesk_oidn"


def _cmds():
    from maya import cmds
    return cmds


def preparar():
    """Carga Arnold, lo pone como motor y crea sus nodos de opciones si faltan."""
    cmds = _cmds()
    if not cmds.pluginInfo("mtoa", query=True, loaded=True):
        cmds.loadPlugin("mtoa")
    if not cmds.objExists(OPCIONES):
        import mtoa.core
        mtoa.core.createOptions()
    cmds.setAttr("defaultRenderGlobals.currentRenderer", "arnold", type="string")


def atributo(clave):
    """Nombre del atributo de Maya que corresponde a ``clave``, o None si no existe."""
    cmds = _cmds()
    d = presets.catalogo()[clave]
    for nombre in d.get("candidatos", ()):
        if cmds.attributeQuery(nombre, node=OPCIONES, exists=True):
            return nombre
    return None


# ---------- limpiador de ruido (imager OIDN) ----------

def _conexiones_imager():
    """(nodo, atributo) donde MtoA busca los imagers, según versión.

    En MtoA 5.6 el driver no tiene atributo de imagers: van en las opciones.
    """
    cmds = _cmds()
    return [(n, a) for n in (OPCIONES, DRIVER) for a in ("imagers", "imager")
            if cmds.objExists(n) and cmds.attributeQuery(a, node=n, exists=True)]


def _oidn():
    cmds = _cmds()
    existentes = cmds.ls(type=TIPO_OIDN) or []
    return existentes[0] if existentes else None


def donde_oidn():
    """Para diagnóstico: a qué está conectado cada imager OIDN de la escena."""
    cmds = _cmds()
    return {n: cmds.listConnections(n, destination=True, source=False, plugs=True) or []
            for n in (cmds.ls(type=TIPO_OIDN) or [])}


def leer_oidn():
    cmds = _cmds()
    nodo = _oidn()
    if not nodo:
        return 0
    if cmds.attributeQuery("enable", node=nodo, exists=True) and not cmds.getAttr(nodo + ".enable"):
        return 0
    return 1 if cmds.listConnections(nodo, destination=True, source=False) else 0


def poner_oidn(activo):
    """Crea o activa el imager OIDN conectado al driver; lo desactiva sin borrarlo."""
    cmds = _cmds()
    nodo = _oidn()
    if not activo:
        if nodo and cmds.attributeQuery("enable", node=nodo, exists=True):
            cmds.setAttr(nodo + ".enable", 0)
        return True
    if TIPO_OIDN not in (cmds.allNodeTypes() or []):
        return False
    if not nodo:
        nodo = cmds.createNode(TIPO_OIDN, name=NODO_OIDN)
    if cmds.attributeQuery("enable", node=nodo, exists=True):
        cmds.setAttr(nodo + ".enable", 1)
    if not cmds.listConnections(nodo, destination=True, source=False):
        for nodo_destino, destino in _conexiones_imager():
            plug = "{}.{}".format(nodo_destino, destino)
            try:
                if cmds.attributeQuery(destino, node=nodo_destino, multi=True):
                    indice = len(cmds.getAttr(plug, multiIndices=True) or [])
                    plug = "{}[{}]".format(plug, indice)
                cmds.connectAttr(nodo + ".message", plug, force=True)
                break
            except RuntimeError:
                continue
        else:
            return False
    return True


# ---------- leer y aplicar ----------

def leer():
    """Ajustes actuales de la escena. Devuelve (valores, claves_que_faltan)."""
    cmds = _cmds()
    valores, faltan = {}, []
    for clave, d in presets.catalogo().items():
        especial = d.get("especial")
        if especial == "oidn":
            valores[clave] = leer_oidn()
        elif especial == "resolucion_prueba":
            valores[clave] = int(_datos().get("res", d["fabrica"]))
        else:
            nombre = atributo(clave)
            if nombre is None:
                faltan.append(clave)
                continue
            valores[clave] = presets.ajustar_tipo(clave, cmds.getAttr("{}.{}".format(OPCIONES, nombre)))
    return valores, faltan


def aplicar(valores, guardar_copia=True, etiqueta=""):
    """Escribe ``valores`` en la escena. Devuelve (cambiados, saltados).

    ``cambiados`` es una lista de (clave, antes, después).
    """
    cmds = _cmds()
    preparar()
    antes, _ = leer()
    if guardar_copia and not _datos().get("copia"):
        _guardar_datos(copia=antes)
    cambiados, saltados = [], []
    for clave, valor in valores.items():
        d = presets.catalogo().get(clave)
        if d is None:
            continue
        especial = d.get("especial")
        if especial == "oidn":
            if not poner_oidn(valor):
                saltados.append(clave)
                continue
        elif especial == "resolucion_prueba":
            _guardar_datos(res=int(valor))
        else:
            nombre = atributo(clave)
            if nombre is None:
                saltados.append(clave)
                continue
            plug = "{}.{}".format(OPCIONES, nombre)
            if d["tipo"] == "bool":
                cmds.setAttr(plug, bool(valor))
            else:
                cmds.setAttr(plug, valor)
        if antes.get(clave) != valor:
            cambiados.append((clave, antes.get(clave), valor))
    if etiqueta:
        _guardar_datos(preset=etiqueta)
    return cambiados, saltados


def restaurar():
    """Vuelve a los ajustes que había antes del primer «Aplicar». Devuelve True si había copia."""
    copia = _datos().get("copia")
    if not copia:
        return False
    aplicar(copia, guardar_copia=False)
    _guardar_datos(copia=None, preset="")
    return True


# ---------- datos de RenderDesk guardados en la escena ----------

def _datos():
    cmds = _cmds()
    if not cmds.objExists(NODO_DATOS):
        return {}
    try:
        return json.loads(cmds.getAttr(NODO_DATOS + ".datos") or "{}")
    except ValueError:
        return {}


def _guardar_datos(**cambios):
    cmds = _cmds()
    if not cmds.objExists(NODO_DATOS):
        cmds.createNode("network", name=NODO_DATOS)
        cmds.addAttr(NODO_DATOS, longName="datos", dataType="string")
    datos = _datos()
    for k, v in cambios.items():
        if v is None:
            datos.pop(k, None)
        else:
            datos[k] = v
    cmds.setAttr(NODO_DATOS + ".datos", json.dumps(datos), type="string")
    return datos


def preset_aplicado():
    return _datos().get("preset", "")
