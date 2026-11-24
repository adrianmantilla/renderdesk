"""Espacio de trabajo «Modo render».

Al entrar se recuerda el espacio en el que se estaba y se pasa a uno propio,
«RenderDesk», con el visor de Arnold grande a la derecha y el panel a su lado. La
primera vez se crea copiando el espacio actual. Al salir se vuelve al espacio
anterior tal como Maya lo tenía guardado.

Cambiar de espacio destruye y rehace los paneles, el de RenderDesk incluido: por
eso el panel llama a estas funciones con ``cmds.evalDeferred`` y nunca desde
dentro de su propio clic.
"""

NOMBRE = "RenderDesk"
VAR_ANTERIOR = "renderDesk_espacioAnterior"
ANCHO_VISOR = 0.5          # parte del ancho de la ventana de Maya para el visor


def _cmds():
    from maya import cmds
    return cmds


def actual():
    try:
        return _cmds().workspaceLayoutManager(query=True, current=True) or ""
    except (RuntimeError, TypeError):
        return ""


def activo():
    return actual() == NOMBRE


def anterior():
    cmds = _cmds()
    if cmds.optionVar(exists=VAR_ANTERIOR):
        return cmds.optionVar(query=VAR_ANTERIOR)
    return ""


def _existentes():
    try:
        return _cmds().workspaceLayoutManager(listLayouts=True) or []
    except (RuntimeError, TypeError):
        return []


def entrar(colocar):
    """Pasa al espacio «RenderDesk». ``colocar()`` abre y acopla el visor y el panel."""
    cmds = _cmds()
    ahora = actual()
    if ahora and ahora != NOMBRE:
        cmds.optionVar(stringValue=(VAR_ANTERIOR, ahora))
    if ahora != NOMBRE:
        if NOMBRE in _existentes():
            cmds.workspaceLayoutManager(setCurrent=NOMBRE)
        else:
            cmds.workspaceLayoutManager(saveAs=NOMBRE)
            if actual() != NOMBRE:
                cmds.workspaceLayoutManager(setCurrent=NOMBRE)
    colocar()
    return actual() == NOMBRE


def salir():
    """Vuelve al espacio de antes. Devuelve su nombre, o "" si no había ninguno guardado."""
    cmds = _cmds()
    destino = anterior()
    if not destino or destino not in _existentes():
        destino = next((e for e in _existentes() if e != NOMBRE), "")
    if destino and actual() != destino:
        cmds.workspaceLayoutManager(setCurrent=destino)
    return destino


def acoplar_visor_grande(control_visor):
    """Acopla el visor a la derecha de la ventana de Maya, con la mitad del ancho."""
    cmds = _cmds()
    if not cmds.workspaceControl(control_visor, exists=True):
        return False
    try:
        if cmds.workspaceControl(control_visor, query=True, floating=True):
            cmds.workspaceControl(control_visor, edit=True, dockToMainWindow=("right", False))
    except RuntimeError:
        return False
    try:
        from .qt import ventana_maya
        principal = ventana_maya()
        if principal is not None:
            cmds.workspaceControl(control_visor, edit=True, resizeWidth=int(principal.width() * ANCHO_VISOR))
    except (RuntimeError, TypeError):
        pass
    return True
