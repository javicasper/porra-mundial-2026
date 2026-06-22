"""Construye la parte de ELIMINATORIAS del esquema de resultados de la porra,
a partir de los partidos reales (formato de build_web_data) y la clasificación
de grupos, para alimentar el motor de puntuación (engine/scoring.py).

Idea clave (validada contra los datos): las 13 quinielas siguen el MISMO cuadro
oficial. La topología (qué slot alimenta a cuál y qué lado es local) es idéntica
en los 13 participantes, así que se DERIVA de las predicciones en tiempo de
ejecución con `canonical_bracket()`. Con esa topología:

  - Dieciseisavos: cada slot se identifica por su feeder LOCAL fijo (p.ej. "2º
    GRUPO A"), cuyo equipo sale de la clasificación final del grupo.
  - Octavos/Cuartos/Semis: cada slot lo alimentan los GANADORES de dos slots de
    la ronda previa; se propaga hacia arriba y se casa con el partido real que
    contiene a esos dos equipos.

La puntuación de marcadores es POR SLOT (regla de la porra): res["cruces_*"] se
devuelve en el MISMO orden de slot que las predicciones, y el motor compara
slot i contra slot i. Todo degrada con elegancia: lo que aún no se conoce queda
a None/[], y el motor simplemente no lo puntúa.
"""
from __future__ import annotations
import unicodedata
from collections import Counter


def _norm(s):
    if s is None:
        return None
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().strip().lower()


def _split(m):
    if not m:
        return [None, None]
    parts = [t.strip() for t in m.split("-", 1)]
    return parts if len(parts) == 2 else [None, None]


def _signo(h, a):
    return "1" if h > a else ("2" if a > h else "X")


# Orden de avance y nombres de fase (como los pone build_web_data en partido["fase"]).
_ORDER = ["dieciseisavos", "octavos", "cuartos", "semis"]
_FASE = {"dieciseisavos": "Dieciseisavos", "octavos": "Octavos",
         "cuartos": "Cuartos", "semis": "Semifinales"}
_N = {"dieciseisavos": 16, "octavos": 8, "cuartos": 4, "semis": 2}
# claves de la lista de "clasificados a la SIGUIENTE ronda" en las predicciones
_CLASIF_SIG = {"dieciseisavos": "clasif_octavos", "octavos": "clasif_cuartos",
               "cuartos": "clasif_semis", "semis": "finalistas"}


def canonical_bracket(PRED):
    """Deriva el cuadro canónico desde las predicciones (consenso de los 13).

    Devuelve dict con:
      r32_home[i]      -> etiqueta de posición de grupo del LOCAL del slot i de dieciseisavos
      topo[ronda][s]   -> (a, b) índices de slot de la ronda previa que alimentan el slot s
      orient[ronda][s] -> "low"/"high": si el LOCAL es el ganador del feeder de índice menor/mayor
      warnings         -> lista de avisos si algún slot no tuvo consenso unánime
    """
    parts = sorted(PRED)
    warnings = []

    def posmap(p):
        return {_norm(e["team"]): e["pos"] for e in p.get("posiciones_grupos", []) if e.get("team")}

    def winner_of(p, ronda):
        """Para cada slot de `ronda`, el equipo que avanza (según clasif a la siguiente)."""
        cru = f"cruces_{ronda}"
        adv = {_norm(x) for x in p.get(_CLASIF_SIG[ronda], [])}
        out = {}
        for j, tie in enumerate(p.get(cru, [])):
            h, a = _split(tie.get("match"))
            cand = [t for t in (h, a) if t and _norm(t) in adv]
            if len(cand) == 1:
                out[_norm(cand[0])] = j
        return out

    # Dieciseisavos: feeder local por slot
    r32_home = []
    for i in range(16):
        c = Counter()
        for k in parts:
            h, _ = _split(PRED[k]["cruces_dieciseisavos"][i].get("match"))
            c[posmap(PRED[k]).get(_norm(h), "?")] += 1
        lbl, n = c.most_common(1)[0]
        if n < len(parts):
            warnings.append(f"dieciseisavos slot {i}: feeder local sin consenso ({n}/{len(parts)})")
        r32_home.append(lbl)

    # Rondas profundas: topología + orientación
    topo, orient = {}, {}
    for r in ["octavos", "cuartos", "semis"]:
        prev = _ORDER[_ORDER.index(r) - 1]
        feeders = [Counter() for _ in range(_N[r])]
        side = [Counter() for _ in range(_N[r])]
        for k in parts:
            p = PRED[k]
            win = winner_of(p, prev)  # norm(team) -> slot previo
            for s in range(_N[r]):
                h, a = _split(p[f"cruces_{r}"][s].get("match"))
                fh, fa = win.get(_norm(h)), win.get(_norm(a))
                if fh is not None and fa is not None:
                    feeders[s][tuple(sorted((fh, fa)))] += 1
                    side[s]["low" if fh < fa else "high"] += 1
        topo[r], orient[r] = [], []
        for s in range(_N[r]):
            if not feeders[s]:
                topo[r].append(None); orient[r].append(None)
                warnings.append(f"{r} slot {s}: sin topología derivable")
                continue
            pair, np_ = feeders[s].most_common(1)[0]
            sd, ns = side[s].most_common(1)[0]
            if np_ < len(parts) or ns < len(parts):
                warnings.append(f"{r} slot {s}: topología sin consenso ({np_}/{len(parts)}, orient {ns}/{len(parts)})")
            topo[r].append(list(pair)); orient[r].append(sd)
    return {"r32_home": r32_home, "topo": topo, "orient": orient, "warnings": warnings}


