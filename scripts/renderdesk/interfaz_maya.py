"""Une RenderDesk con Maya: menú, panel acoplado al visor de Arnold, órdenes para atajos y «Modo render»."""

from maya import cmds

import renderdesk
from renderdesk import espacio, pack, visor
from renderdesk.i18n import t
from renderdesk.qt import QtWidgets, destruir, shiboken, sigue_vivo

CONTROL = "RenderDeskWorkspaceControl"
MENU = "RenderDeskMenu"
PLUGIN = "renderdesk_plugin"
COMANDOS = {
    "RenderDeskAbrir": ("cmd.abrir", "alternar()"),
    "RenderDeskProbar": ("cmd.probar", "probar()"),
    "RenderDeskInstantanea": ("cmd.instantanea", "instantanea()"),
    "RenderDeskModoRender": ("cmd.modo_render", "alternar_modo_render()"),
}

_estado = {"ventana": None, "servicios": None, "trabajos": []}


def servicios():
    if _estado["servicios"] is None:
        from renderdesk.escena_maya import ServiciosMaya
        _estado["servicios"] = ServiciosMaya()
    return _estado["servicios"]


def ventana():
    v = _estado["ventana"]
    return v if sigue_vivo(v) else None


def restaurar():
    """Maya lo llama al crear (o recuperar con el espacio de trabajo) el panel: mete el panel dentro."""
    from maya import OpenMayaUI as omui
    from renderdesk.panel import PanelRenderDesk
    puntero = omui.MQtUtil.getCurrentParent()
    padre = shiboken.wrapInstance(int(puntero), QtWidgets.QWidget)
    v = ventana()
    if v is None:
        v = PanelRenderDesk(servicios=servicios())
        _estado["ventana"] = v
    padre.layout().addWidget(v)


def _acoplar_al_visor():
    if cmds.workspaceControl(visor.CONTROL, exists=True) and cmds.workspaceControl(CONTROL, exists=True):
        try:
            cmds.workspaceControl(CONTROL, edit=True, dockToControl=(visor.CONTROL, "right"))
            return True
        except RuntimeError:
            return False
    return False


def mostrar(con_visor=True):
    """Abre el panel. Con ``con_visor`` abre también el visor de Arnold y se acopla a su derecha."""
    servicios().preparar()
    if con_visor:
        visor.abrir()
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.workspaceControl(CONTROL, edit=True, restore=True, visible=True)
        if ventana() is not None:
            return ventana()
        cmds.deleteUI(CONTROL)
    cmds.workspaceControl(CONTROL, label="RenderDesk", retain=False, floating=True, initialWidth=380,
                          initialHeight=720, minimumWidth=330, requiredPlugin=PLUGIN,
                          uiScript="import renderdesk.interfaz_maya as m\nm.restaurar()",
                          closeCommand="import renderdesk.interfaz_maya as m\nm.al_cerrar()")
    _acoplar_al_visor()
    return ventana()


def alternar():
    if cmds.workspaceControl(CONTROL, exists=True) and cmds.workspaceControl(CONTROL, query=True, visible=True):
        cmds.workspaceControl(CONTROL, edit=True, visible=False)
    else:
        mostrar()


def al_cerrar():
    v = ventana()
    if v is not None:
        v.cerrar()
    _estado["ventana"] = None


# ---------- acciones (menú, atajos y, más adelante, Radial) ----------

def probar():
    """Arranca o para el render interactivo."""
    v = ventana() or mostrar()
    if v is not None:
        v.boton_probar.toggle()
    else:
        visor.probar(not visor.probando())


def instantanea():
    visor.instantanea()


def modo_render(activo):
    """Entra o sale del espacio «Modo render». Va diferido: cambiar de espacio rehace el panel."""
    cmds.evalDeferred(_entrar if activo else _salir, lowestPriority=True)


def alternar_modo_render():
    modo_render(not espacio.activo())


def _colocar():
    visor.abrir()
    espacio.acoplar_visor_grande(visor.CONTROL)
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.workspaceControl(CONTROL, edit=True, restore=True, visible=True)
        if ventana() is None:
            cmds.deleteUI(CONTROL)
            mostrar(con_visor=False)
    else:
        mostrar(con_visor=False)
    _acoplar_al_visor()


def _refrescar_panel():
    v = ventana()
    if v is not None:
        v.refrescar()


def _entrar():
    try:
        espacio.entrar(_colocar)
    except RuntimeError as error:
        cmds.warning(t("aviso.modo_render", error=error))
    cmds.evalDeferred(_refrescar_panel, lowestPriority=True)


def _salir():
    try:
        espacio.salir()
    except RuntimeError as error:
        cmds.warning(t("aviso.modo_render", error=error))
    cmds.evalDeferred(_refrescar_panel, lowestPriority=True)


# ---------- arranque ----------

def _al_cambiar_escena():
    v = ventana()
    if v is not None:
        v.al_cambiar_escena()


def _crear_ordenes():
    for nombre, (clave, llamada) in COMANDOS.items():
        codigo = "import renderdesk.interfaz_maya as m\nm.{}".format(llamada)
        if cmds.runTimeCommand(nombre, exists=True):
            cmds.runTimeCommand(nombre, edit=True, command=codigo, commandLanguage="python", annotation=t(clave))
        else:
            cmds.runTimeCommand(nombre, command=codigo, commandLanguage="python", annotation=t(clave),
                                category="Custom Scripts.RenderDesk")


def _crear_menu():
    pack.crear_menu(MENU, "RenderDesk")
    cmds.menuItem(label=t("menu.abrir"), command=lambda *_: mostrar(), annotation=t("cmd.abrir"))
    cmds.menuItem(label=t("menu.modo_render"), command=lambda *_: alternar_modo_render(),
                  annotation=t("cmd.modo_render"))
    cmds.menuItem(divider=True)
    cmds.menuItem(label=t("menu.probar"), command=lambda *_: probar(), annotation=t("cmd.probar"))
    cmds.menuItem(label=t("menu.instantanea"), command=lambda *_: instantanea(), annotation=t("cmd.instantanea"))
    cmds.menuItem(divider=True)
    cmds.menuItem(label=t("menu.acerca", version=renderdesk.__version__), enable=False)


def iniciar():
    _crear_ordenes()
    if cmds.about(batch=True):
        return
    _crear_menu()
    _estado["trabajos"] = [
        cmds.scriptJob(event=["SceneOpened", _al_cambiar_escena]),
        cmds.scriptJob(event=["NewSceneOpened", _al_cambiar_escena]),
    ]


def detener():
    for trabajo in _estado["trabajos"]:
        if cmds.scriptJob(exists=trabajo):
            cmds.scriptJob(kill=trabajo, force=True)
    _estado["trabajos"] = []
    v = ventana()
    if v is not None:
        v.cerrar()
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.deleteUI(CONTROL)
    if v is not None:
        destruir(v)
    _estado["ventana"] = None
    pack.quitar_menu(MENU)
