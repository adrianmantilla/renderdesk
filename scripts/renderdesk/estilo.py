"""Estilo común de las ventanas del pack MantiTools (la línea de Materials).

Este archivo es el mismo en todas las herramientas del pack: el original está en
``mantitools/estilo.py`` y las copias se comprueban con las pruebas de MantiTools.
Si lo cambias, cámbialo allí y cópialo.

Uso::

    from <herramienta> import estilo
    estilo.aplicar(ventana, "TrepadoraVentana")     # hoja de estilo acotada a la ventana
    estilo.rol(boton, "primario")                   # botón azul de la acción principal
    estilo.rol(etiqueta, "seccion")                 # título de sección
    estilo.paso(1, "Elige la superficie")           # círculo numerado + texto

Todo va acotado al nombre de objeto de la ventana para no cambiar el resto de Maya.
Los papeles se marcan con la propiedad dinámica ``rol``: ``primario``, ``segmento``
(con ``lado`` izq/der), ``peligro``, ``tenue``, ``titulo``, ``seccion``, ``chip``,
``paso``, ``aviso``, ``bien``, ``tarjeta``, ``cabecera`` y ``franja``.
"""

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ImportError:  # pragma: no cover - Maya 2024 o anterior
    from PySide2 import QtCore, QtGui, QtWidgets

Qt = QtCore.Qt

ACENTO = "#4a9bd1"
ACENTO_OSCURO = "#3579a8"
FONDO = "#444444"
FONDO_TARJETA = "#3a3a3a"
FONDO_CAMPO = "#2b2b2b"
BORDE = "#262626"
TEXTO = "#e2e2e2"
TENUE = "#9c9c9c"

# Color de cada herramienta del pack (icono del estante, tarjeta y cabecera).
COLORES = {
    "trepadora": "#3fae8c", "arboles": "#b07a48", "radial": "#a58bd6", "muro": "#e8c04f",
    "materials": "#e0685a", "grasseditor": "#a8cf5a", "simplesave": "#e88fb8", "mantitools": ACENTO,
}