# ---------- helpers sobre los partidos reales ----------
def _ganador_equipo(p):
    """Equipo ganador del partido (usa el campo 'ganador' = side, resuelto incl. penaltis)."""
    g = p.get("ganador")
    if g == "local":
        return p.get("local")
    if g == "visitante":
        return p.get("visitante")
    return None


def _orientar(p, equipo_local_canonico):
    """Devuelve (home, away, gh, ga) con el LADO LOCAL = equipo_local_canonico."""
    el, ev = p.get("local"), p.get("visitante")
    gl, gv = p.get("golesLocal"), p.get("golesVisitante")
    if _norm(el) == _norm(equipo_local_canonico):
        return el, ev, gl, gv
    return ev, el, gv, gl


def _buscar_por_equipo(partidos, equipo):
    eq = _norm(equipo)
    for p in partidos:
        if eq in (_norm(p.get("local")), _norm(p.get("visitante"))):
            return p
    return None


def _buscar_por_par(partidos, t1, t2):
    par = {_norm(t1), _norm(t2)}
    for p in partidos:
        if {_norm(p.get("local")), _norm(p.get("visitante"))} == par:
            return p
    return None


def _equipos_en(partidos):
    s = set()
    for p in partidos:
        for t in (p.get("local"), p.get("visitante")):
            if t:
                s.add(t)
    return sorted(s)


def _grupos_completos(partidos):
    """{grupo: True} para grupos con sus 6 partidos FINALIZADOS."""
    cnt = Counter()
    for p in partidos:
        if p.get("fase") == "Grupos" and p.get("jugado") and p.get("golesLocal") is not None:
            if p.get("grupo"):
                cnt[p["grupo"]] += 1
    return {g for g, n in cnt.items() if n >= 6}


