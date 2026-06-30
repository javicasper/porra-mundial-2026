"""Genera web/data.json para el frontend de la porra (en vivo).

Pipeline:
  API football-data.org  ->  resultados (esquema porra)  ->  motor de scoring
                         ->  data.json  (ranking + calendario + detalle/participante)

Uso:
    FOOTBALLDATA_API_KEY=xxx python web/build_web_data.py
    python web/build_web_data.py --cache /tmp/wcm.json     # sin red
"""
from __future__ import annotations
import argparse, json, os, sys, urllib.request, unicodedata
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT / "engine"))
from scoring import puntuar, puntos_partido, buscar_cruce, REGLAS  # noqa: E402
from ko_resultados import build_ko, proyeccion_cuadro  # noqa: E402

MAP = {k: v for k, v in json.loads((DATA / "equipos_map.json").read_text(encoding="utf-8")).items()
       if not k.startswith("_")}
# Predicciones reales si existen; si no, el ejemplo anonimizado incluido en el repo.
_PRED_FILE = DATA / "predicciones.json"
if not _PRED_FILE.exists():
    _PRED_FILE = DATA / "predicciones.sample.json"
PRED = json.loads(_PRED_FILE.read_text(encoding="utf-8"))
# Participante de referencia para el orden estable del fixture (72 partidos).
FIXTURE_REF = sorted(PRED)[0]


def display_name(pid):
    """Nombre a mostrar a partir del id (sin nombres hardcodeados)."""
    return str(pid).replace("_", " ")


STAGE_ES = {"GROUP_STAGE": "Grupos", "LAST_32": "Dieciseisavos", "LAST_16": "Octavos",
            "QUARTER_FINALS": "Cuartos", "SEMI_FINALS": "Semifinales",
            "THIRD_PLACE": "3er puesto", "FINAL": "Final"}


