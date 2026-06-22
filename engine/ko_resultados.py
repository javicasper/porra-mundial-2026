"""Construye la parte de ELIMINATORIAS del esquema de resultados de la porra,
a partir de los partidos reales (formato de build_web_data) y la clasificación
de grupos, para alimentar el motor de puntuación (engine/scoring.py).

Regla de la porra (confirmada en el Excel oficial): el marcador de un cruce se
puntúa POR EQUIPOS — la pareja que pronosticaste tiene que enfrentarse de verdad
en esa ronda (da igual el orden local/visitante y da igual la posición en el
cuadro); si ese enfrentamiento no existe, no suma marcador. Por eso aquí NO hay
mapeo de slots ni topología del cuadro: para cada ronda basta con la LISTA de
partidos reales (equipos + marcador), y el casado por equipos lo hace el motor
(scoring.buscar_cruce). Los "clasificados" por ronda son un criterio aparte (por
equipo). Todo degrada con elegancia: lo que aún no se conoce queda a [] / None.
"""
from __future__ import annotations
import unicodedata


def _norm(s):
    if s is None:
        return None
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().strip().lower()


def _signo(h, a):
    return "1" if h > a else ("2" if a > h else "X")


def _equipos_en(partidos):
    """Equipos presentes (con nombre asignado) en una lista de partidos."""
    s = set()
    for p in partidos:
        for t in (p.get("local"), p.get("visitante")):
            if t:
                s.add(t)
    return sorted(s)


def _jugado(p):
    return p.get("jugado") and p.get("golesLocal") is not None and p.get("golesVisitante") is not None


def _marcador(p):
    """Partido real -> {local, visitante, pred:{sign,home,away}} (None si no jugado)."""
    if not _jugado(p):
        return None
    gl, gv = p["golesLocal"], p["golesVisitante"]
    return {"local": p.get("local"), "visitante": p.get("visitante"),
            "pred": {"sign": _signo(gl, gv), "home": gl, "away": gv}}


def _ganador_equipo(p):
    """Equipo ganador (campo 'ganador' = side, resuelto incl. penaltis)."""
    g = p.get("ganador")
    return p.get("local") if g == "local" else (p.get("visitante") if g == "visitante" else None)


def _grupos_completos(partidos):
    """Conjunto de grupos con sus 6 partidos finalizados."""
    cnt = {}
    for p in partidos:
        if p.get("fase") == "Grupos" and _jugado(p) and p.get("grupo"):
            cnt[p["grupo"]] = cnt.get(p["grupo"], 0) + 1
    return {g for g, n in cnt.items() if n >= 6}


def build_ko(partidos, tablas_grupos, posiciones=None):
    """Construye los campos de eliminatorias del esquema de resultados.

    partidos      : lista de build_web_data (fase, local, visitante, golesLocal,
                    golesVisitante, jugado, ganador...).
    tablas_grupos : dict {grupo: [filas ordenadas]} (fallback para posiciones).
    posiciones    : lista [{"pos":"1º GRUPO A","team":...}] OFICIAL (de /standings)
                    para grupos completos; si None, se derivan de tablas_grupos.
    Devuelve dict con posiciones_grupos, clasif_*, cruces_* (listas de partidos
    reales de cada ronda), finalistas, clasif_34, partido_34, partido_final,
    campeon, subcampeon, tercero.
    """
    fases = {"Dieciseisavos": [], "Octavos": [], "Cuartos": [], "Semifinales": [], "3er puesto": [], "Final": []}
    for p in partidos:
        if p.get("fase") in fases:
            fases[p["fase"]].append(p)

    res = {
        "posiciones_grupos": [], "clasif_dieciseisavos": [], "cruces_dieciseisavos": [],
        "clasif_octavos": [], "cruces_octavos": [], "clasif_cuartos": [], "cruces_cuartos": [],
        "clasif_semis": [], "cruces_semis": [], "clasif_34": [], "finalistas": [],
        "partido_34": {"match": None, "pred": None}, "partido_final": {"match": None, "pred": None},
        "campeon": None, "subcampeon": None, "tercero": None,
    }

    # 1) Posiciones de grupo (oficiales si se pasan; si no, de tablas, solo grupos completos)
    if posiciones is not None:
        res["posiciones_grupos"] = list(posiciones)
    else:
        for g in sorted(tablas_grupos or {}):
            if g not in _grupos_completos(partidos):
                continue
            for fila in tablas_grupos[g]:
                res["posiciones_grupos"].append({"pos": f"{fila['pos']}º GRUPO {g}", "team": fila["team"]})

    # 2) Clasificados por ronda (equipos presentes) + finalistas / 3º-4º
    res["clasif_dieciseisavos"] = _equipos_en(fases["Dieciseisavos"])
    res["clasif_octavos"] = _equipos_en(fases["Octavos"])
    res["clasif_cuartos"] = _equipos_en(fases["Cuartos"])
    res["clasif_semis"] = _equipos_en(fases["Semifinales"])
    res["finalistas"] = _equipos_en(fases["Final"])
    res["clasif_34"] = _equipos_en(fases["3er puesto"])

    # 3) Marcadores de cruces: lista de partidos reales jugados de cada ronda
    #    (el motor los casa por equipos; aquí no importa el orden de la lista)
    res["cruces_dieciseisavos"] = [m for p in fases["Dieciseisavos"] if (m := _marcador(p))]
    res["cruces_octavos"] = [m for p in fases["Octavos"] if (m := _marcador(p))]
    res["cruces_cuartos"] = [m for p in fases["Cuartos"] if (m := _marcador(p))]
    res["cruces_semis"] = [m for p in fases["Semifinales"] if (m := _marcador(p))]

    # 4) Partido 3º-4º y Final (marcador) + cuadro de honor
    def marcador_pf(p):
        m = _marcador(p)
        return {"match": f"{p['local']}-{p['visitante']}", "pred": m["pred"]} if m else {"match": None, "pred": None}

    fin = fases["Final"][0] if fases["Final"] else None
    t34 = fases["3er puesto"][0] if fases["3er puesto"] else None
    if fin:
        res["partido_final"] = marcador_pf(fin)
        camp = _ganador_equipo(fin)
        if camp:
            res["campeon"] = camp
            res["subcampeon"] = fin["visitante"] if _norm(camp) == _norm(fin.get("local")) else fin["local"]
    if t34:
        res["partido_34"] = marcador_pf(t34)
        ter = _ganador_equipo(t34)
        if ter:
            res["tercero"] = ter
    return res
