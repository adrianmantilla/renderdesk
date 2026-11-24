"""Historial de pruebas en el panel: tira de instantáneas y comparación A/B."""

from renderdesk import estilo
from renderdesk.i18n import t
from renderdesk.qt import QtCore, QtGui, QtWidgets
from renderdesk.coste import texto_duracion

Qt = QtCore.Qt
ROL_ENTRADA = Qt.UserRole + 1
ICONO = QtCore.QSize(96, 54)


def texto_entrada(entrada):
    """«#3 · 14 s» (o «#3 · 23:41» si no hay tiempo medido)."""
    numero = "#{}".format(entrada.get("numero", "?"))
    if entrada.get("segundos"):
        return "{} · {}".format(numero, texto_duracion(entrada["segundos"]))
    return "{} · {}".format(numero, entrada.get("hora", ""))


def ayuda_entrada(entrada):
    tam = entrada.get("tamano") or ("?", "?")
    return t("historial.ayuda_entrada", preset=entrada.get("preset", ""), hora=entrada.get("hora", ""),
             camara=entrada.get("camara", ""), ancho=tam[0], alto=tam[1],
             tiempo=texto_duracion(entrada["segundos"]) if entrada.get("segundos") else "—")


class VistaAB(QtWidgets.QWidget):
    """Dos imágenes una sobre otra: A a la izquierda del corte y B a la derecha. Se arrastra el corte."""

    def __init__(self, imagen_a, imagen_b, texto_a, texto_b, padre=None):
        super(VistaAB, self).__init__(padre)
        self.a, self.b = QtGui.QImage(imagen_a), QtGui.QImage(imagen_b)
        self.texto_a, self.texto_b = texto_a, texto_b
        self.corte = 0.5
        self.setMinimumSize(320, 200)
        self.setCursor(Qt.SplitHCursor)

    def _caja(self):
        referencia = self.a if not self.a.isNull() else self.b
        if referencia.isNull():
            return QtCore.QRectF(self.rect())
        tam = QtCore.QSizeF(referencia.size())
        tam.scale(QtCore.QSizeF(self.size()), Qt.KeepAspectRatio)
        return QtCore.QRectF((self.width() - tam.width()) / 2.0, (self.height() - tam.height()) / 2.0,
                             tam.width(), tam.height())

    def poner_corte(self, x):
        caja = self._caja()
        self.corte = min(1.0, max(0.0, (x - caja.left()) / max(1.0, caja.width())))
        self.update()

    def mousePressEvent(self, evento):
        self.poner_corte(evento.position().x() if hasattr(evento, "position") else evento.pos().x())

    def mouseMoveEvent(self, evento):
        self.poner_corte(evento.position().x() if hasattr(evento, "position") else evento.pos().x())

    def paintEvent(self, _evento):
        pintor = QtGui.QPainter(self)
        pintor.fillRect(self.rect(), QtGui.QColor("#2b2b2b"))
        pintor.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        caja = self._caja()
        if not self.b.isNull():
            pintor.drawImage(caja, self.b)
        x = caja.left() + caja.width() * self.corte
        if not self.a.isNull():
            pintor.save()
            pintor.setClipRect(QtCore.QRectF(caja.left(), caja.top(), x - caja.left(), caja.height()))
            pintor.drawImage(caja, self.a)
            pintor.restore()
        pintor.setPen(QtGui.QPen(QtGui.QColor(estilo.ACENTO), 2))
        pintor.drawLine(QtCore.QPointF(x, caja.top()), QtCore.QPointF(x, caja.bottom()))
        for texto, izquierda in ((self.texto_a, True), (self.texto_b, False)):
            metricas = pintor.fontMetrics()
            ancho = metricas.horizontalAdvance(texto) + 14
            alto = metricas.height() + 6
            rx = caja.left() + 8 if izquierda else caja.right() - ancho - 8
            etiqueta = QtCore.QRectF(rx, caja.top() + 8, ancho, alto)
            pintor.setPen(Qt.NoPen)
            pintor.setBrush(QtGui.QColor(0, 0, 0, 160))
            pintor.drawRoundedRect(etiqueta, alto / 2.0, alto / 2.0)
            pintor.setPen(QtGui.QColor("#eeeeee"))
            pintor.drawText(etiqueta, Qt.AlignCenter, texto)
        pintor.end()