def norm(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().strip().lower()


def es(name):
    return MAP.get(name, name)


def signo(h, a):
    return "1" if h > a else ("2" if a > h else "X")


def fetch_api():
    key = os.environ.get("FOOTBALLDATA_API_KEY")
    if not key:
        sys.exit("ERROR: falta FOOTBALLDATA_API_KEY (o usa --cache).")
    req = urllib.request.Request(
        "https://api.football-data.org/v4/competitions/WC/matches",
        headers={"X-Auth-Token": key})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def build_partidos(matches):
    out = []
    for m in matches:
        sc = m.get("score") or {}
        ft = sc.get("fullTime") or {}
        # Para la PORRA cuenta el marcador de los 90' (reglamentario): si hubo prórroga o
        # penaltis, football-data lo da en 'regularTime'; si no, 'fullTime' ya son los 90'.
        reg = sc.get("regularTime")
        m90 = reg if reg else ft
        pens = sc.get("penalties") or {}
        dur = sc.get("duration")
        fin = m["status"] == "FINISHED"
        live = m["status"] in ("IN_PLAY", "PAUSED")
        show = fin or live
        win = {"HOME_TEAM": "local", "AWAY_TEAM": "visitante"}.get((m.get("score") or {}).get("winner"))
        out.append({
            "fase": STAGE_ES.get(m["stage"], m["stage"]),
            "grupo": (m.get("group") or "").replace("GROUP_", ""),
            "jornada": m.get("matchday") if m["stage"] == "GROUP_STAGE" else None,
            "utc": m.get("utcDate"),
            "local": es(m["homeTeam"]["name"]) if m["homeTeam"].get("name") else None,
            "visitante": es(m["awayTeam"]["name"]) if m["awayTeam"].get("name") else None,
            "tlaLocal": m["homeTeam"].get("tla"),       # código FIFA (ESP, BRA...) para casar el directo
            "tlaVisitante": m["awayTeam"].get("tla"),
            "golesLocal": m90.get("home") if show else None,        # 90' (lo que cuenta para la porra)
            "golesVisitante": m90.get("away") if show else None,
            # Final con prórroga/penaltis (solo si difiere de los 90', para mostrarlo aparte):
            "golesLocalFull": ft.get("home") if (show and reg) else None,
            "golesVisitanteFull": ft.get("away") if (show and reg) else None,
            "penaltisLocal": pens.get("home") if (fin and dur == "PENALTY_SHOOTOUT") else None,
            "penaltisVisitante": pens.get("away") if (fin and dur == "PENALTY_SHOOTOUT") else None,
            "decidido": dur if fin else None,   # REGULAR / EXTRA_TIME / PENALTY_SHOOTOUT
            "status": m["status"],
            "jugado": fin,
            "envivo": live,
            "ganador": win if fin else None,   # 'local'/'visitante' (resuelto incl. penaltis)
            "minuto": None,
            "eventos": None,
            "stats": None,
            "colores": None,
        })
    out.sort(key=lambda x: (x["utc"] or "9999"))
    return out


def fetch_espn():
    """Marcador y MINUTO en vivo desde la API abierta de ESPN (sin clave).
    Más fresca que football-data free para partidos en juego. Best-effort."""
    try:
        with urllib.request.urlopen(
                "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard",
                timeout=15) as r:
            d = json.loads(r.read().decode())
    except Exception:
        return []
    out = []
    for e in d.get("events", []):
        try:
            comp = e["competitions"][0]
            cs = comp["competitors"]
            h = next(x for x in cs if x["homeAway"] == "home")
            a = next(x for x in cs if x["homeAway"] == "away")
            hid = (h.get("team") or {}).get("id")
            sc = lambda x: int(x["score"]) if str(x.get("score", "")).strip() != "" else None
            eventos = []
            for x in comp.get("details", []):
                t = (x.get("type") or {}).get("text", "")
                quien = [z.get("displayName") for z in (x.get("athletesInvolved") or []) if z.get("displayName")]
                if x.get("scoringPlay") or "Goal" in t:
                    kind = "og" if x.get("ownGoal") else ("pen" if x.get("penaltyKick") else "goal")
                elif x.get("redCard") or "Red" in t:
                    kind = "red"
                elif x.get("yellowCard") or "Yellow" in t:
                    kind = "yellow"
                else:
                    continue
                eventos.append({"kind": kind, "clock": (x.get("clock") or {}).get("displayValue", ""),
                                "side": "h" if (x.get("team") or {}).get("id") == hid else "a",
                                "who": quien[0] if quien else ""})

            def st(team, name):
                for s in team.get("statistics", []):
                    if s.get("name") == name:
                        v = s.get("displayValue")
                        try:
                            return round(float(v))
                        except (TypeError, ValueError):
                            return v
                return None
            STATS = [("posesion", "possessionPct"), ("tiros", "totalShots"),
                     ("aPuerta", "shotsOnTarget"), ("corners", "wonCorners"), ("faltas", "foulsCommitted")]
            stats = {k: [st(h, n), st(a, n)] for k, n in STATS}
            if all(v is None for pair in stats.values() for v in pair):
                stats = None

            def color(team):
                t = team.get("team") or {}
                c, alt = t.get("color") or "", t.get("alternateColor") or ""
                def claro(x):
                    try:
                        r, g, b = int(x[0:2], 16), int(x[2:4], 16), int(x[4:6], 16)
                        return 0.2126 * r + 0.7152 * g + 0.0722 * b > 200
                    except (ValueError, IndexError):
                        return True
                pick = c if (c and not claro(c)) else (alt if (alt and not claro(alt)) else (c or alt))
                return "#" + pick if pick else None
            colores = [color(h), color(a)]

            ty = e["status"]["type"]
            clock = e["status"].get("displayClock")
            if ty.get("name") == "STATUS_HALFTIME" or ty.get("shortDetail") == "HT":
                clock = "Descanso"

            # clave = hora + código FIFA del local: desambigua partidos simultáneos
            habbr = (h.get("team") or {}).get("abbreviation") or ""
            out.append({"key": (e.get("date") or "")[:16] + "|" + habbr,
                        "state": ty["state"],          # pre | in | post
                        "clock": clock,
                        "home": sc(h), "away": sc(a), "eventos": eventos, "stats": stats, "colores": colores})
        except Exception:
            continue
    return out


def overlay_espn(partidos, espn):
    """Superpone ESPN (más fresca que football-data free): marcador y minuto en
    vivo, y también marca FINALIZADO en cuanto ESPN lo da por terminado."""
    by_key = {e["key"]: e for e in espn if e.get("key")}
    for p in partidos:
        e = by_key.get((p.get("utc") or "")[:16] + "|" + (p.get("tlaLocal") or ""))
        if not e:
            continue
        if e["state"] == "in":
            p["envivo"], p["jugado"], p["status"] = True, False, "IN_PLAY"
            if e["home"] is not None: p["golesLocal"] = e["home"]
            if e["away"] is not None: p["golesVisitante"] = e["away"]
            p["minuto"] = e["clock"]
            p["eventos"] = e.get("eventos") or None
            p["stats"] = e.get("stats")
            p["colores"] = e.get("colores")
        elif e["state"] == "post":
            fd_fin = p.get("status") == "FINISHED"  # football-data ya lo cerró (trae el 90' correcto)
            p["envivo"], p["jugado"], p["status"], p["minuto"] = False, True, "FINISHED", None
            # Solo cogemos el marcador de ESPN si football-data aún no lo tenía cerrado, para no
            # pisar el resultado de los 90' (ESPN daría el agregado con penaltis).
            if not fd_fin:
                if e["home"] is not None: p["golesLocal"] = e["home"]
                if e["away"] is not None: p["golesVisitante"] = e["away"]
            p["eventos"] = e.get("eventos") or None
            p["stats"] = e.get("stats")
            p["colores"] = e.get("colores")
    return partidos


def build_resultados(partidos):
    """Resultados de grupos para el motor, desde los partidos ya fusionados (ESPN incl.)."""
    por_par = {}
    for p in partidos:
        if not p.get("grupo") or not p.get("jugado"):
            continue
        if p.get("golesLocal") is None or p.get("golesVisitante") is None:
            continue
        por_par[frozenset((norm(p["local"]), norm(p["visitante"])))] = (
            norm(p["local"]), p["golesLocal"], p["golesVisitante"])
    grupos, jug = [], 0
    for fx in PRED[FIXTURE_REF]["grupos"]:
        local, visit = [t.strip() for t in fx["match"].split("-", 1)]
        entry = {"code": fx["code"], "match": fx["match"], "pred": None}
        key = frozenset((norm(local), norm(visit)))
        if key in por_par:
            hn, gh, ga = por_par[key]
            h, v = (gh, ga) if hn == norm(local) else (ga, gh)
            entry["pred"] = {"sign": signo(h, v), "home": h, "away": v}
            jug += 1
        grupos.append(entry)
    res = {"grupos": grupos, "posiciones_grupos": [], "clasif_dieciseisavos": [],
           "cruces_dieciseisavos": [], "clasif_octavos": [], "cruces_octavos": [],
           "clasif_cuartos": [], "cruces_cuartos": [], "clasif_semis": [], "cruces_semis": [],
           "clasif_34": [], "finalistas": [], "partido_34": {"match": None, "pred": None},
           "partido_final": {"match": None, "pred": None}, "campeon": None, "subcampeon": None,
           "tercero": None, "bota_oro": None, "bota_plata": None, "bota_bronce": None,
           "balon_oro": None, "balon_plata": None, "balon_bronce": None}
    return res, jug


def build_ranking(res):
    filas = []
    for k, pred in PRED.items():
        r = puntuar(pred, res)
        g = r["detalle"]["grupos_partidos"]["info"]
        filas.append({"id": k, "nombre": display_name(k), "puntos": r["total"],
                      "clavados": g.get("exacto", 0), "diferencias": g.get("diferencia", 0),
                      "signos": g.get("signo", 0), "campeon": pred.get("campeon"),
                      "bota_oro": pred.get("bota_oro"), "balon_oro": pred.get("balon_oro")})
    filas.sort(key=lambda x: (-x["puntos"], -x["clavados"], x["nombre"]))
    pos, prev = 0, None
    for i, f in enumerate(filas):
        clave = (f["puntos"], f["clavados"])
        if clave != prev:
            pos, prev = i + 1, clave
        f["pos"] = pos
    return filas


def build_tla_map(matches):
    """tla (ARG, ESP...) -> nombre porra (ES)."""
    m = {}
    for mt in matches:
        for side in ("homeTeam", "awayTeam"):
            t = mt[side]
            if t.get("tla") and t.get("name"):
                m[t["tla"]] = es(t["name"])
    return m


def fetch_standings():
    """Clasificación OFICIAL de grupos (con desempates correctos). Best-effort: [] si falla."""
    key = os.environ.get("FOOTBALLDATA_API_KEY")
    if not key:
        return []
    try:
        req = urllib.request.Request(
            "https://api.football-data.org/v4/competitions/WC/standings",
            headers={"X-Auth-Token": key})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode()).get("standings", [])
    except Exception:
        return []


