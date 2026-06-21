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
from scoring import puntuar, puntos_partido, REGLAS  # noqa: E402

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
        ft = m["score"]["fullTime"]
        fin = m["status"] == "FINISHED"
        live = m["status"] in ("IN_PLAY", "PAUSED")
        show = fin or live
        out.append({
            "fase": STAGE_ES.get(m["stage"], m["stage"]),
            "grupo": (m.get("group") or "").replace("GROUP_", ""),
            "jornada": m.get("matchday") if m["stage"] == "GROUP_STAGE" else None,
            "utc": m.get("utcDate"),
            "local": es(m["homeTeam"]["name"]) if m["homeTeam"].get("name") else None,
            "visitante": es(m["awayTeam"]["name"]) if m["awayTeam"].get("name") else None,
            "golesLocal": ft.get("home") if show else None,
            "golesVisitante": ft.get("away") if show else None,
            "status": m["status"],
            "jugado": fin,
            "envivo": live,
            "minuto": None,
            "eventos": None,
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
            out.append({"key": (e.get("date") or "")[:16],
                        "state": e["status"]["type"]["state"],          # pre | in | post
                        "clock": e["status"].get("displayClock"),
                        "home": sc(h), "away": sc(a), "eventos": eventos})
        except Exception:
            continue
    return out


def overlay_espn(partidos, espn):
    """Superpone ESPN (más fresca que football-data free): marcador y minuto en
    vivo, y también marca FINALIZADO en cuanto ESPN lo da por terminado."""
    by_key = {e["key"]: e for e in espn if e.get("key")}
    for p in partidos:
        e = by_key.get((p.get("utc") or "")[:16])
        if not e:
            continue
        if e["state"] == "in":
            p["envivo"], p["jugado"], p["status"] = True, False, "IN_PLAY"
            if e["home"] is not None: p["golesLocal"] = e["home"]
            if e["away"] is not None: p["golesVisitante"] = e["away"]
            p["minuto"] = e["clock"]
            p["eventos"] = e.get("eventos") or None
        elif e["state"] == "post":
            p["envivo"], p["jugado"], p["status"], p["minuto"] = False, True, "FINISHED", None
            if e["home"] is not None: p["golesLocal"] = e["home"]
            if e["away"] is not None: p["golesVisitante"] = e["away"]
            p["eventos"] = e.get("eventos") or None
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


def build_timeline(partidos, participantes):
    """Histórico de puntos: cada X = un partido de grupos jugado (cronológico),
    Y = puntos acumulados de cada participante."""
    played = [p for p in partidos if p.get("grupo") and p.get("jugado")
              and p.get("golesLocal") is not None and p.get("utc")]
    played.sort(key=lambda p: p["utc"])
    keyseq, labels = [], ["Inicio"]
    for p in played:
        keyseq.append(frozenset((norm(p["local"]), norm(p["visitante"]))))
        dt = datetime.fromisoformat(p["utc"].replace("Z", "+00:00")) + timedelta(hours=2)
        labels.append(f"{dt.day}/{dt.month}")
    series = {}
    for pid, P in participantes.items():
        ptsby = {frozenset((norm(g["local"]), norm(g["visitante"]))): g["pts"]
                 for g in P["grupos"] if g.get("real")}
        cum, arr = 0, [0]
        for k in keyseq:
            cum += ptsby.get(k, 0)
            arr.append(cum)
        series[pid] = arr
    return {"x": labels, "series": series}


def build_participantes(res):
    """Detalle por participante: pronóstico de cada partido de grupos vs real + puntos."""
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
            "cruces_dieciseisavos": pred.get("cruces_dieciseisavos"),
            "cruces_octavos": pred.get("cruces_octavos"),
            "cruces_cuartos": pred.get("cruces_cuartos"),
            "cruces_semis": pred.get("cruces_semis"),
            "partido_34": pred.get("partido_34"), "partido_final": pred.get("partido_final"),
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
    ranking = build_ranking(res)
    participantes = build_participantes(res)
    tablas_grupos = build_tablas_grupos(partidos)
    goleadores = build_goleadores(fetch_scorers(), build_tla_map(matches))
    timeline = build_timeline(partidos, participantes)
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
    }
    WEB.mkdir(exist_ok=True)
    (WEB / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK -> web/data.json | {jug}/72 jugados | {len(partidos)} partidos | "
          f"líder: {ranking[0]['nombre']} ({ranking[0]['puntos']}) | {len(participantes)} fichas")


if __name__ == "__main__":
    main()
