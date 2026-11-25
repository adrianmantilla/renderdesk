"""Pestaña Salida del panel y tarjeta de progreso del render final en segundo plano."""

from renderdesk import estilo, salida
from renderdesk.coste import texto_duracion
from renderdesk.i18n import t
from renderdesk.qt import QtCore, QtWidgets

Qt = QtCore.Qt
OTRO = "otro"


def _segmentos(claves, textos, ayudas=None):
    from renderdesk.panel import _segmentos as segmentos
    return segmentos(claves, textos, ayudas)


def _fila(*widgets):
    w = QtWidgets.QWidget()
    capa = QtWidgets.QHBoxLayout(w)
    capa.setContentsMargins(0, 0, 0, 0)
    capa.setSpacing(6)
    for widget in widgets:
        if widget is None:
            capa.addStretch(1)
        else:
            capa.addWidget(widget)
    return w


class PestanaSalida(QtWidgets.QWidget):
    """Qué se renderiza, con qué nombre y formato, qué AOV y con cuántos núcleos.

    Los cambios van directos a la escena por ``servicios.poner_salida``. Lo único que
    toca los valores de calidad es «Qué renderizar» (secuencia y giro fijan el patrón
    de ruido para que no parpadee), por eso se avisa al panel con ``que_cambiado``.
    """
    que_cambiado = QtCore.Signal(str)
    render_final = QtCore.Signal()

    def __init__(self, servicios, padre=None):
        super(PestanaSalida, self).__init__(padre)
        self.servicios = servicios
        self._quieto = False
        self._datos = {}
        self.que = "fija"

        capa = QtWidgets.QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 4, 0)
        capa.setSpacing(6)

        # Qué renderizar
        capa.addWidget(estilo.etiqueta(t("salida.seccion.que"), "seccion"))
        fila, self.grupo_que, self.botones_que = _segmentos(
            salida.QUE, [t("salida." + q) for q in salida.QUE], [t("salida." + q + ".ayuda") for q in salida.QUE])
        self.grupo_que.buttonClicked.connect(lambda b: self._al_que(b.property("clave")))
        capa.addWidget(fila)

        self.inicio = QtWidgets.QSpinBox()
        self.fin = QtWidgets.QSpinBox()
        for caja in (self.inicio, self.fin):
            caja.setRange(-100000, 100000)
            caja.setFixedWidth(70)
            caja.setKeyboardTracking(False)
            caja.valueChanged.connect(self._al_fotogramas)
        self.texto_fotogramas = estilo.etiqueta("", "tenue")
        self.fila_fotogramas = _fila(estilo.etiqueta(t("salida.desde")), self.inicio,
                                     estilo.etiqueta(t("salida.hasta")), self.fin, self.texto_fotogramas, None)
        capa.addWidget(self.fila_fotogramas)
        self.boton_giro = QtWidgets.QPushButton(t("salida.crear_giro"))
        self.boton_giro.setToolTip(t("salida.crear_giro.ayuda"))
        self.boton_giro.clicked.connect(self._al_crear_giro)
        self.texto_giro = estilo.etiqueta("", "tenue", ajuste=True)
        capa.addWidget(self.boton_giro)
        capa.addWidget(self.texto_giro)

        # Archivo
        capa.addWidget(estilo.etiqueta(t("salida.seccion.archivo"), "seccion"))
        formulario = estilo.formulario()
        formulario.setHorizontalSpacing(8)
        formulario.setVerticalSpacing(6)
        fila, self.grupo_formato, self.botones_formato = _segmentos(
            salida.FORMATOS, [t("salida.formato." + f) for f in salida.FORMATOS],
            [t("salida.formato." + f + ".ayuda") for f in salida.FORMATOS])
        self.grupo_formato.buttonClicked.connect(lambda b: self._poner(formato=b.property("clave")))
        formulario.addRow(t("salida.formato"), fila)
        self.combo_nombre = QtWidgets.QComboBox()
        self.combo_nombre.setToolTip(t("salida.nombre.ayuda"))
        for clave, _ in salida.NOMBRES:
            self.combo_nombre.addItem(t("salida.nombre." + clave), clave)
        self.combo_nombre.activated.connect(self._al_nombre)
        formulario.addRow(t("salida.nombre"), self.combo_nombre)
        capa.addLayout(formulario)
        self.ejemplo = estilo.etiqueta("", "tenue", ajuste=True)
        self.ejemplo.setTextInteractionFlags(Qt.TextSelectableByMouse)
        capa.addWidget(self.ejemplo)

        # Pasadas (AOV)
        capa.addWidget(estilo.etiqueta(t("salida.seccion.aov"), "seccion"))
        claves = [c for c, _ in salida.PAQUETES_AOV]
        fila, self.grupo_aov, self.botones_aov = _segmentos(
            claves, [t("salida.aov." + c) for c in claves], [t("salida.aov." + c + ".ayuda") for c in claves])
        self.grupo_aov.buttonClicked.connect(lambda b: self._poner(paquete=b.property("clave")))
        capa.addWidget(fila)
        self.texto_aov = estilo.etiqueta("", "tenue", ajuste=True)
        capa.addWidget(self.texto_aov)
        self.aviso_aov = estilo.etiqueta(t("salida.aov.aviso_png"), "aviso", ajuste=True)
        capa.addWidget(self.aviso_aov)

        # Texturas
        capa.addWidget(estilo.etiqueta(t("salida.seccion.texturas"), "seccion"))
        self.casilla_autotx = QtWidgets.QCheckBox(t("salida.autotx"))
        self.casilla_autotx.setToolTip(t("salida.autotx.ayuda"))
        self.casilla_autotx.toggled.connect(lambda v: self._poner(autotx=v))
        self.casilla_usar_tx = QtWidgets.QCheckBox(t("salida.usar_tx"))
        self.casilla_usar_tx.setToolTip(t("salida.usar_tx.ayuda"))
        self.casilla_usar_tx.toggled.connect(lambda v: self._poner(usar_tx=v))
        capa.addWidget(self.casilla_autotx)
        capa.addWidget(self.casilla_usar_tx)

        # Render final
        capa.addWidget(estilo.etiqueta(t("salida.seccion.final"), "seccion"))
        self.combo_nucleos = QtWidgets.QComboBox()
        self.combo_nucleos.setToolTip(t("salida.nucleos.ayuda"))
        for clave in salida.NUCLEOS:
            self.combo_nucleos.addItem(t("salida.nucleos." + clave), clave)
        self.combo_nucleos.activated.connect(self._al_nucleos)
        formulario = estilo.formulario()
        formulario.setHorizontalSpacing(8)
        formulario.addRow(t("salida.nucleos"), self.combo_nucleos)
        capa.addLayout(formulario)
        self.estimado = estilo.etiqueta("", "tenue", ajuste=True)
        capa.addWidget(self.estimado)
        self.aviso_calidad = estilo.etiqueta("", "aviso", ajuste=True)
        capa.addWidget(self.aviso_calidad)
        self.boton_final = QtWidgets.QPushButton(t("render_final"))
        estilo.primario(self.boton_final)
        self.boton_final.setToolTip(t("render_final.ayuda"))
        self.boton_final.clicked.connect(self.render_final.emit)
        capa.addWidget(self.boton_final)
        capa.addWidget(estilo.etiqueta(t("render_final.nota"), "tenue", ajuste=True))
        capa.addStretch(1)

        nucleos = self.servicios.preferencia("nucleos", salida.NUCLEOS[0])
        self.combo_nucleos.setCurrentIndex(salida.NUCLEOS.index(nucleos) if nucleos in salida.NUCLEOS else 0)

    # ------------------------------------------------------------ estado

    def nucleos(self):
        return self.combo_nucleos.currentData() or salida.NUCLEOS[0]

    def poner_que(self, que):
        """El panel dice qué se renderiza (viene de la selección guardada en la escena)."""
        self.que = que if que in salida.QUE else "fija"
        self.refrescar()

    def refrescar(self):
        self._quieto = True
        try:
            d = self._datos = self.servicios.salida()
            for clave, b in self.botones_que.items():
                b.setChecked(clave == self.que)
            animado = self.que != "fija"
            self.fila_fotogramas.setVisible(animado)
            self.inicio.setValue(int(d.get("inicio", 1)))
            self.fin.setValue(int(d.get("fin", 1)))
            self.texto_fotogramas.setText(salida.texto_fotogramas(d.get("inicio", 1), d.get("fin", 1)))
            self.boton_giro.setVisible(self.que == "giro")
            self.texto_giro.setVisible(self.que == "giro")
            if self.que == "giro" and not self.texto_giro.text():
                self.texto_giro.setText(t("salida.crear_giro.nota"))

            formato = d.get("formato") if d.get("formato") in salida.FORMATOS else None
            for clave, b in self.botones_formato.items():
                b.setChecked(clave == formato)
            clave_nombre = salida.clave_de_prefijo(d.get("prefijo"))
            if clave_nombre is None:
                if self.combo_nombre.findData(OTRO) < 0:
                    self.combo_nombre.addItem(t("salida.nombre.otro"), OTRO)
                self.combo_nombre.setCurrentIndex(self.combo_nombre.findData(OTRO))
            else:
                otro = self.combo_nombre.findData(OTRO)
                if otro >= 0:
                    self.combo_nombre.removeItem(otro)
                self.combo_nombre.setCurrentIndex(self.combo_nombre.findData(clave_nombre))
            ruta = salida.ejemplo(d.get("prefijo") or "<Scene>", self.servicios.nombre_escena(),
                                  self.servicios.camara(), d.get("formato"), d.get("inicio", 1), animado)
            self.ejemplo.setText(t("salida.ejemplo", ruta=ruta))

            paquete = salida.paquete_de(d.get("aovs"))
            for clave, b in self.botones_aov.items():
                b.setChecked(clave == paquete)
            aovs = d.get("aovs") or []
            self.texto_aov.setText(t("salida.aov.lista", lista=", ".join(aovs)) if aovs else t("salida.aov.ninguna"))
            self.aviso_aov.setVisible(bool(aovs) and d.get("formato") != "exr")

            for casilla, clave in ((self.casilla_autotx, "autotx"), (self.casilla_usar_tx, "usar_tx")):
                valor = d.get(clave)
                casilla.setEnabled(valor is not None)
                casilla.setChecked(bool(valor))
        finally:
            self._quieto = False

    def total(self):
        d = self._datos or {}
        return salida.total_fotogramas(self.que, d.get("inicio", 1), d.get("fin", 1))

    def poner_estimado(self, texto, aviso=""):
        self.estimado.setText(texto)
        self.aviso_calidad.setText(aviso)
        self.aviso_calidad.setVisible(bool(aviso))

    def poner_en_marcha(self, activo):
        self.boton_final.setEnabled(not activo)
        self.boton_final.setText(t("render_final.en_marcha") if activo else t("render_final"))

    # ------------------------------------------------------------ cambios

    def _poner(self, **cambios):
        if self._quieto:
            return
        self.servicios.poner_salida(**cambios)
        self.refrescar()

    def _al_que(self, que):
        if self._quieto:
            return
        self.que = que
        cambios = {"animacion": que != "fija"}
        if que == "giro":
            cambios.update(inicio=1, fin=120)       # una vuelta de 5 s a 24 fps; luego se puede cambiar
        self.servicios.poner_salida(**cambios)
        self.refrescar()
        self.que_cambiado.emit(que)

    def _al_fotogramas(self, _valor=None):
        if self._quieto:
            return
        inicio, fin = self.inicio.value(), self.fin.value()
        if fin < inicio:
            fin = inicio
        self._poner(inicio=inicio, fin=fin)

    def _al_nombre(self, indice):
        clave = self.combo_nombre.itemData(indice)
        if clave and clave != OTRO:
            self._poner(prefijo=salida.prefijo(clave))

    def _al_nucleos(self, indice):
        self.servicios.guardar_preferencia("nucleos", self.combo_nucleos.itemData(indice))

    def _al_crear_giro(self):
        d = self.servicios.salida()
        camara = self.servicios.crear_giro(d.get("inicio", 1), d.get("fin", 120))
        self.texto_giro.setText(t("salida.giro_creado", camara=camara) if camara else t("salida.giro_sin_objetos"))
        self.refrescar()
        self.que_cambiado.emit(self.que)     # la cámara cambió: el panel refresca la barra