HOJA = """
%(raiz)s { background: #444444; }
%(raiz)s QLabel { color: %(texto)s; }
%(raiz)s QLabel[rol="tenue"] { color: %(tenue)s; }
%(raiz)s QLabel[rol="titulo"] { font-size: 13pt; font-weight: 600; color: #f2f2f2; }
%(raiz)s QLabel[rol="seccion"] { color: #8fc0e3; font-weight: 600; padding-top: 6px; }
%(raiz)s QLabel[rol="chip"] { border-radius: 8px; padding: 1px 8px; font-size: 8.5pt; font-weight: 600; }
%(raiz)s QLabel[rol="paso"] { background: %(acento)s; color: white; border-radius: 10px;
    min-width: 20px; max-width: 20px; min-height: 20px; max-height: 20px; font-weight: 700; qproperty-alignment: AlignCenter; }

%(raiz)s QFrame[rol="tarjeta"] { background: %(tarjeta)s; border: 1px solid #333333; border-radius: 8px; }
%(raiz)s QFrame[rol="cabecera"] { background: #3b3b3b; border-bottom: 1px solid #303030; }

%(raiz)s QTabWidget::pane { border: none; border-top: 1px solid #353535; top: -1px; }
%(raiz)s QTabBar::tab { background: transparent; color: #a8a8a8; padding: 7px 14px; border: none;
    border-bottom: 2px solid transparent; margin-right: 2px; }
%(raiz)s QTabBar::tab:selected { color: #ffffff; border-bottom: 2px solid %(acento)s; }
%(raiz)s QTabBar::tab:hover:!selected { color: #dddddd; border-bottom: 2px solid #5a5a5a; }

%(raiz)s QPushButton { background: #575757; color: #eeeeee; border: 1px solid #303030;
    border-radius: 5px; padding: 5px 12px; }
%(raiz)s QPushButton:hover { background: #636363; }
%(raiz)s QPushButton:pressed { background: #4b4b4b; }
%(raiz)s QPushButton:disabled { background: #4a4a4a; color: #858585; }
%(raiz)s QPushButton[rol="primario"] { background: %(acento)s; border: 1px solid %(acento_oscuro)s;
    color: white; font-weight: 600; padding: 7px 12px; }
%(raiz)s QPushButton[rol="primario"]:hover { background: #5aa9de; }
%(raiz)s QPushButton[rol="primario"]:pressed { background: %(acento_oscuro)s; }
%(raiz)s QPushButton[rol="primario"]:disabled { background: #4a4a4a; color: #858585; border-color: #303030; }
%(raiz)s QPushButton[rol="icono"] { padding: 2px 4px; }
%(raiz)s QToolButton::menu-button { border: none; background: transparent; width: 16px; }
%(raiz)s QScrollArea, %(raiz)s QScrollArea > QWidget > QWidget { background: transparent; }

%(raiz)s QToolButton[rol="segmento"] { background: #383838; color: #bbbbbb; border: 1px solid #2c2c2c;
    padding: 5px 14px; font-weight: 600; }
%(raiz)s QToolButton[rol="segmento"][lado="izq"] { border-top-left-radius: 6px; border-bottom-left-radius: 6px; }
%(raiz)s QToolButton[rol="segmento"][lado="der"] { border-top-right-radius: 6px; border-bottom-right-radius: 6px;
    border-left: none; }
%(raiz)s QToolButton[rol="segmento"]:hover:!checked { background: #424242; color: #e0e0e0; }
%(raiz)s QToolButton[rol="segmento"]:checked { background: %(acento)s; color: white; border-color: %(acento_oscuro)s; }
%(raiz)s QToolButton { border-radius: 4px; padding: 3px 8px; }

%(raiz)s QLineEdit, %(raiz)s QComboBox, %(raiz)s QDoubleSpinBox,
%(raiz)s QPlainTextEdit { background: %(campo)s; color: %(texto)s; border: 1px solid %(borde)s;
    border-radius: 5px; padding: 4px 6px; selection-background-color: %(acento)s; }
%(raiz)s QLineEdit:focus, %(raiz)s QDoubleSpinBox:focus, %(raiz)s QComboBox:focus
    { border: 1px solid %(acento)s; }
%(raiz)s QComboBox::drop-down { border: none; width: 18px; }
%(raiz)s QDoubleSpinBox::up-button, %(raiz)s QDoubleSpinBox::down-button { width: 0px; border: none; }

%(raiz)s QListWidget, %(raiz)s QTreeWidget, %(raiz)s QTableWidget {
    background: #363636; color: %(texto)s; border: 1px solid #2e2e2e; border-radius: 8px; outline: none; }
%(raiz)s QHeaderView::section { background: #3d3d3d; color: #bdbdbd; border: none;
    border-bottom: 1px solid #2c2c2c; padding: 5px 6px; font-weight: 600; }
%(raiz)s QTableWidget { gridline-color: #3e3e3e; }
%(raiz)s QTableWidget::item:selected, %(raiz)s QTreeWidget::item:selected,
%(raiz)s QListWidget::item:selected { background: %(acento_oscuro)s; color: white; }
%(raiz)s QSlider::groove:horizontal { height: 4px; background: #2a2a2a; border-radius: 2px; }
%(raiz)s QSlider::sub-page:horizontal { background: %(acento)s; border-radius: 2px; }
%(raiz)s QSlider::handle:horizontal { background: #ececec; width: 14px; height: 14px; margin: -5px 0;
    border-radius: 7px; border: 1px solid #2a2a2a; }
%(raiz)s QSlider::handle:horizontal:hover { background: #ffffff; }

%(raiz)s QCheckBox { color: %(texto)s; spacing: 7px; }
%(raiz)s QCheckBox::indicator, %(raiz)s QGroupBox::indicator { width: 14px; height: 14px;
    border-radius: 3px; border: 1px solid #222; background: %(campo)s; }
%(raiz)s QCheckBox::indicator:checked, %(raiz)s QGroupBox::indicator:checked
    { background: %(acento)s; border-color: %(acento_oscuro)s; }

%(raiz)s QGroupBox { border: 1px solid #353535; border-radius: 8px; margin-top: 12px; padding-top: 8px;
    background: #3e3e3e; }
%(raiz)s QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #cfcfcf; }

%(raiz)s QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
%(raiz)s QScrollBar::handle:vertical { background: #5a5a5a; border-radius: 4px; min-height: 30px; }
%(raiz)s QScrollBar::handle:vertical:hover { background: #6a6a6a; }
%(raiz)s QScrollBar::add-line, %(raiz)s QScrollBar::sub-line { height: 0; width: 0; }
%(raiz)s QScrollBar::add-page, %(raiz)s QScrollBar::sub-page { background: transparent; }
%(raiz)s QSplitter::handle { background: transparent; }
%(raiz)s QSpinBox { background: %(campo)s; color: %(texto)s; border: 1px solid %(borde)s; border-radius: 5px;
    padding: 4px 6px; }
%(raiz)s QSpinBox::up-button, %(raiz)s QSpinBox::down-button { width: 0px; border: none; }
%(raiz)s QRadioButton { color: %(texto)s; spacing: 7px; }
%(raiz)s QLabel[rol="aviso"] { color: #f0c060; }
%(raiz)s QLabel[rol="bien"] { color: #7ccf98; }
%(raiz)s QFrame[rol="franja"] { border: none; min-height: 3px; max-height: 3px; }
%(raiz)s QPushButton[rol="peligro"] { background: #6a3b3b; border: 1px solid #4a2626; }
%(raiz)s QPushButton[rol="peligro"]:hover { background: #7a4545; }
%(raiz)s QMenu { background: #3d3d3d; color: %(texto)s; border: 1px solid #222; }
%(raiz)s QMenu::item:selected { background: %(acento_oscuro)s; }
%(raiz)s QToolTip { background: #2b2b2b; color: %(texto)s; border: 1px solid #222; }
"""