def build_posiciones_oficiales(standings, partidos):
    """Posiciones de grupo OFICIALES (de /standings) solo para grupos COMPLETOS
    (6 partidos finalizados). Devuelve [{"pos": "1º GRUPO A", "team": <ES>}]."""
    completos = set()
    cnt = {}
    for p in partidos:
        if p.get("fase") == "Grupos" and p.get("jugado") and p.get("golesLocal") is not None and p.get("grupo"):
            cnt[p["grupo"]] = cnt.get(p["grupo"], 0) + 1
    completos = {g for g, n in cnt.items() if n >= 6}
    out = []
    for bloque in standings:
        if bloque.get("type") != "TOTAL":
            continue
        g = (bloque.get("group") or "").replace("Group ", "").strip()
        if not g or g not in completos:
            continue
        for fila in bloque.get("table", []):
            name = (fila.get("team") or {}).get("name")
            if name and fila.get("position"):
                out.append({"pos": f"{fila['position']}º GRUPO {g}", "team": es(name)})
    return out


def clasificados_dieciseisavos(standings, partidos):
    """Los 32 equipos que pasan a dieciseisavos, calculados de la clasificación OFICIAL
    (1.º y 2.º de cada grupo + los 8 mejores terceros), sin depender de que la API
    rellene el cuadro (la free tier va lentísima con eso). [] si no han acabado los
    72 partidos de grupos."""
    jug = sum(1 for p in partidos if p.get("fase") == "Grupos" and p.get("jugado") and p.get("golesLocal") is not None)
    if jug < 72:
        return []
    primeros, segundos, terceros = [], [], []
    for b in standings:
        if b.get("type") != "TOTAL":
            continue
        for r in b.get("table", []):
            name = (r.get("team") or {}).get("name")
            pos = r.get("position")
            if not name or not pos:
                continue
            if pos == 1:
                primeros.append(es(name))
            elif pos == 2:
                segundos.append(es(name))
            elif pos == 3:
                terceros.append((es(name), r.get("points", 0), r.get("goalDifference", 0), r.get("goalsFor", 0)))
    if len(primeros) < 12 or len(segundos) < 12 or len(terceros) < 12:
        return []
    terceros.sort(key=lambda t: (-t[1], -t[2], -t[3], t[0]))   # pts, dif, GF (criterio FIFA)
    return primeros + segundos + [t[0] for t in terceros[:8]]


