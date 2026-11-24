"""Combinación de presets: calidad + tipo de escena + extras + salida.

Python puro, sin Maya. Los datos viven en la carpeta ``presets/`` como JSON,
así que añadir o ajustar un preset no pide tocar este código.

    >>> from renderdesk import presets
    >>> v = presets.combinar("final", "interior", ["vidrio"])
    >>> v["tD"]
    12
"""

import json
import os

_CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "presets")
_cache = {}

OPERACIONES = ("poner", "sumar", "al_menos", "como_mucho")


def _leer(nombre):
    if nombre not in _cache:
        with open(os.path.join(_CARPETA, nombre + ".json"), encoding="utf-8") as f:
            _cache[nombre] = json.load(f)
    return _cache[nombre]


def catalogo():
    """Diccionario clave -> definición del ajuste (tipo, candidatos, fábrica, límites)."""
    return _leer("atributos")["ajustes"]


def orden_ajustes():
    return list(_leer("atributos")["orden"])


def calidades():
    return list(_leer("calidades")["orden"])


def escenas():
    return list(_leer("escenas")["orden"])


def extras():
    return list(_leer("extras")["orden"])


def salidas():
    return list(_leer("salidas")["orden"])


def fabrica():
    """Valores con los que Arnold viene de fábrica."""
    return {clave: d["fabrica"] for clave, d in catalogo().items()}


def ajustar_tipo(clave, valor):
    """Convierte ``valor`` al tipo del ajuste y lo encaja entre su mínimo y su máximo."""
    d = catalogo()[clave]
    if d["tipo"] == "bool":
        return 1 if valor else 0
    valor = float(valor)
    if "min" in d:
        valor = max(d["min"], valor)
    if "max" in d:
        valor = min(d["max"], valor)
    return int(round(valor)) if d["tipo"] == "int" else round(valor, 4)


def _aplica(regla, calidad):
    if calidad in regla.get("salvo", ()):
        return False
    solo = regla.get("solo")
    return not solo or calidad in solo


def aplicar_reglas(valores, reglas, calidad):
    """Aplica una lista de reglas sobre ``valores`` (se modifica y se devuelve)."""
    for regla in reglas:
        if not _aplica(regla, calidad):
            continue
        clave, op, v = regla["clave"], regla["op"], regla["valor"]
        if op not in OPERACIONES:
            raise ValueError("Operación desconocida: {}".format(op))
        actual = valores.get(clave, catalogo()[clave]["fabrica"])
        if op == "poner":
            nuevo = v
        elif op == "sumar":
            nuevo = actual + v
        elif op == "al_menos":
            nuevo = max(actual, v)
        else:
            nuevo = min(actual, v)
        valores[clave] = ajustar_tipo(clave, nuevo)
    return valores


def _derivados(valores):
    """Valores que dependen de otros: el total de rebotes nunca debe recortar a los demás."""
    necesario = max(valores["dD"] + valores["sD"], valores["tD"]) + 2
    valores["total"] = ajustar_tipo("total", max(valores.get("total", 10), necesario))
    return valores


def combinar(calidad="revision", escena="producto", con_extras=(), salida="fija", cambios=None):
    """Devuelve el diccionario completo de ajustes para esa combinación.

    ``cambios`` son retoques a mano (nivel Detalle o Experto) que se ponen encima
    del preset, después de todas las reglas. El total de rebotes se recalcula con
    ellos, salvo que el propio total sea uno de los retoques.
    """
    if calidad not in calidades():
        raise KeyError("Calidad desconocida: {}".format(calidad))
    if escena not in escenas():
        raise KeyError("Tipo de escena desconocido: {}".format(escena))
    valores = fabrica()
    valores.update(_leer("calidades")["calidades"][calidad]["valores"])
    aplicar_reglas(valores, _leer("escenas")["escenas"][escena]["reglas"], calidad)
    for extra in extras():                       # siempre en el mismo orden
        if extra in con_extras:
            aplicar_reglas(valores, _leer("extras")["extras"][extra]["reglas"], calidad)
    desconocidos = set(con_extras) - set(extras())
    if desconocidos:
        raise KeyError("Extras desconocidos: {}".format(", ".join(sorted(desconocidos))))
    aplicar_reglas(valores, _leer("salidas")["salidas"][salida]["reglas"], calidad)
    cambios = cambios or {}
    for clave, v in cambios.items():
        valores[clave] = ajustar_tipo(clave, v)
    if "total" not in cambios:          # el total sigue a los rebotes salvo que se toque a mano
        _derivados(valores)
    return valores


def diferencias(antes, despues):
    """Lista de (clave, antes, después) de los ajustes que cambian, en el orden del panel."""
    return [(c, antes.get(c), despues.get(c)) for c in orden_ajustes()
            if c in despues and antes.get(c) != despues.get(c)]


def nombre(calidad, escena, modificado=False):
    """Texto corto del preset para la barra: «Final · Interior (modificado)»."""
    from .i18n import t
    texto = "{} · {}".format(t("calidad." + calidad), t("escena." + escena))
    return texto + (" " + t("preset.modificado") if modificado else "")
