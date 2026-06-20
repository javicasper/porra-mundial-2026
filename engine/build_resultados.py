"""Construye data/resultados.json (esquema porra) desde football-data.org.

Por ahora rellena los marcadores de la FASE DE GRUPOS ya jugados. El resto
de la estructura (posiciones, clasificados, eliminatorias, honor, botas) se
deja vacio hasta que la competicion avance y la API lo determine.

Uso:
    FOOTBALLDATA_API_KEY=xxx python engine/build_resultados.py
    # o, sin red, usa un volcado cacheado:
    python engine/build_resultados.py --cache /tmp/wcm.json
"""
from __future__ import annotations
import argparse, json, os, sys, urllib.request, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MAP = {k: v for k, v in json.loads((DATA / "equipos_map.json").read_text(encoding="utf-8")).items()
       if not k.startswith("_")}
_PRED_FILE = DATA / "predicciones.json"
if not _PRED_FILE.exists():
    _PRED_FILE = DATA / "predicciones.sample.json"
PRED = json.loads(_PRED_FILE.read_text(encoding="utf-8"))


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.strip().lower()


def es(nombre_en):
    if nombre_en in MAP:
        return MAP[nombre_en]
    raise KeyError(f"Equipo API sin mapear: {nombre_en!r}")


def signo(gh, ga):
    return "1" if gh > ga else ("2" if ga > gh else "X")


def fetch_api():
    key = os.environ.get("FOOTBALLDATA_API_KEY")
    if not key:
        sys.exit("ERROR: falta FOOTBALLDATA_API_KEY (o usa --cache).")
    req = urllib.request.Request(
        "https://api.football-data.org/v4/competitions/WC/matches",
        headers={"X-Auth-Token": key})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())["matches"]


def build(matches):
    # 1) Resultados de grupos por par de equipos (normalizado), guardando orientacion
    por_par = {}  # frozenset(homeES,awayES) -> (homeES, gh, ga)
    jugados = 0
    for m in matches:
        if m["stage"] != "GROUP_STAGE" or m["status"] != "FINISHED":
            continue
        h, a = es(m["homeTeam"]["name"]), es(m["awayTeam"]["name"])
        ft = m["score"]["fullTime"]
        gh, ga = ft["home"], ft["away"]
        por_par[frozenset((norm(h), norm(a)))] = (norm(h), gh, ga)
        jugados += 1

    # 2) Recorrer el fixture canonico (orden de cualquier participante) y volcar
    fixture = PRED[sorted(PRED)[0]]["grupos"]  # 72 partidos, orden estable
    grupos_res = []
    rellenos = 0
    for fx in fixture:
        local, visit = [t.strip() for t in fx["match"].split("-", 1)]
        key = frozenset((norm(local), norm(visit)))
        entry = {"code": fx["code"], "match": fx["match"], "pred": None}
        if key in por_par:
            home_norm, gh, ga = por_par[key]
            # Reorientar al orden de la porra (local-visit)
            if home_norm == norm(local):
                h, v = gh, ga
            else:
                h, v = ga, gh
            entry["pred"] = {"sign": signo(h, v), "home": h, "away": v}
            rellenos += 1
        grupos_res.append(entry)

    res = {
        "_fuente": "football-data.org WC (id 2000)",
        "_grupos_jugados": rellenos,
        "grupos": grupos_res,
        # Pendientes hasta que avance el torneo:
        "posiciones_grupos": [], "clasif_dieciseisavos": [], "cruces_dieciseisavos": [],
        "clasif_octavos": [], "cruces_octavos": [], "clasif_cuartos": [], "cruces_cuartos": [],
        "clasif_semis": [], "cruces_semis": [], "clasif_34": [], "finalistas": [],
        "partido_34": {"match": None, "pred": None}, "partido_final": {"match": None, "pred": None},
        "campeon": None, "subcampeon": None, "tercero": None,
        "bota_oro": None, "bota_plata": None, "bota_bronce": None,
        "balon_oro": None, "balon_plata": None, "balon_bronce": None,
    }
    return res, jugados, rellenos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", help="ruta a un volcado JSON de /matches (en vez de la API)")
    args = ap.parse_args()
    if args.cache:
        matches = json.loads(Path(args.cache).read_text())["matches"]
    else:
        matches = fetch_api()
    res, jugados, rellenos = build(matches)
    (DATA / "resultados.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"API: {jugados} partidos de grupos FINISHED")
    print(f"Volcados al fixture de la porra: {rellenos}/72")
    if jugados != rellenos:
        print(f"⚠️  {jugados-rellenos} partidos de la API no casaron con el fixture (revisar nombres/orientacion)")
    print("-> data/resultados.json")


if __name__ == "__main__":
    main()