def fetch_scorers():
    """Goleadores (best-effort: [] si no hay clave o falla)."""
    key = os.environ.get("FOOTBALLDATA_API_KEY")
    if not key:
        return []
    try:
        req = urllib.request.Request(
            "https://api.football-data.org/v4/competitions/WC/scorers?limit=30",
            headers={"X-Auth-Token": key})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode()).get("scorers", [])
    except Exception:
        return []


def build_goleadores(scorers, tla2es):
    out = []
    for i, s in enumerate(scorers, 1):
        tla = (s.get("team") or {}).get("tla")
        out.append({
            "pos": i,
            "jugador": (s.get("player") or {}).get("name"),
            "equipo": tla2es.get(tla, tla),
            "goles": s.get("goals") or 0,
            "asistencias": s.get("assists") or 0,
            "penaltis": s.get("penalties") or 0,
            "partidos": s.get("playedMatches") or 0,
        })
    # ranking denso por goles
    pos, prev = 0, None
    for i, g in enumerate(out):
        if g["goles"] != prev:
            pos, prev = i + 1, g["goles"]
        g["pos"] = pos
    return out


def build_tablas_grupos(partidos):
    """Clasificación de cada grupo (A-L) calculada desde los partidos jugados.
    Orden: puntos, diferencia de goles, goles a favor. Tiebreak head-to-head no aplicado."""
    grupos = {}
    gm = sorted([p for p in partidos if p.get("fase") == "Grupos"], key=lambda p: p.get("utc") or "")
    for p in gm:
        g = p.get("grupo")
        if not g:
            continue
        tb = grupos.setdefault(g, {})
        for t in (p.get("local"), p.get("visitante")):
            if t and t not in tb:
                tb[t] = {"team": t, "pj": 0, "g": 0, "e": 0, "p": 0, "gf": 0, "gc": 0, "dg": 0, "pts": 0, "form": []}
        if not p.get("jugado") or p.get("golesLocal") is None:
            continue
        h, a = p["local"], p["visitante"]
        gh, ga = p["golesLocal"], p["golesVisitante"]
        for t, gf, gc in ((h, gh, ga), (a, ga, gh)):
            r = tb[t]
            r["pj"] += 1; r["gf"] += gf; r["gc"] += gc; r["dg"] = r["gf"] - r["gc"]
            if gf > gc: r["g"] += 1; r["pts"] += 3; r["form"].append("G")
            elif gf == gc: r["e"] += 1; r["pts"] += 1; r["form"].append("E")
            else: r["p"] += 1; r["form"].append("P")
    out = {}
    for g in sorted(grupos):
        filas = sorted(grupos[g].values(), key=lambda r: (-r["pts"], -r["dg"], -r["gf"], r["team"]))
        for i, r in enumerate(filas):
            r["pos"] = i + 1
        out[g] = filas
    return out