class TarjetaRender(QtWidgets.QFrame):
    """Progreso del render final: barra, fotograma, tiempo que queda, Cancelar y Abrir carpeta."""
    cancelar = QtCore.Signal()
    abrir_carpeta = QtCore.Signal()

    def __init__(self, padre=None):
        super(TarjetaRender, self).__init__(padre)
        estilo.rol(self, "tarjeta")
        self.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Maximum)
        capa = QtWidgets.QVBoxLayout(self)
        capa.setContentsMargins(8, 6, 8, 6)
        capa.setSpacing(4)
        self.titulo = estilo.etiqueta(t("render_final.titulo"))
        self.titulo.setStyleSheet("font-weight: 600;")
        capa.addWidget(self.titulo)
        self.barra = QtWidgets.QProgressBar()
        self.barra.setRange(0, 1000)
        self.barra.setTextVisible(False)
        self.barra.setFixedHeight(8)
        capa.addWidget(self.barra)
        self.texto = estilo.etiqueta("", "tenue", ajuste=True)
        capa.addWidget(self.texto)
        fila = QtWidgets.QHBoxLayout()
        fila.setSpacing(6)
        self.boton_carpeta = QtWidgets.QPushButton(t("render_final.abrir_carpeta"))
        self.boton_carpeta.clicked.connect(self.abrir_carpeta.emit)
        self.boton_cancelar = QtWidgets.QPushButton(t("render_final.cancelar"))
        self.boton_cancelar.clicked.connect(self.cancelar.emit)
        self.boton_cerrar = QtWidgets.QPushButton(t("boton.cerrar"))
        self.boton_cerrar.clicked.connect(self.hide)
        fila.addWidget(self.boton_carpeta)
        fila.addStretch(1)
        fila.addWidget(self.boton_cancelar)
        fila.addWidget(self.boton_cerrar)
        capa.addLayout(fila)
        self.hide()

    def empezar(self, total):
        self.titulo.setText(t("render_final.titulo"))
        self.barra.setValue(0)
        self.texto.setText(t("render_final.preparando", total=total))
        self.boton_cancelar.setVisible(True)
        self.boton_cerrar.setVisible(False)
        self.show()

    def progreso(self, hechos, total, porcentaje, restante=None):
        parte = (hechos + porcentaje / 100.0) / float(max(1, total))
        self.barra.setValue(int(round(1000 * min(1.0, parte))))
        actual = min(total, hechos + 1)
        texto = t("render_final.progreso", actual=actual, total=total, pct=porcentaje)
        if restante is not None and (hechos or porcentaje >= 5):
            texto += " · " + t("render_final.quedan", tiempo=texto_duracion(restante))
        self.texto.setText(texto)

    def terminar(self, bien, texto):
        self.titulo.setText(t("render_final.fin." + ("bien" if bien else "mal")))
        if bien:
            self.barra.setValue(1000)
        self.texto.setText(texto)
        self.boton_cancelar.setVisible(False)
        self.boton_cerrar.setVisible(True)