def build_ko(partidos, tablas_grupos, PRED, bracket=None, posiciones=None):
    """Construye los campos de eliminatorias del esquema de resultados.

    partidos       : lista de build_web_data (fase, grupo, local, visitante,
                     golesLocal, golesVisitante, jugado, ganador...).
    tablas_grupos  : dict {grupo: [filas ordenadas]} de build_tablas_grupos.
    posiciones     : lista [{"pos": "1º GRUPO A", "team": ...}] OFICIAL (de
                     /standings) para grupos completos. Si None, se derivan de
                     tablas_grupos (desempate simplificado, fallback).
    Devuelve dict con: posiciones_grupos, clasif_*, cruces_*, finalistas,
    clasif_34, partido_34, partido_final, campeon, subcampeon, tercero, _warnings.
    """
    B = bracket or canonical_bracket(PRED)
    fases = {"Dieciseisavos": [], "Octavos": [], "Cuartos": [], "Semifinales": [], "3er puesto": [], "Final": []}
    for p in partidos:
        if p.get("fase") in fases:
            fases[p["fase"]].append(p)

    res = {
        "posiciones_grupos": [], "clasif_dieciseisavos": [], "cruces_dieciseisavos": [],
        "clasif_octavos": [], "cruces_octavos": [], "clasif_cuartos": [], "cruces_cuartos": [],
        "clasif_semis": [], "cruces_semis": [], "clasif_34": [], "finalistas": [],
        "partido_34": {"match": None, "pred": None}, "partido_final": {"match": None, "pred": None},
        "campeon": None, "subcampeon": None, "tercero": None, "_warnings": list(B.get("warnings", [])),
    }

    # 1) Posiciones de grupo + realPos para identificar los slots de dieciseisavos.
    #    Preferimos las posiciones OFICIALES (/standings); si no, las derivadas
    #    de tablas_grupos (solo grupos completos).
    realPos = {}
    if posiciones is not None:
        res["posiciones_grupos"] = list(posiciones)
        realPos = {e["pos"]: e["team"] for e in posiciones if e.get("team")}
    else:
        completos = _grupos_completos(partidos)
        for g in sorted(tablas_grupos):
            if g not in completos:
                continue
            for fila in tablas_grupos[g]:
                label = f"{fila['pos']}º GRUPO {g}"
                res["posiciones_grupos"].append({"pos": label, "team": fila["team"]})
                realPos[label] = fila["team"]

    # 2) Clasificados por ronda (equipos presentes en cada fase) + finalistas / 3º-4º
    res["clasif_dieciseisavos"] = _equipos_en(fases["Dieciseisavos"])
    res["clasif_octavos"] = _equipos_en(fases["Octavos"])
    res["clasif_cuartos"] = _equipos_en(fases["Cuartos"])
    res["clasif_semis"] = _equipos_en(fases["Semifinales"])
    res["finalistas"] = _equipos_en(fases["Final"])
    res["clasif_34"] = _equipos_en(fases["3er puesto"])

    # 3) Marcadores de cruces por slot, propagando ganadores por el cuadro
    slot_teams = {r: {} for r in _ORDER}   # ronda -> {slot: (home, away)}
    slot_winner = {r: {} for r in _ORDER}  # ronda -> {slot: equipo}

    def registrar(r, s, partido, home_team, away_team):
        if partido.get("jugado") and partido.get("golesLocal") is not None:
            home, away, gh, ga = _orientar(partido, home_team)
            res[f"cruces_{r}"][s] = {"match": f"{home}-{away}",
                                     "pred": {"sign": _signo(gh, ga), "home": gh, "away": ga}}
        else:
            res[f"cruces_{r}"][s] = {"match": f"{home_team}-{away_team}", "pred": None}
        slot_teams[r][s] = (home_team, away_team)
        w = _ganador_equipo(partido)
        if w:
            slot_winner[r][s] = w

    for r in _ORDER:
        res[f"cruces_{r}"] = [{"match": None, "pred": None} for _ in range(_N[r])]

    # Dieciseisavos: localizar slot por el feeder local fijo
    for i in range(16):
        home_team = realPos.get(B["r32_home"][i])
        if not home_team:
            continue
        m = _buscar_por_equipo(fases["Dieciseisavos"], home_team)
        if not m:
            continue
        home, away, _, _ = _orientar(m, home_team)
        registrar("dieciseisavos", i, m, home, away)

    # Octavos -> Cuartos -> Semis: por ganadores de los slots feeder
    for r in ["octavos", "cuartos", "semis"]:
        prev = _ORDER[_ORDER.index(r) - 1]
        for s in range(_N[r]):
            topo_s = B["topo"][r][s]
            if not topo_s:
                continue
            a, b = topo_s
            home_feeder = a if B["orient"][r][s] == "low" else b
            away_feeder = b if B["orient"][r][s] == "low" else a
            ht = slot_winner[prev].get(home_feeder)
            at = slot_winner[prev].get(away_feeder)
            if not ht or not at:
                continue
            m = _buscar_por_par(fases[_FASE[r]], ht, at)
            if not m:
                continue
            registrar(r, s, m, ht, at)

    # 4) Partido 3º-4º y Final (marcadores) + cuadro de honor
    def marcador(p):
        if p and p.get("jugado") and p.get("golesLocal") is not None:
            gl, gv = p["golesLocal"], p["golesVisitante"]
            return {"match": f"{p['local']}-{p['visitante']}", "pred": {"sign": _signo(gl, gv), "home": gl, "away": gv}}
        return {"match": None, "pred": None}

    fin = fases["Final"][0] if fases["Final"] else None
    t34 = fases["3er puesto"][0] if fases["3er puesto"] else None
    if fin:
        res["partido_final"] = marcador(fin)
        camp = _ganador_equipo(fin)
        if camp:
            res["campeon"] = camp
            res["subcampeon"] = fin["visitante"] if _norm(camp) == _norm(fin.get("local")) else fin["local"]
    if t34:
        res["partido_34"] = marcador(t34)
        ter = _ganador_equipo(t34)
        if ter:
            res["tercero"] = ter
    return res