_KO_FASES = ["Dieciseisavos", "Octavos", "Cuartos", "Semifinales", "3er puesto", "Final"]
_PREV_FASE = {"Dieciseisavos": "Grupos", "Octavos": "Dieciseisavos", "Cuartos": "Octavos",
              "Semifinales": "Cuartos", "3er puesto": "Semifinales", "Final": "Semifinales"}


def _lbl(utc):
    dt = datetime.fromisoformat(utc.replace("Z", "+00:00")) + timedelta(hours=2)
    return f"{dt.day}/{dt.month}"


def build_timeline(partidos, participantes, res_full, tablas_grupos, posic, clasif16=None):
    """Histórico de puntos. Fase de grupos: cada X = un partido jugado (puntos de
    grupos acumulados). Eliminatorias: un hito por partido KO jugado (más uno al
    cerrar los grupos), con el TOTAL COMPLETO a esa fecha — así entran posiciones,
    clasificados, cruces y honor a medida que se resuelven."""
    played = [p for p in partidos if p.get("grupo") and p.get("jugado")
              and p.get("golesLocal") is not None and p.get("utc")]
    played.sort(key=lambda p: p["utc"])
    keyseq, labels = [], ["Inicio"]
    for p in played:
        keyseq.append(frozenset((norm(p["local"]), norm(p["visitante"]))))
        labels.append(_lbl(p["utc"]))
    series = {}
    for pid, P in participantes.items():
        ptsby = {frozenset((norm(g["local"]), norm(g["visitante"]))): g["pts"]
                 for g in P["grupos"] if g.get("real")}
        cum, arr = 0, [0]
        for k in keyseq:
            cum += ptsby.get(k, 0)
            arr.append(cum)
        series[pid] = arr

    # --- eliminatorias ---
    ko_played = sorted([p for p in partidos if p.get("fase") in _KO_FASES and p.get("jugado")
                        and p.get("golesLocal") is not None and p.get("utc")], key=lambda p: p["utc"])
    if not ko_played:
        return {"x": labels, "series": series}

    maxutc = {}
    for p in partidos:
        f = p.get("fase")
        if p.get("utc") and (f == "Grupos" or f in _KO_FASES):
            maxutc[f] = max(maxutc.get(f, ""), p["utc"])
    thr = {f: maxutc.get(_PREV_FASE[f]) for f in _KO_FASES}

    def mask(T):
        """Partidos tal como se conocían en la fecha T: oculta resultados de partidos
        no jugados aún y los equipos de rondas todavía no sorteadas."""
        out = []
        for p in partidos:
            f = p.get("fase")
            if f not in _KO_FASES:
                out.append(p); continue
            q = dict(p)
            drawn = thr[f] is not None and T >= thr[f]
            if not drawn:
                q.update(local=None, visitante=None, jugado=False,
                         golesLocal=None, golesVisitante=None, ganador=None)
            elif not (p["utc"] <= T and p.get("jugado") and p.get("golesLocal") is not None):
                q.update(jugado=False, golesLocal=None, golesVisitante=None, ganador=None)
            out.append(q)
        return out

    def res_at(T):
        ko = build_ko(mask(T), tablas_grupos, posiciones=(posic or None), clasif16=(clasif16 or None))
        return {"grupos": res_full["grupos"], **ko}

    hitos = ([maxutc["Grupos"]] if maxutc.get("Grupos") else []) + [p["utc"] for p in ko_played]
    for T in hitos:
        resT = res_at(T)
        for pid, pred in PRED.items():
            series[pid].append(puntuar(pred, resT)["total"])
        labels.append(_lbl(T))
    return {"x": labels, "series": series}


