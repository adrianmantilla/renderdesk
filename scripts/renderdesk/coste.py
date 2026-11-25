"""Estimación del coste de un render a partir de los ajustes (Python puro).

Arnold lanza, por cada píxel, AA² rayos de cámara, y por cada uno de ellos
muestras² rayos de cada tipo. La cuenta da una idea de cuánto trabaja Arnold;
el tiempo real lo mide la prueba (``estimar_final``).
"""


def rayos_por_pixel(v, con_extras=()):
    """Rayos aproximados por píxel con los ajustes ``v``."""
    por_camara = 1 + v["diff"] ** 2 * (0.6 + 0.4 * v["dD"]) + v["spec"] ** 2 * (0.5 + 0.25 * v["sD"])
    if "vidrio" in con_extras:
        por_camara += v["trans"] ** 2 * (1 + v["tD"] / 12.0)
    if "sss" in con_extras:
        por_camara += v["sss"] ** 2 * 1.2
    if "niebla" in con_extras:
        por_camara += v["vol"] ** 2 * 1.5
    return v["aa"] ** 2 * por_camara


def coste_relativo(v, con_extras=(), escena="producto"):
    """Trabajo total en unidades arbitrarias, para comparar dos ajustes entre sí."""
    c = rayos_por_pixel(v, con_extras) * (v.get("res", 100) / 100.0) ** 2
    if v.get("adapt"):
        c *= 1.5
    if v.get("mb"):
        c *= 1.25
    if escena == "interior":
        c *= 1.3
    return c


def estimar_final(segundos_prueba, v_prueba, v_final, con_extras=(), escena="producto",
                  fraccion_area=1.0, fotogramas=1):
    """Segundos que tardará el final, sacados del tiempo real de una prueba.

    ``fraccion_area`` es la parte de la imagen que renderizó la prueba (1 si no era
    una región). La relación entre los dos costes corrige el cambio de ajustes.
    """
    if segundos_prueba <= 0 or fraccion_area <= 0:
        return 0.0
    completo = segundos_prueba / fraccion_area
    relacion = coste_relativo(v_final, con_extras, escena) / max(coste_relativo(v_prueba, con_extras, escena), 1e-9)
    return completo * relacion * max(1, fotogramas)


def texto_duracion(segundos):
    """«45 s», «4 min», «1 h 20 min»."""
    s = int(round(segundos))
    if s < 60:
        return "{} s".format(s)
    m = int(round(s / 60.0))
    if m < 60:
        return "{} min".format(m)
    h, m = divmod(m, 60)
    return "{} h {} min".format(h, m) if m else "{} h".format(h)