class CompararAB(QtWidgets.QDialog):
    def __init__(self, imagen_a, imagen_b, texto_a, texto_b, padre=None):
        super(CompararAB, self).__init__(padre)
        self.setWindowTitle(t("comparar.titulo"))
        estilo.aplicar(self, "RenderDeskComparar")
        capa = QtWidgets.QVBoxLayout(self)
        self.vista = VistaAB(imagen_a, imagen_b, texto_a, texto_b)
        capa.addWidget(self.vista, 1)
        fila = QtWidgets.QHBoxLayout()
        fila.addWidget(estilo.etiqueta(t("comparar.ayuda"), "tenue"), 1)
        cerrar = QtWidgets.QPushButton(t("boton.cerrar"))
        cerrar.clicked.connect(self.close)
        fila.addWidget(cerrar)
        capa.addLayout(fila)
        self.resize(960, 620)


class TiraHistorial(QtWidgets.QWidget):
    """Lista horizontal de instantáneas con los botones Comparar, Recuperar y Borrar."""
    comparar = QtCore.Signal(list)
    recuperar = QtCore.Signal(dict)
    borrar = QtCore.Signal(list)

    def __init__(self, padre=None):
        super(TiraHistorial, self).__init__(padre)
        capa = QtWidgets.QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.setSpacing(4)
        self.lista = QtWidgets.QListWidget()
        self.lista.setViewMode(QtWidgets.QListView.IconMode)
        self.lista.setFlow(QtWidgets.QListView.LeftToRight)
        self.lista.setWrapping(False)
        self.lista.setMovement(QtWidgets.QListView.Static)
        self.lista.setIconSize(ICONO)
        self.lista.setSpacing(3)
        self.lista.setFixedHeight(ICONO.height() + 40)
        self.lista.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.lista.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.lista.itemSelectionChanged.connect(self._al_seleccionar)
        self.lista.itemDoubleClicked.connect(lambda item: self.comparar.emit([item.data(ROL_ENTRADA)]))
        capa.addWidget(self.lista)
        self.vacio = estilo.etiqueta(t("historial.vacio"), "tenue", ajuste=True)
        capa.addWidget(self.vacio)
        fila = QtWidgets.QHBoxLayout()
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(6)
        self.boton_comparar = QtWidgets.QPushButton(t("historial.comparar"))
        self.boton_comparar.setToolTip(t("historial.comparar.ayuda"))
        self.boton_comparar.clicked.connect(lambda: self.comparar.emit(self.seleccionadas()))
        self.boton_recuperar = QtWidgets.QPushButton(t("historial.recuperar"))
        self.boton_recuperar.setToolTip(t("historial.recuperar.ayuda"))
        self.boton_recuperar.clicked.connect(self._al_recuperar)
        self.boton_borrar = QtWidgets.QPushButton(t("historial.borrar"))
        self.boton_borrar.clicked.connect(lambda: self.borrar.emit(self.seleccionadas()))
        fila.addWidget(self.boton_comparar)
        fila.addWidget(self.boton_recuperar)
        fila.addStretch(1)
        fila.addWidget(self.boton_borrar)
        self.fila_botones = QtWidgets.QWidget()
        self.fila_botones.setLayout(fila)
        capa.addWidget(self.fila_botones)
        self.poner([])

    def poner(self, entradas):
        elegidas = set(e.get("numero") for e in self.seleccionadas())
        self.lista.blockSignals(True)
        self.lista.clear()
        for entrada in entradas:
            item = QtWidgets.QListWidgetItem(texto_entrada(entrada))
            imagen = QtGui.QImage(entrada.get("ruta_imagen") or "")
            if not imagen.isNull():
                mapa = QtGui.QPixmap.fromImage(imagen.scaled(ICONO * 2, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                item.setIcon(QtGui.QIcon(mapa))
            item.setToolTip(ayuda_entrada(entrada))
            item.setData(ROL_ENTRADA, entrada)
            self.lista.addItem(item)
            if entrada.get("numero") in elegidas:
                item.setSelected(True)
        self.lista.blockSignals(False)
        hay = bool(entradas)
        self.lista.setVisible(hay)
        self.fila_botones.setVisible(hay)
        self.vacio.setVisible(not hay)
        self._al_seleccionar()

    def seleccionadas(self):
        return [item.data(ROL_ENTRADA) for item in self.lista.selectedItems()]

    def _al_seleccionar(self):
        n = len(self.lista.selectedItems())
        self.boton_comparar.setEnabled(n in (1, 2))
        self.boton_comparar.setText(t("historial.comparar_dos") if n == 2 else t("historial.comparar"))
        self.boton_recuperar.setEnabled(n == 1)
        self.boton_borrar.setEnabled(n >= 1)

    def _al_recuperar(self):
        elegidas = self.seleccionadas()
        if len(elegidas) == 1:
            self.recuperar.emit(elegidas[0])