# (cruces de predicción, tabla del motor, índice de detalle, clave en res)
_CRUCES = [("cruces_dieciseisavos", "r32", "cruces_r32"),
           ("cruces_octavos", "r16", "cruces_r16"),
           ("cruces_cuartos", "qf", "cruces_qf"),
           ("cruces_semis", "sf", "cruces_sf")]


def _enrich_cruces(pred_list, real_list, tabla):
    """Añade a cada cruce predicho su resultado real (casado POR EQUIPOS, orientado
    a su pronóstico; None si ese enfrentamiento no existe), puntos y categoría."""
    out = []
    for c in (pred_list or []):
        realc = buscar_cruce(c.get("match"), real_list or [])
        pts, tier = puntos_partido(c.get("pred"), realc, tabla)
        out.append({**c, "real": realc, "pts": pts, "tier": tier})
    return out


def _ko_breakdown(res, det):
    """Desglose de puntos de eliminatorias por sección, con flag 'started' (si esa
    sección ya tiene datos reales). Excluye grupos (van aparte) y botas/balones
    (aún no cableadas)."""
    def info_ac(cat):
        return (det.get(cat, {}).get("info") or {}).get("aciertos", 0)

    rows = []
    rows.append({"label": "Posiciones de grupo", "pts": det["posiciones_grupo"]["puntos"],
                 "info": f"{info_ac('posiciones_grupo')} aciertos",
                 "started": bool(res.get("posiciones_grupos"))})
    RND = [("Dieciseisavos", "clasif_dieciseisavos", "cruces_r32", "clasif_dieciseisavos", "cruces_dieciseisavos"),
           ("Octavos", "clasif_octavos", "cruces_r16", "clasif_octavos", "cruces_octavos"),
           ("Cuartos", "clasif_cuartos", "cruces_qf", "clasif_cuartos", "cruces_cuartos"),
           ("Semifinales", "clasif_semis", "cruces_sf", "clasif_semis", "cruces_semis")]
    for label, dclas, dcru, rclas, rcru in RND:
        cp, mp = det[dclas]["puntos"], det[dcru]["puntos"]
        started = bool(res.get(rclas)) or any(c.get("pred") for c in (res.get(rcru) or []))
        rows.append({"label": label, "pts": cp + mp,
                     "info": f"{info_ac(dclas)} clasificados (+{cp}) · marcadores +{mp}", "started": started})
    rows.append({"label": "Finalistas", "pts": det["clasif_final"]["puntos"],
                 "info": f"{info_ac('clasif_final')} aciertos", "started": bool(res.get("finalistas"))})
    rows.append({"label": "Clasif. 3.º y 4.º", "pts": det["clasif_3y4"]["puntos"],
                 "info": f"{info_ac('clasif_3y4')} aciertos", "started": bool(res.get("clasif_34"))})
    rows.append({"label": "Partido 3.º-4.º", "pts": det["partido_3y4"]["puntos"], "info": "",
                 "started": bool((res.get("partido_34") or {}).get("pred"))})
    rows.append({"label": "Final", "pts": det["partido_final"]["puntos"], "info": "",
                 "started": bool((res.get("partido_final") or {}).get("pred"))})
    honor = det["campeon"]["puntos"] + det["subcampeon"]["puntos"] + det["tercero"]["puntos"]
    rows.append({"label": "Campeón · Subcampeón · 3.º", "pts": honor, "info": "",
                 "started": bool(res.get("campeon"))})
    return {"total": sum(r["pts"] for r in rows), "rows": rows,
            "iniciado": any(r["started"] for r in rows)}


