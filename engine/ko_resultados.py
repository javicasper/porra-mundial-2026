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
import json
import unicodedata
from pathlib import Path

# Tabla oficial FIFA de reparto de los 8 mejores terceros (extraída del Excel):
# combinación (8 letras de grupo cuyos terceros clasifican) -> {casilla: grupo del tercero}.
# La "casilla" es el grupo del 1.º que juega ese cruce (A,B,D,E,G,I,K,L).
_TERCEROS = json.loads((Path(__file__).resolve().parent.parent / "data" / "terceros_combinaciones.json").read_text(encoding="utf-8"))

# Dieciseisavos: winLabel -> (feeder1, feeder2, utc). Feeders: "1X"/"2X" (posición de
# grupo) o "3XXXXX" (mejor tercero entre esos grupos). utc = el del calendario real.
_R32 = {
    "W73": ("2A", "2B", "2026-06-28T19:00:00Z"), "W74": ("1F", "2C", "2026-06-29T20:30:00Z"),
    "W75": ("1C", "2F", "2026-06-30T01:00:00Z"), "W76": ("1E", "3ABCDF", "2026-06-29T17:00:00Z"),
    "W77": ("2E", "2I", "2026-06-30T21:00:00Z"), "W78": ("1I", "3CDFGH", "2026-06-30T17:00:00Z"),
    "W79": ("1A", "3CEFHI", "2026-07-01T01:00:00Z"), "W80": ("1L", "3EHIJK", "2026-07-01T16:00:00Z"),
    "W81": ("1G", "3AEHIJ", "2026-07-02T00:00:00Z"), "W82": ("1D", "3BEFIJ", "2026-07-01T20:00:00Z"),
    "W83": ("1H", "2J", "2026-07-02T23:00:00Z"), "W84": ("2K", "2L", "2026-07-02T19:00:00Z"),
    "W85": ("1B", "3EFGIJ", "2026-07-03T03:00:00Z"), "W86": ("1K", "3DEIJL", "2026-07-03T22:00:00Z"),
    "W87": ("2D", "2G", "2026-07-04T01:30:00Z"), "W88": ("1J", "2H", "2026-07-03T18:00:00Z"),
}


def _pos_grupo(tablas, pos, g):
    for f in (tablas.get(g) or []):
        if f.get("pos") == pos:
            return f.get("team")
    return None


def proyeccion_cuadro(tablas_grupos):
    """Proyección PROVISIONAL de los dieciseisavos según la clasificación actual:
    1.º/2.º de cada grupo en su casilla fija + los 8 mejores terceros repartidos por
    la tabla oficial FIFA. Devuelve {utc: {"local","visitante"}} (hasta 16 partidos),
    o {} si aún no hay datos suficientes (faltan grupos)."""
    tablas_grupos = tablas_grupos or {}
    thirds = [(g, next((f for f in filas if f.get("pos") == 3), None)) for g, filas in tablas_grupos.items()]
    thirds = [(g, f) for g, f in thirds if f]
    if len(thirds) < 12:
        return {}
    thirds.sort(key=lambda gf: (-gf[1].get("pts", 0), -gf[1].get("dg", 0), -gf[1].get("gf", 0), gf[1].get("team", "")))
    alloc = _TERCEROS.get("".join(sorted(g for g, _ in thirds[:8])))
    if not alloc:
        return {}

    def equipo(f, otro):
        if f[0] in "12":
            return _pos_grupo(tablas_grupos, int(f[0]), f[1])
        return _pos_grupo(tablas_grupos, 3, alloc.get(otro[1]))   # tercero asignado a la casilla del 1.º

    # ¿está ya FIJO ese lado? 1.º/2.º: si su grupo terminó. Tercero: solo cuando han
    # acabado TODOS los grupos (hasta entonces el ranking de terceros puede cambiar).
    def _gcompleto(g):
        rows = tablas_grupos.get(g) or []
        return len(rows) >= 4 and all((r.get("pj") or 0) >= 3 for r in rows)
    todos = sum(1 for g in tablas_grupos if _gcompleto(g)) >= 12

    def fijo(f):
        return _gcompleto(f[1]) if f[0] in "12" else todos

    out = {}
    for f1, f2, utc in _R32.values():
        local, visit = equipo(f1, f2), equipo(f2, f1)
        if local and visit:
            out[utc] = {"local": local, "visitante": visit,
                        "localFijo": fijo(f1), "visitanteFijo": fijo(f2)}
    return out


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

    # Estado de cada ronda: una ronda "alimenta" a la siguiente solo cuando ha
    # terminado del todo. Hasta entonces no se suman ni posiciones ni clasificados
    # (si no, la API los va asignando a trozos y los puntos bailarían).
    def _fin(lst):
        return sum(1 for p in lst if _jugado(p))
    grupos_ok = sum(1 for p in partidos if p.get("fase") == "Grupos" and _jugado(p)) >= 72
    r32_ok = _fin(fases["Dieciseisavos"]) >= 16
    r16_ok = _fin(fases["Octavos"]) >= 8
    qf_ok = _fin(fases["Cuartos"]) >= 4
    sf_ok = _fin(fases["Semifinales"]) >= 2

    # 1) Posiciones de grupo: solo cuando TODA la fase de grupos ha terminado.
    if grupos_ok:
        if posiciones is not None:
            res["posiciones_grupos"] = list(posiciones)
        else:
            for g in sorted(tablas_grupos or {}):
                if g not in _grupos_completos(partidos):
                    continue
                for fila in tablas_grupos[g]:
                    res["posiciones_grupos"].append({"pos": f"{fila['pos']}º GRUPO {g}", "team": fila["team"]})

    # 2) Clasificados por ronda (gateados por la ronda previa completa).
    res["clasif_dieciseisavos"] = _equipos_en(fases["Dieciseisavos"]) if grupos_ok else []
    res["clasif_octavos"] = _equipos_en(fases["Octavos"]) if r32_ok else []
    res["clasif_cuartos"] = _equipos_en(fases["Cuartos"]) if r16_ok else []
    res["clasif_semis"] = _equipos_en(fases["Semifinales"]) if qf_ok else []
    res["finalistas"] = _equipos_en(fases["Final"]) if sf_ok else []
    res["clasif_34"] = _equipos_en(fases["3er puesto"]) if sf_ok else []

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
