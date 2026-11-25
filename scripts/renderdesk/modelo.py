"""Lo que el panel tiene elegido, sin Maya ni Qt (se prueba con unittest).

Una ``Seleccion`` es el preset (calidad + tipo de escena + extras + salida) y los
retoques a mano de los niveles Detalle y Experto. Si la escena todavía no usa
ningún preset, ``calidad`` es None y los retoques van sobre los ajustes que ya
tenía la escena (``base``).
"""

from . import presets
from .i18n import t

NIVELES = ("sencillo", "detalle", "experto")

# Ajustes que salen en el nivel Detalle, con el tope de su deslizador. El nivel
# Experto enseña todos los del catálogo, con sus límites completos.
DETALLE = (
    ("aa", 10), ("diff", 6), ("spec", 6), ("trans", 6), ("sss", 6), ("vol", 6),
    ("dD", 6), ("sD", 6), ("tD", 16), ("vD", 4), ("at", 32), ("clamp", 20),
    ("den", None), ("mb", None), ("res", 100),
)

# Tamaños de la barra superior: (clave, ancho, alto).
TAMANOS = (
    ("hd1080", 1920, 1080),
    ("hd720", 1280, 720),
    ("uhd", 3840, 2160),
    ("cuadrado", 1080, 1080),
    ("vertical", 1080, 1920),
)


def tamano_de(ancho, alto):
    """Clave del tamaño que coincide con ``ancho`` × ``alto``, o None si es otro."""
    for clave, a, b in TAMANOS:
        if (a, b) == (int(ancho), int(alto)):
            return clave
    return None


def texto_tamano(clave=None, ancho=None, alto=None):
    """«HD 1080 · 1920 × 1080», o «Escena · 1500 × 900» si no es de la lista."""
    if clave:
        for c, a, b in TAMANOS:
            if c == clave:
                return t("tamano." + c, ancho=a, alto=b)
    return t("tamano.otro", ancho=ancho, alto=alto)


class Seleccion(object):
    def __init__(self, calidad=None, escena="producto", extras=(), salida="fija", cambios=None, base=None):
        self.calidad = calidad
        self.escena = escena
        self.extras = [e for e in presets.extras() if e in extras]
        self.salida = salida
        self.cambios = dict(cambios or {})
        self.base = dict(base or {})

    # ----- valores -----

    def hay_preset(self):
        return self.calidad is not None

    def del_preset(self):
        """Valores del preset (o de la escena) sin los retoques a mano."""
        if self.hay_preset():
            return presets.combinar(self.calidad, self.escena, self.extras, self.salida)
        valores = presets.fabrica()
        valores.update(self.base)
        return valores

    def valores(self):
        """Valores completos que se escriben en la escena."""
        if self.hay_preset():
            return presets.combinar(self.calidad, self.escena, self.extras, self.salida, self.cambios)
        valores = self.del_preset()
        for clave, v in self.cambios.items():
            valores[clave] = presets.ajustar_tipo(clave, v)
        return valores

    def modificado(self):
        return bool(self.cambios)

    def retocados(self):
        """Claves cuyo valor final difiere del preset por un retoque a mano."""
        antes, ahora = self.del_preset(), self.valores()
        return [c for c in presets.orden_ajustes() if c in self.cambios or antes.get(c) != ahora.get(c)]

    def nombre(self):
        if not self.hay_preset():
            return t("preset.escena") + (" " + t("preset.modificado") if self.modificado() else "")
        return presets.nombre(self.calidad, self.escena, self.modificado())

    # ----- cambios desde el panel -----

    def elegir_calidad(self, calidad):
        """Cambiar de calidad deja los retoques: siguen encima del nuevo preset."""
        self.calidad = calidad

    def elegir_escena(self, escena):
        self.escena = escena

    def poner_extra(self, extra, activo):
        conjunto = set(self.extras)
        if activo:
            conjunto.add(extra)
        else:
            conjunto.discard(extra)
        self.extras = [e for e in presets.extras() if e in conjunto]

    def retocar(self, clave, valor):
        """Retoque a mano. Si vuelve al valor del preset, deja de contar como retoque."""
        valor = presets.ajustar_tipo(clave, valor)
        if self.del_preset().get(clave) == valor:
            self.cambios.pop(clave, None)
        else:
            self.cambios[clave] = valor

    def volver_al_preset(self):
        self.cambios = {}

    def adoptar_de_escena(self, valores_escena, esperados):
        """Recoge los cambios hechos fuera del panel (Render Settings, Attribute Editor).

        ``esperados`` son los valores que el panel escribió la última vez: lo que
        difiera de ellos lo ha cambiado otra persona o ventana. Devuelve las claves
        adoptadas.
        """
        adoptadas = []
        for clave, valor in valores_escena.items():
            if clave in esperados and esperados[clave] != valor:
                self.retocar(clave, valor)
                adoptadas.append(clave)
        return adoptadas

    # ----- guardar en la escena -----

    def a_dict(self):
        return {"calidad": self.calidad, "escena": self.escena, "extras": list(self.extras),
                "salida": self.salida, "cambios": dict(self.cambios)}

    @classmethod
    def de_dict(cls, datos, base=None):
        datos = datos or {}
        calidad = datos.get("calidad")
        if calidad not in presets.calidades():
            calidad = None
        escena = datos.get("escena") if datos.get("escena") in presets.escenas() else "producto"
        salida = datos.get("salida") if datos.get("salida") in presets.salidas() else "fija"
        cambios = {c: v for c, v in (datos.get("cambios") or {}).items() if c in presets.catalogo()}
        return cls(calidad, escena, datos.get("extras") or (), salida, cambios, base=base)


def cambios_frente_a_fabrica(valores):
    """[(clave, fábrica, ahora)] de lo que cambia respecto a Arnold recién instalado."""
    return presets.diferencias(presets.fabrica(), valores)


def texto_valor(clave, valor):
    """Valor legible: «sí/no», «50 %», o el número sin decimales de sobra."""
    d = presets.catalogo()[clave]
    if valor is None:
        return "—"
    if d["tipo"] == "bool":
        return t("valor.si") if valor else t("valor.no")
    if clave == "res":
        return "{} %".format(int(valor))
    if d["tipo"] == "float":
        return ("%g" % round(float(valor), 4)).replace(".", ",")
    return str(int(valor))