def build_participantes(res):
    """Detalle por participante: pronóstico de cada partido de grupos vs real + puntos,
    más el desglose de eliminatorias (cruces con puntos por slot y resumen por sección)."""
    tabla = REGLAS["partidos"]["grupos"]
    out = {}
    for k, pred in PRED.items():
        grupos = []
        for gp, gr in zip(pred["grupos"], res["grupos"]):
            real = gr.get("pred")
            pts, tier = puntos_partido(gp.get("pred"), real, tabla)
            local, visit = [t.strip() for t in gp["match"].split("-", 1)]
            grupos.append({"code": gp["code"], "local": local, "visitante": visit,
                           "pred": gp.get("pred"), "real": real, "pts": pts, "tier": tier})
        det = puntuar(pred, res)["detalle"]
        cruces = {pk: _enrich_cruces(pred.get(pk), res.get(pk), REGLAS["partidos"][tk])
                  for pk, tk, _ in _CRUCES}
        out[k] = {
            "id": k, "nombre": display_name(k),
            "campeon": pred.get("campeon"), "subcampeon": pred.get("subcampeon"),
            "tercero": pred.get("tercero"),
            "bota_oro": pred.get("bota_oro"), "bota_plata": pred.get("bota_plata"),
            "bota_bronce": pred.get("bota_bronce"), "balon_oro": pred.get("balon_oro"),
            "balon_plata": pred.get("balon_plata"), "balon_bronce": pred.get("balon_bronce"),
            "finalistas": pred.get("finalistas"), "clasif_semis": pred.get("clasif_semis"),
            "clasif_cuartos": pred.get("clasif_cuartos"), "clasif_octavos": pred.get("clasif_octavos"),
            "clasif_dieciseisavos": pred.get("clasif_dieciseisavos"),
            "cruces_dieciseisavos": cruces["cruces_dieciseisavos"],
            "cruces_octavos": cruces["cruces_octavos"],
            "cruces_cuartos": cruces["cruces_cuartos"],
            "cruces_semis": cruces["cruces_semis"],
            "partido_34": pred.get("partido_34"), "partido_final": pred.get("partido_final"),
            "ko": _ko_breakdown(res, det),
            "grupos": grupos,
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache")
    args = ap.parse_args()
    payload = json.loads(Path(args.cache).read_text()) if args.cache else fetch_api()
    matches = payload["matches"]

    partidos = overlay_espn(build_partidos(matches), fetch_espn())
    res, jug = build_resultados(partidos)
    tablas_grupos = build_tablas_grupos(partidos)

    # Eliminatorias: alimenta el motor con los resultados reales de KO (posiciones,
    # clasificados, cruces, honor). Protegido: si algo falla, se mantiene la fase de
    # grupos y la web sigue funcionando.
    posic, clasif16 = [], []
    try:
        standings = fetch_standings()
        posic = build_posiciones_oficiales(standings, partidos)
        clasif16 = clasificados_dieciseisavos(standings, partidos)
        res.update(build_ko(partidos, tablas_grupos, posiciones=(posic or None), clasif16=(clasif16 or None)))
    except Exception as e:  # noqa: BLE001
        print(f"  [KO] omitido por error: {e}")

    ranking = build_ranking(res)
    participantes = build_participantes(res)
    goleadores = build_goleadores(fetch_scorers(), build_tla_map(matches))
    timeline = build_timeline(partidos, participantes, res, tablas_grupos, posic, clasif16=(clasif16 or None))
    try:
        proyeccion = proyeccion_cuadro(tablas_grupos)
    except Exception as e:  # noqa: BLE001
        print(f"  [proyección] omitida por error: {e}"); proyeccion = {}
    _lid = [f["nombre"] for f in ranking if f["pos"] == 1]

    data = {
        "generado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "meta": dict(jugados=jug, total_grupos=72, total_partidos=len(partidos),
                     fase_actual="Fase de grupos", participantes=len(PRED),
                     lider=(" y ".join(_lid) if len(_lid) <= 2 else f"{len(_lid)} empatados"),
                     n_lideres=len(_lid), lider_pts=ranking[0]["puntos"]),
        "ranking": ranking,
        "partidos": partidos,
        "participantes": participantes,
        "tablas_grupos": tablas_grupos,
        "goleadores": goleadores,
        "timeline": timeline,
        "proyeccion": proyeccion,
    }
    WEB.mkdir(exist_ok=True)
    (WEB / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK -> web/data.json | {jug}/72 jugados | {len(partidos)} partidos | "
          f"líder: {ranking[0]['nombre']} ({ranking[0]['puntos']}) | {len(participantes)} fichas")


if __name__ == "__main__":
    main()
