"""Panel de RenderDesk (Qt). No llama a Maya: todo pasa por ``servicios``.

Arriba, la barra para preparar y probar: cámara, tamaño, ▶ Probar, Región e
Instantánea. Debajo, la pestaña Calidad con tres niveles sobre los mismos valores:

* Sencillo: calidad, tipo de escena y extras, sin números.
* Detalle: deslizadores con nombre humano («Grano en superficies mates»).
* Experto: los atributos de Arnold tal cual, con su valor de fábrica al lado.

Cada cambio se escribe en la escena al momento (con un pequeño retardo para no
reiniciar el render interactivo a cada píxel del deslizador). Antes del primer
cambio se guarda una copia, y «Restaurar lo que tenía» vuelve a ella.
"""

import renderdesk
from renderdesk import estilo, modelo, presets
from renderdesk.i18n import t
from renderdesk.qt import QtCore, QtGui, QtWidgets

Qt = QtCore.Qt
NOMBRE_OBJETO = "RenderDeskPanel"
RETARDO_MS = 150
VIGILAR_MS = 1500
MARCA = "●"


class Servicios(object):
    """Servicios sin Maya: una escena de mentira en memoria (para las pruebas y para ver el panel fuera de Maya).

    ``escena_maya.ServiciosMaya`` hace lo mismo con la escena real.
    """
    en_maya = False

    def __init__(self):
        self.valores = presets.fabrica()
        self.copia = None
        self.datos_seleccion = None
        self.lista_camaras = ["camara_final", "persp"]
        self.camara_actual = "persp"
        self.tamano = (960, 540)
        self.ipr = False
        self.recorte = False
        self.instantaneas = 0
        self.modo = False
        self.prefs = {}
        self.aplicaciones = 0

    def preparar(self): return True
    def leer(self): return dict(self.valores), []

    def aplicar(self, valores, etiqueta="", seleccion=None):
        self.datos_seleccion = seleccion
        if self.copia is None:
            self.copia = dict(self.valores)
        cambiados = [(c, self.valores.get(c), v) for c, v in valores.items() if self.valores.get(c) != v]
        self.valores.update(valores)
        self.aplicaciones += 1
        return cambiados, []

    def restaurar(self):
        if self.copia is None:
            return False
        self.valores, self.copia, self.datos_seleccion = dict(self.copia), None, None
        return True

    def hay_copia(self): return self.copia is not None
    def seleccion(self): return self.datos_seleccion
    def guardar_seleccion(self, datos): self.datos_seleccion = datos
    def nombre_atributo(self, clave): return (presets.catalogo()[clave].get("candidatos") or [clave])[0]
    def abrir_render_settings(self): pass
    def camaras(self): return list(self.lista_camaras)
    def camara(self): return self.camara_actual
    def poner_camara(self, c): self.camara_actual = c
    def resolucion(self): return self.tamano
    def poner_resolucion(self, ancho, alto): self.tamano = (ancho, alto)
    def visor_disponible(self): return True
    def visor_controlable(self): return True
    def abrir_visor(self): return True
    def probando(self): return self.ipr

    def probar(self, activo, resolucion_prueba=None):
        self.ipr = activo
        return True

    def region(self, activo):
        self.recorte = activo
        return True

    def en_region(self): return self.recorte

    def instantanea(self):
        self.instantaneas += 1
        return True

    def modo_render_activo(self): return self.modo
    def modo_render(self, activo): self.modo = activo
    def preferencia(self, clave, defecto=""): return self.prefs.get(clave, defecto)
    def guardar_preferencia(self, clave, valor): self.prefs[clave] = str(valor)


# ---------------------------------------------------------------- piezas