def hoja(nombre_objeto):
    """La hoja de estilo acotada a ``#nombre_objeto``."""
    return HOJA % {"raiz": "#" + nombre_objeto, "acento": ACENTO, "acento_oscuro": ACENTO_OSCURO,
                   "tarjeta": FONDO_TARJETA, "campo": FONDO_CAMPO, "borde": BORDE, "texto": TEXTO,
                   "tenue": TENUE}


def aplicar(widget, nombre_objeto):
    """Da a ``widget`` su nombre de objeto y la hoja de estilo. Devuelve el widget."""
    widget.setObjectName(nombre_objeto)
    widget.setAttribute(QtCore.Qt.WA_StyledBackground, True)  # que pinte su fondo aunque sea un QWidget
    widget.setStyleSheet(hoja(nombre_objeto))
    return widget


def rol(widget, nombre, **extra):
    """Marca un widget con un papel de la hoja de estilo (y propiedades extra)."""
    widget.setProperty("rol", nombre)
    for clave, valor in extra.items():
        widget.setProperty(clave, valor)
    estilo = widget.style()
    if estilo is not None:  # por si la hoja ya estaba puesta: que se vuelva a mirar el papel
        estilo.unpolish(widget)
        estilo.polish(widget)
    return widget


def etiqueta(texto, papel=None, ajuste=False):
    e = QtWidgets.QLabel(texto)
    if papel:
        rol(e, papel)
    e.setWordWrap(ajuste)
    return e


def formulario(padre=None):
    """QFormLayout igual en Windows y Mac.

    En macOS Qt deja los campos a su tamaño mínimo (FieldsStayAtSizeHint): las etiquetas
    con ajuste de línea se quedan estrechas y el texto se monta sobre la fila siguiente.
    """
    f = QtWidgets.QFormLayout(padre) if padre is not None else QtWidgets.QFormLayout()
    f.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
    f.setRowWrapPolicy(QtWidgets.QFormLayout.DontWrapRows)
    f.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    f.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
    return f


def tarjeta(margenes=10, espacio=6):
    """Marco redondeado con su capa vertical."""
    marco = QtWidgets.QFrame()
    rol(marco, "tarjeta")
    capa = QtWidgets.QVBoxLayout(marco)
    capa.setContentsMargins(margenes, margenes, margenes, margenes)
    capa.setSpacing(espacio)
    return marco, capa


def chip(texto, color, fondo_alfa=60):
    """Etiqueta en forma de píldora con el color dado."""
    c = QtGui.QColor(color)
    e = etiqueta(texto, "chip")
    e.setStyleSheet("background: rgba({},{},{},{}); color: {};".format(c.red(), c.green(), c.blue(), fondo_alfa,
                                                                      c.lighter(130).name()))
    return e


def punto(color, lado=10):
    """Círculo de color (el de la herramienta) como QLabel."""
    e = QtWidgets.QLabel()
    e.setFixedSize(lado, lado)
    e.setStyleSheet("background: {}; border-radius: {}px;".format(color, lado // 2))
    return e


def cabecera(titulo, color=None, version=None):
    """Barra de cabecera como la de Materials: punto de color, título y versión a la derecha.

    Devuelve (marco, fila): en ``fila`` se pueden añadir más controles antes de la versión
    con ``fila.insertWidget(fila.count() - 2, widget)``.
    """
    marco = QtWidgets.QFrame()
    rol(marco, "cabecera")
    fila = QtWidgets.QHBoxLayout(marco)
    fila.setContentsMargins(10, 8, 10, 8)
    fila.setSpacing(8)
    if color:
        fila.addWidget(punto(color, 12))
    fila.addWidget(etiqueta(titulo, "titulo"))
    fila.addStretch(1)
    fila.addWidget(etiqueta("v" + version if version else "", "tenue"))
    return marco, fila


def paso(numero, texto):
    """Fila con el círculo azul numerado y el texto del paso, como en Materials."""
    fila = QtWidgets.QWidget()
    capa = QtWidgets.QHBoxLayout(fila)
    capa.setContentsMargins(0, 0, 0, 0)
    capa.setSpacing(8)
    capa.addWidget(etiqueta(str(numero), "paso"))
    titulo = etiqueta(texto)
    titulo.setStyleSheet("font-weight: 600;")
    capa.addWidget(titulo, 1)
    return fila


def primario(boton):
    """Marca el botón de la acción principal (azul)."""
    return rol(boton, "primario")