def _segmentos(claves, textos, ayudas=None):
    """Fila de botones de segmento exclusivos. Devuelve (widget, grupo, {clave: botón})."""
    fila = QtWidgets.QWidget()
    capa = QtWidgets.QHBoxLayout(fila)
    capa.setContentsMargins(0, 0, 0, 0)
    capa.setSpacing(0)
    grupo = QtWidgets.QButtonGroup(fila)
    grupo.setExclusive(True)
    botones = {}
    for i, clave in enumerate(claves):
        b = QtWidgets.QToolButton()
        b.setText(textos[i])
        b.setCheckable(True)
        b.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        lado = "izq" if i == 0 else ("der" if i == len(claves) - 1 else "medio")
        estilo.rol(b, "segmento", lado=lado)
        if ayudas:
            b.setToolTip(ayudas[i])
        b.setProperty("clave", clave)
        grupo.addButton(b, i)
        capa.addWidget(b, 1)
        botones[clave] = b
    return fila, grupo, botones


class Numero(QtWidgets.QWidget):
    """Deslizador con casilla numérica. Emite ``cambiado(valor)`` solo cuando lo mueve el usuario."""
    cambiado = QtCore.Signal(object)

    def __init__(self, tipo, minimo, maximo, decimales=1, con_barra=True, padre=None):
        super(Numero, self).__init__(padre)
        self.tipo = tipo
        self.factor = 1 if tipo == "int" else 10 ** decimales
        capa = QtWidgets.QHBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.setSpacing(6)
        self.barra = None
        if con_barra:
            self.barra = QtWidgets.QSlider(Qt.Horizontal)
            self.barra.setRange(int(round(minimo * self.factor)), int(round(maximo * self.factor)))
            self.barra.valueChanged.connect(self._de_barra)
            capa.addWidget(self.barra, 1)
        if tipo == "int":
            self.caja = QtWidgets.QSpinBox()
        else:
            self.caja = QtWidgets.QDoubleSpinBox()
            self.caja.setDecimals(decimales)
            self.caja.setSingleStep(1.0 / self.factor if decimales > 1 else 0.5)
        self.caja.setRange(minimo, maximo)
        self.caja.setFixedWidth(58)
        self.caja.setAlignment(Qt.AlignRight)
        self.caja.valueChanged.connect(self._de_caja)
        capa.addWidget(self.caja, 0 if con_barra else 1)
        self._quieto = False

    def valor(self):
        return self.caja.value()

    def poner(self, valor):
        valor = int(round(float(valor))) if self.tipo == "int" else float(valor)
        self._quieto = True
        self.caja.setValue(valor)
        if self.barra is not None:
            self.barra.setValue(int(round(float(valor) * self.factor)))
        self._quieto = False

    def _de_barra(self, v):
        if self._quieto:
            return
        self._quieto = True
        self.caja.setValue(v / float(self.factor) if self.tipo != "int" else v)
        self._quieto = False
        self.cambiado.emit(self.caja.value())

    def _de_caja(self, v):
        if self._quieto:
            return
        self._quieto = True
        if self.barra is not None:
            self.barra.setValue(int(round(float(v) * self.factor)))
        self._quieto = False
        self.cambiado.emit(v)


def _decimales(clave):
    return 3 if clave == "umbral" else 1


# ---------------------------------------------------------------- panel

class PanelRenderDesk(QtWidgets.QWidget):
    def __init__(self, servicios=None, padre=None):
        super(PanelRenderDesk, self).__init__(padre)
        self.servicios = servicios or Servicios()
        self.sel = modelo.Seleccion()
        self._esperados = {}
        self._guardada = None
        self._quieto = False
        estilo.aplicar(self, NOMBRE_OBJETO)
        self.setMinimumWidth(330)

        capa = QtWidgets.QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.setSpacing(0)
        capa.addWidget(self._crear_cabecera())
        cuerpo = QtWidgets.QWidget()
        capa_cuerpo = QtWidgets.QVBoxLayout(cuerpo)
        capa_cuerpo.setContentsMargins(10, 10, 10, 8)
        capa_cuerpo.setSpacing(8)
        capa_cuerpo.addWidget(self._crear_barra())
        self.pestanas = QtWidgets.QTabWidget()
        self.pestanas.addTab(self._crear_calidad(), t("pestana.calidad"))
        capa_cuerpo.addWidget(self.pestanas, 1)
        capa_cuerpo.addLayout(self._crear_pie())
        capa.addWidget(cuerpo, 1)

        self._temporizador = QtCore.QTimer(self)
        self._temporizador.setSingleShot(True)
        self._temporizador.timeout.connect(self.aplicar_pendiente)
        self._vigia = QtCore.QTimer(self)
        self._vigia.timeout.connect(self.vigilar)
        self._vigia.start(VIGILAR_MS)

        nivel = self.servicios.preferencia("nivel", "sencillo")
        self.poner_nivel(nivel if nivel in modelo.NIVELES else "sencillo", guardar=False)
        self.al_cambiar_escena()

    # ------------------------------------------------------------ construcción

    def _crear_cabecera(self):
        marco, fila = estilo.cabecera("RenderDesk", estilo.ACENTO, renderdesk.__version__)
        self.chip = estilo.etiqueta("", "chip")
        self.chip.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        self.chip.setToolTip(t("barra.preset.ayuda"))
        self.boton_modo = QtWidgets.QPushButton(t("modo_render"))
        self.boton_modo.setCheckable(True)
        self.boton_modo.setToolTip(t("modo_render.ayuda"))
        self.boton_modo.toggled.connect(self._al_modo_render)
        fila.insertWidget(fila.count() - 1, self.boton_modo)
        return marco

    def _crear_barra(self):
        marco, capa = estilo.tarjeta(8, 6)
        formulario = estilo.formulario()
        formulario.setHorizontalSpacing(8)
        formulario.setVerticalSpacing(6)
        self.combo_camara = QtWidgets.QComboBox()
        self.combo_camara.setToolTip(t("camara.ayuda"))
        self.combo_camara.activated.connect(self._al_elegir_camara)
        self.combo_tamano = QtWidgets.QComboBox()
        self.combo_tamano.activated.connect(self._al_elegir_tamano)
        formulario.addRow(t("barra.preset"), self.chip)
        formulario.addRow(t("barra.camara"), self.combo_camara)
        formulario.addRow(t("barra.tamano"), self.combo_tamano)
        capa.addLayout(formulario)

        botones = QtWidgets.QHBoxLayout()
        botones.setSpacing(6)
        self.boton_probar = QtWidgets.QPushButton(t("probar"))
        estilo.primario(self.boton_probar)
        self.boton_probar.setCheckable(True)
        self.boton_probar.setToolTip(t("probar.ayuda"))
        self.boton_probar.toggled.connect(self._al_probar)
        self.boton_region = QtWidgets.QPushButton(t("region"))
        self.boton_region.setCheckable(True)
        self.boton_region.setToolTip(t("region.ayuda"))
        self.boton_region.toggled.connect(self._al_region)
        self.boton_instantanea = QtWidgets.QPushButton(t("instantanea"))
        self.boton_instantanea.setToolTip(t("instantanea.ayuda"))
        self.boton_instantanea.clicked.connect(self._al_instantanea)
        botones.addWidget(self.boton_probar, 3)
        botones.addWidget(self.boton_region, 2)
        botones.addWidget(self.boton_instantanea, 2)
        capa.addLayout(botones)
        self.estado = estilo.etiqueta("", "tenue", ajuste=True)
        capa.addWidget(self.estado)
        return marco

    def _crear_calidad(self):
        pagina = QtWidgets.QWidget()
        capa = QtWidgets.QVBoxLayout(pagina)
        capa.setContentsMargins(0, 8, 0, 0)
        capa.setSpacing(8)
        fila, self.grupo_nivel, self.botones_nivel = _segmentos(
            modelo.NIVELES, [t("nivel." + n) for n in modelo.NIVELES], [t("nivel." + n + ".ayuda") for n in modelo.NIVELES])
        self.grupo_nivel.buttonClicked.connect(lambda b: self.poner_nivel(b.property("clave")))
        capa.addWidget(fila)
        self.pilas = QtWidgets.QStackedWidget()
        for pagina_nivel in (self._crear_sencillo(), self._crear_detalle(), self._crear_experto()):
            zona = QtWidgets.QScrollArea()
            zona.setWidgetResizable(True)
            zona.setFrameShape(QtWidgets.QFrame.NoFrame)
            zona.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            zona.setWidget(pagina_nivel)
            self.pilas.addWidget(zona)
        capa.addWidget(self.pilas, 1)
        return pagina

    def _crear_sencillo(self):
        w = QtWidgets.QWidget()
        capa = QtWidgets.QVBoxLayout(w)
        capa.setContentsMargins(0, 0, 4, 0)
        capa.setSpacing(6)

        capa.addWidget(estilo.etiqueta(t("seccion.calidad"), "seccion"))
        calidades = presets.calidades()
        fila, self.grupo_calidad, self.botones_calidad = _segmentos(
            calidades, [t("calidad." + c) for c in calidades], [t("calidad." + c + ".ayuda") for c in calidades])
        self.grupo_calidad.buttonClicked.connect(lambda b: self._al_elegir_calidad(b.property("clave")))
        capa.addWidget(fila)

        capa.addWidget(estilo.etiqueta(t("seccion.escena"), "seccion"))
        escenas = presets.escenas()
        fila, self.grupo_escena, self.botones_escena = _segmentos(
            escenas, [t("escena." + e) for e in escenas], [t("escena." + e + ".ayuda") for e in escenas])
        self.grupo_escena.buttonClicked.connect(lambda b: self._al_elegir_escena(b.property("clave")))
        capa.addWidget(fila)

        capa.addWidget(estilo.etiqueta(t("seccion.extras"), "seccion"))
        self.casillas_extra = {}
        for extra in presets.extras():
            casilla = QtWidgets.QCheckBox(t("extra." + extra))
            casilla.setToolTip(t("extra." + extra + ".ayuda"))
            casilla.toggled.connect(lambda activo, e=extra: self._al_extra(e, activo))
            capa.addWidget(casilla)
            self.casillas_extra[extra] = casilla

        self.aviso_sin_preset = estilo.etiqueta(t("sin_preset"), "aviso", ajuste=True)
        capa.addWidget(self.aviso_sin_preset)

        capa.addWidget(estilo.etiqueta(t("seccion.cambios"), "seccion"))
        self.lista_cambios = estilo.etiqueta("", ajuste=True)
        self.lista_cambios.setTextFormat(Qt.RichText)
        capa.addWidget(self.lista_cambios)
        consejo = estilo.etiqueta(t("consejo"), "tenue", ajuste=True)
        capa.addWidget(consejo)
        capa.addStretch(1)
        return w

    def _fila_marca(self, texto, ayuda):
        etiqueta = estilo.etiqueta(texto)
        etiqueta.setToolTip(ayuda)
        marca = estilo.etiqueta(MARCA)
        marca.setStyleSheet("color: {}; font-size: 8pt;".format(estilo.ACENTO))
        marca.setToolTip(t("retocado.ayuda"))
        marca.setFixedWidth(10)
        return etiqueta, marca

    def _crear_detalle(self):
        w = QtWidgets.QWidget()
        capa = QtWidgets.QVBoxLayout(w)
        capa.setContentsMargins(0, 0, 4, 0)
        capa.setSpacing(4)
        self.sobre_detalle = estilo.etiqueta("", "tenue", ajuste=True)
        capa.addWidget(self.sobre_detalle)
        self.controles_detalle = {}
        self.marcas_detalle = {}
        catalogo = presets.catalogo()
        topes = dict(modelo.DETALLE)
        grupo_actual = None
        rejilla = None
        for clave in presets.orden_ajustes():
            if clave not in topes:
                continue
            d = catalogo[clave]
            if d["grupo"] != grupo_actual:
                grupo_actual = d["grupo"]
                capa.addWidget(estilo.etiqueta(t("grupo." + grupo_actual), "seccion"))
                contenedor = QtWidgets.QWidget()
                rejilla = QtWidgets.QGridLayout(contenedor)
                rejilla.setContentsMargins(0, 0, 0, 0)
                rejilla.setHorizontalSpacing(6)
                rejilla.setVerticalSpacing(5)
                rejilla.setColumnStretch(2, 1)
                capa.addWidget(contenedor)
            ayuda = "<b>{}</b><br>{}".format(t("ajuste." + clave + ".nombre"), t("ajuste." + clave + ".porque"))
            etiqueta, marca = self._fila_marca(t("ajuste." + clave + ".detalle"), ayuda)
            fila = rejilla.rowCount()
            rejilla.addWidget(marca, fila, 0)
            rejilla.addWidget(etiqueta, fila, 1)
            if d["tipo"] == "bool":
                control = QtWidgets.QCheckBox()
                control.toggled.connect(lambda v, c=clave: self._al_retocar(c, 1 if v else 0))
            else:
                control = Numero(d["tipo"], d.get("min", 0), topes[clave] or d.get("max", 100), _decimales(clave))
                control.cambiado.connect(lambda v, c=clave: self._al_retocar(c, v))
            control.setToolTip(ayuda)
            rejilla.addWidget(control, fila, 2)
            self.controles_detalle[clave] = control
            self.marcas_detalle[clave] = marca
        botones = QtWidgets.QHBoxLayout()
        self.boton_volver_detalle = QtWidgets.QPushButton(t("volver_preset"))
        self.boton_volver_detalle.clicked.connect(self._al_volver_preset)
        botones.addWidget(self.boton_volver_detalle)
        botones.addStretch(1)
        capa.addSpacing(6)
        capa.addLayout(botones)
        capa.addStretch(1)
        return w

    def _crear_experto(self):
        w = QtWidgets.QWidget()
        capa = QtWidgets.QVBoxLayout(w)
        capa.setContentsMargins(0, 0, 4, 0)
        capa.setSpacing(4)
        capa.addWidget(estilo.etiqueta(t("experto.nota"), "tenue", ajuste=True))
        self.controles_experto = {}
        self.marcas_experto = {}
        self.nombres_experto = {}
        catalogo = presets.catalogo()
        grupo_actual = None
        rejilla = None
        fuente = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        for clave in presets.orden_ajustes():
            d = catalogo[clave]
            if d["grupo"] != grupo_actual:
                grupo_actual = d["grupo"]
                capa.addWidget(estilo.etiqueta(t("grupo." + grupo_actual), "seccion"))
                contenedor = QtWidgets.QWidget()
                rejilla = QtWidgets.QGridLayout(contenedor)
                rejilla.setContentsMargins(0, 0, 0, 0)
                rejilla.setHorizontalSpacing(8)
                rejilla.setVerticalSpacing(4)
                rejilla.setColumnStretch(1, 1)
                rejilla.addWidget(estilo.etiqueta(t("experto.atributo"), "tenue"), 0, 1)
                rejilla.addWidget(estilo.etiqueta(t("experto.ahora"), "tenue"), 0, 2)
                rejilla.addWidget(estilo.etiqueta(t("experto.fabrica"), "tenue"), 0, 3)
                capa.addWidget(contenedor)
            ayuda = "<b>{}</b><br>{}".format(t("ajuste." + clave + ".nombre"), t("ajuste." + clave + ".porque"))
            etiqueta, marca = self._fila_marca("", ayuda)
            etiqueta.setFont(fuente)
            fila = rejilla.rowCount()
            rejilla.addWidget(marca, fila, 0)
            rejilla.addWidget(etiqueta, fila, 1)
            if d["tipo"] == "bool":
                control = QtWidgets.QCheckBox()
                control.toggled.connect(lambda v, c=clave: self._al_retocar(c, 1 if v else 0))
            else:
                control = Numero(d["tipo"], d.get("min", 0), d.get("max", 100), _decimales(clave), con_barra=False)
                control.cambiado.connect(lambda v, c=clave: self._al_retocar(c, v))
            control.setToolTip(ayuda)
            rejilla.addWidget(control, fila, 2)
            fabrica = estilo.etiqueta(modelo.texto_valor(clave, d["fabrica"]), "tenue")
            rejilla.addWidget(fabrica, fila, 3)
            self.controles_experto[clave] = control
            self.marcas_experto[clave] = marca
            self.nombres_experto[clave] = etiqueta
        botones = QtWidgets.QHBoxLayout()
        self.boton_volver_experto = QtWidgets.QPushButton(t("volver_preset"))
        self.boton_volver_experto.clicked.connect(self._al_volver_preset)
        completo = QtWidgets.QPushButton(t("render_settings_completo"))
        completo.clicked.connect(self._al_render_settings)
        botones.addWidget(self.boton_volver_experto)
        botones.addWidget(completo)
        botones.addStretch(1)
        capa.addSpacing(6)
        capa.addLayout(botones)
        capa.addStretch(1)
        return w

    def _crear_pie(self):
        fila = QtWidgets.QHBoxLayout()
        fila.setSpacing(6)
        self.boton_restaurar = QtWidgets.QPushButton(t("restaurar"))
        self.boton_restaurar.setToolTip(t("restaurar.ayuda"))
        self.boton_restaurar.clicked.connect(self._al_restaurar)
        ajustes = QtWidgets.QPushButton(t("render_settings"))
        ajustes.setToolTip(t("render_settings.ayuda"))
        ajustes.clicked.connect(self._al_render_settings)
        fila.addWidget(self.boton_restaurar)
        fila.addStretch(1)
        fila.addWidget(ajustes)
        return fila

    # ------------------------------------------------------------ estado

    def al_cambiar_escena(self):
        """Lee la escena: lo que RenderDesk tenía elegido en ella, o sus ajustes tal cual."""
        self._temporizador.stop()
        valores, _ = self.servicios.leer()
        datos = self.servicios.seleccion()
        self.sel = modelo.Seleccion.de_dict(datos, base=valores) if datos else modelo.Seleccion(base=valores)
        self._guardada = datos
        # Lo que se espera ver en la escena: si alguien lo cambió con el panel cerrado, saldrá como retoque.
        self._esperados = self.sel.valores() if self.sel.hay_preset() else dict(valores)
        self.vigilar(adoptar=True)
        self.refrescar()

    def nivel(self):
        return next((n for n, b in self.botones_nivel.items() if b.isChecked()), "sencillo")

    def poner_nivel(self, nivel, guardar=True):
        self.botones_nivel[nivel].setChecked(True)
        self.pilas.setCurrentIndex(modelo.NIVELES.index(nivel))
        if guardar:
            self.servicios.guardar_preferencia("nivel", nivel)

    def refrescar(self):
        """Pone todos los controles con el estado actual, sin disparar cambios."""
        self._quieto = True
        try:
            sel = self.sel
            valores = sel.valores()
            retocados = set(sel.retocados())
            self.chip.setText(sel.nombre())
            color = estilo.ACENTO if sel.hay_preset() else estilo.TENUE
            q = QtGui.QColor(color)
            self.chip.setStyleSheet("background: rgba({},{},{},60); color: {};".format(
                q.red(), q.green(), q.blue(), q.lighter(130).name()))

            self.grupo_calidad.setExclusive(False)
            for clave, b in self.botones_calidad.items():
                b.setChecked(clave == sel.calidad)
            self.grupo_calidad.setExclusive(True)
            for clave, b in self.botones_escena.items():
                b.setChecked(clave == sel.escena)
                b.setEnabled(sel.hay_preset())
            for clave, casilla in self.casillas_extra.items():
                casilla.setChecked(clave in sel.extras)
                casilla.setEnabled(sel.hay_preset())
            self.aviso_sin_preset.setVisible(not sel.hay_preset())
            self.lista_cambios.setText(self._texto_cambios(valores))

            self.sobre_detalle.setText(t("detalle.sobre", preset=sel.nombre()))
            for clave, control in self.controles_detalle.items():
                self._poner_control(control, valores.get(clave))
                self.marcas_detalle[clave].setText(MARCA if clave in retocados else "")
            for clave, control in self.controles_experto.items():
                self._poner_control(control, valores.get(clave))
                self.marcas_experto[clave].setText(MARCA if clave in retocados else "")
                nombre = self.servicios.nombre_atributo(clave) or t("experto.no_existe")
                self.nombres_experto[clave].setText(nombre)
            for boton in (self.boton_volver_detalle, self.boton_volver_experto):
                boton.setEnabled(sel.modificado())
            self.boton_restaurar.setEnabled(self.servicios.hay_copia())
            self._refrescar_barra()
        finally:
            self._quieto = False

    @staticmethod
    def _poner_control(control, valor):
        if valor is None:
            return
        if isinstance(control, QtWidgets.QCheckBox):
            control.setChecked(bool(valor))
        else:
            control.poner(valor)

    def _texto_cambios(self, valores):
        cambios = modelo.cambios_frente_a_fabrica(valores)
        if not cambios:
            return "<span style='color:{}'>{}</span>".format(estilo.TENUE, t("cambios.ninguno"))
        filas = []
        for clave, antes, ahora in cambios:
            filas.append("<tr><td>{}</td><td style='color:{};padding-left:8px'>{}</td>"
                         "<td style='padding-left:4px'>→ <b>{}</b></td></tr>".format(
                             t("ajuste." + clave + ".detalle"), estilo.TENUE, modelo.texto_valor(clave, antes),
                             modelo.texto_valor(clave, ahora)))
        return "<table cellspacing='0' cellpadding='1'>{}</table>".format("".join(filas))

    def _refrescar_barra(self):
        s = self.servicios
        camaras = s.camaras()
        actual = s.camara()
        if [self.combo_camara.itemText(i) for i in range(self.combo_camara.count())] != camaras:
            self.combo_camara.clear()
            self.combo_camara.addItems(camaras)
        if actual in camaras:
            self.combo_camara.setCurrentIndex(camaras.index(actual))
        ancho, alto = s.resolucion()
        clave = modelo.tamano_de(ancho, alto)
        self.combo_tamano.clear()
        if clave is None:
            self.combo_tamano.addItem(modelo.texto_tamano(None, ancho, alto), None)
        for c, a, b in modelo.TAMANOS:
            self.combo_tamano.addItem(modelo.texto_tamano(c), (a, b))
        self.combo_tamano.setCurrentIndex(0 if clave is None else [c for c, _, _ in modelo.TAMANOS].index(clave))
        self._refrescar_visor()

    def _refrescar_visor(self, probando=None, region=None):
        s = self.servicios
        disponible = s.visor_disponible()
        controlable = disponible and s.visor_controlable()
        probando = controlable and (s.probando() if probando is None else probando)
        region = controlable and (s.en_region() if region is None else region)
        quieto, self._quieto = self._quieto, True
        for boton, activo in ((self.boton_probar, probando), (self.boton_region, region)):
            boton.blockSignals(True)
            boton.setChecked(bool(activo))
            boton.blockSignals(False)
        self._quieto = quieto
        self.boton_probar.setText(t("parar") if probando else t("probar"))
        for boton in (self.boton_probar, self.boton_region, self.boton_instantanea):
            boton.setEnabled(controlable)
        if not disponible:
            self.estado.setText(t("estado.sin_arnold"))
        elif not controlable:
            self.estado.setText(t("estado.sin_control"))
        elif probando:
            self.estado.setText(t("estado.probando", preset=self.sel.nombre()))
        else:
            self.estado.setText(t("estado.listo"))
        modo = s.modo_render_activo()
        self.boton_modo.blockSignals(True)
        self.boton_modo.setChecked(modo)
        self.boton_modo.blockSignals(False)
        self.boton_modo.setText(t("modo_render.salir") if modo else t("modo_render"))

    def vigilar(self, adoptar=True):
        """Cada poco: estado del visor y cambios hechos fuera del panel (Render Settings, Ctrl+Z...)."""
        if self._temporizador.isActive():
            return                                  # hay un cambio nuestro sin escribir todavía
        if adoptar and self.servicios.seleccion() != self._guardada:
            self.al_cambiar_escena()                # Ctrl+Z, o la escena cambió por otro lado
            return
        if adoptar and self._esperados:
            valores, _ = self.servicios.leer()
            escena = {c: v for c, v in valores.items() if c != "res"}
            if self.sel.adoptar_de_escena(escena, self._esperados):
                self._esperados = self.sel.valores()
                self._esperados.update(escena)
                self._guardar_seleccion()
                self.refrescar()
                return
        if not self._quieto:
            self._refrescar_visor()

    # ------------------------------------------------------------ cambios

    def _cambio(self):
        """El usuario cambió algo: refresca ya y escribe en la escena en un momento."""
        self.refrescar()
        self._temporizador.start(RETARDO_MS)

    def aplicar_pendiente(self):
        self._temporizador.stop()
        valores = self.sel.valores()
        self._guardada = self._datos_seleccion()
        self.servicios.aplicar(valores, etiqueta=self.sel.nombre(), seleccion=self._guardada)
        self._esperados = valores
        self.refrescar()

    def _datos_seleccion(self):
        return self.sel.a_dict() if self.sel.hay_preset() else None

    def _guardar_seleccion(self):
        self._guardada = self._datos_seleccion()
        self.servicios.guardar_seleccion(self._guardada)

    def _al_elegir_calidad(self, calidad):
        if self._quieto:
            return
        self.sel.elegir_calidad(calidad)
        self._cambio()

    def _al_elegir_escena(self, escena):
        if self._quieto:
            return
        self.sel.elegir_escena(escena)
        self._cambio()

    def _al_extra(self, extra, activo):
        if self._quieto:
            return
        self.sel.poner_extra(extra, activo)
        self._cambio()

    def _al_retocar(self, clave, valor):
        if self._quieto:
            return
        self.sel.retocar(clave, valor)
        self._cambio()

    def _al_volver_preset(self):
        self.sel.volver_al_preset()
        self._cambio()

    def _al_restaurar(self):
        self._temporizador.stop()
        if self.servicios.restaurar():
            valores, _ = self.servicios.leer()
            self.sel = modelo.Seleccion(base=valores)
            self._esperados = dict(valores)
            self._guardada = self.servicios.seleccion()
            self.refrescar()

    def _al_render_settings(self):
        self.servicios.abrir_render_settings()

    def _al_elegir_camara(self, indice):
        self.servicios.poner_camara(self.combo_camara.itemText(indice))
        self._refrescar_barra()

    def _al_elegir_tamano(self, indice):
        datos = self.combo_tamano.itemData(indice)
        if datos:
            self.servicios.poner_resolucion(*datos)
        self._refrescar_barra()

    def _al_probar(self, activo):
        if self._quieto:
            return
        if self._temporizador.isActive():
            self.aplicar_pendiente()
        self.servicios.probar(activo, resolucion_prueba=self.sel.valores().get("res"))
        self._refrescar_visor(probando=activo)

    def _al_region(self, activo):
        if self._quieto:
            return
        self.servicios.region(activo)
        self._refrescar_visor(region=activo)

    def _al_instantanea(self):
        self.servicios.instantanea()

    def _al_modo_render(self, activo):
        if self._quieto:
            return
        self.servicios.modo_render(activo)

    # ------------------------------------------------------------ cierre

    def cerrar(self):
        """Escribe lo pendiente y para los temporizadores (Maya lo llama al cerrar el panel)."""
        if self._temporizador.isActive():
            self.aplicar_pendiente()
        self._vigia.stop()
