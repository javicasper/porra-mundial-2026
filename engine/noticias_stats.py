"""Estadísticas para las crónicas de la porra (pestaña Noticias).

Calcula, para una FASE (jornada 1/2/3 de grupos, fase de grupos completa, o una
ronda de eliminatoria), los datos jugosos para una crónica: clasificación de la
porra, puntos y clavados por participante, resultados reales, sorpresas (upsets)
y mejores aciertos. No escribe prosa: solo devuelve datos (los usa Claude).

Lee web/data.json (ya tiene partidos + participantes con pred/real/pts/tier).
"""
from __future__ import annotations
import json
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _norm(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().strip().lower()


def cargar(data_path=None):
    p = Path(data_path) if data_path else (ROOT / "web" / "data.json")
    return json.loads(p.read_text(encoding="utf-8"))


def stats_jornada(d, jornada):
    """Stats de una jornada de grupos (1, 2 o 3)."""
    parts = d["participantes"]
    # puntos y clavados de ESA jornada por participante
    porj = {}
    for name, P in parts.items():
        pts = cla = dif = sig = jug = 0
        for g in P["grupos"]:
            if (g.get("code") or "")[-1:] != str(jornada) or not g.get("real"):
                continue
            jug += 1
            pts += g["pts"]
            if g["tier"] == "exacto": cla += 1
            elif g["tier"] == "diferencia": dif += 1
            elif g["tier"] == "signo": sig += 1
        porj[P["nombre"]] = {"pts": pts, "clavados": cla, "dif": dif, "signo": sig, "jugados": jug}
    # resultados reales de la jornada + dificultad (cuántos acertaron signo/exacto)
    resultados = []
    vistos = set()
    for name, P in parts.items():
        for g in P["grupos"]:
            if (g.get("code") or "")[-1:] != str(jornada) or not g.get("real"):
                continue
            k = (g["local"], g["visitante"])
            if k in vistos: continue
            vistos.add(k)
            r = g["real"]
            # cuántos participantes clavaron / acertaron signo este partido
            cl = sg = 0
            for Q in parts.values():
                gg = next((x for x in Q["grupos"] if x["local"] == g["local"] and x["visitante"] == g["visitante"]), None)
                if gg and gg.get("pred"):
                    if gg["tier"] == "exacto": cl += 1
                    if gg["tier"] in ("exacto", "diferencia", "signo"): sg += 1
            resultados.append({"local": g["local"], "visitante": g["visitante"],
                               "marcador": f"{r['home']}-{r['away']}", "sign": r["sign"],
                               "clavaron": cl, "acertaron_signo": sg, "n": len(parts)})
    rank = sorted(porj.items(), key=lambda kv: (-kv[1]["pts"], -kv[1]["clavados"], kv[0]))
    upsets = sorted(resultados, key=lambda r: (r["acertaron_signo"], r["clavaron"]))[:5]
    faciles = sorted(resultados, key=lambda r: (-r["clavaron"], -r["acertaron_signo"]))[:5]
    return {"jornada": jornada, "n_partidos": len(resultados),
            "ranking_jornada": [{"nombre": n, **s} for n, s in rank],
            "resultados": resultados, "upsets": upsets, "mas_clavados": faciles}


def stats_grupos(d):
    """Stats de toda la fase de grupos."""
    parts = d["participantes"]
    tot = {}
    for name, P in parts.items():
        jug = [g for g in P["grupos"] if g.get("real")]
        tot[P["nombre"]] = {
            "pts": sum(g["pts"] for g in jug),
            "clavados": sum(1 for g in jug if g["tier"] == "exacto"),
            "dif": sum(1 for g in jug if g["tier"] == "diferencia"),
            "signo": sum(1 for g in jug if g["tier"] == "signo"),
            "campeon": P.get("campeon"),
        }
    rank = sorted(tot.items(), key=lambda kv: (-kv[1]["pts"], -kv[1]["clavados"], kv[0]))
    # ranking oficial de la porra (con posiciones/clasif ya puntuados) = d["ranking"]
    return {"ranking_porra": d.get("ranking", []),
            "resumen_grupos": [{"nombre": n, **s} for n, s in rank],
            "tablas_grupos": d.get("tablas_grupos", {}),
            "goleadores": (d.get("goleadores") or [])[:5]}


_KO_KEY = {"Dieciseisavos": "cruces_dieciseisavos", "Octavos": "cruces_octavos",
           "Cuartos": "cruces_cuartos", "Semifinales": "cruces_semis"}


def stats_ko(d, fase):
    """Stats de una ronda de eliminatoria (fase = 'Dieciseisavos'...'Semifinales')."""
    parts = d["participantes"]
    key = _KO_KEY[fase]
    pj = [p for p in d["partidos"] if p.get("fase") == fase and p.get("jugado") and p.get("golesLocal") is not None]
    resultados = []
    for p in pj:
        gan = p["local"] if p.get("ganador") == "local" else (p["visitante"] if p.get("ganador") == "visitante" else None)
        resultados.append({"local": p["local"], "visitante": p["visitante"],
                           "marcador": f"{p['golesLocal']}-{p['golesVisitante']}", "avanza": gan})
    # puntos y clavados de marcador de la ronda por participante
    porp = {}
    for P in parts.values():
        pts = cla = 0
        for c in (P.get(key) or []):
            if c.get("real"):
                pts += c.get("pts", 0)
                if c.get("tier") == "exacto":
                    cla += 1
        porp[P["nombre"]] = {"pts": pts, "clavados": cla}
    rank = sorted(porp.items(), key=lambda kv: (-kv[1]["pts"], -kv[1]["clavados"], kv[0]))
    # eliminados y quién los tenía de campeón (para el roast)
    avanzan = {_norm(r["avanza"]) for r in resultados if r["avanza"]}
    jugaron = {t for r in resultados for t in (r["local"], r["visitante"])}
    eliminados = sorted(t for t in jugaron if _norm(t) not in avanzan)
    campeones_eliminados = {}
    for t in eliminados:
        fans = [P["nombre"] for P in parts.values() if _norm(P.get("campeon")) == _norm(t)]
        if fans:
            campeones_eliminados[t] = fans
    return {"fase": fase, "resultados": resultados,
            "ranking_ronda": [{"nombre": n, **s} for n, s in rank],
            "eliminados": eliminados, "campeones_eliminados": campeones_eliminados,
            "ranking_porra": [{"nombre": x["nombre"], "pos": x["pos"], "puntos": x["puntos"]} for x in (d.get("ranking") or [])[:6]]}


def stats_partido(d, fase, local, visitante):
    """Datos de la PORRA para un solo cruce de eliminatoria (para la mini-crónica)."""
    parts = d["participantes"]
    key = _KO_KEY[fase]
    pj = next((p for p in d["partidos"] if p.get("fase") == fase and p.get("local") == local
               and p.get("visitante") == visitante and p.get("jugado")), None)
    if not pj or pj.get("golesLocal") is None:
        return None
    gl, gv = pj["golesLocal"], pj["golesVisitante"]
    gan = local if pj.get("ganador") == "local" else (visitante if pj.get("ganador") == "visitante" else None)
    elim = visitante if gan == local else (local if gan == visitante else None)
    predijeron = []
    for Q in parts.values():
        for c in (Q.get(key) or []):
            m = c.get("match", "")
            if c.get("real") and local in m and visitante in m:
                predijeron.append({"nombre": Q["nombre"],
                                   "pred": f'{c["pred"]["home"]}-{c["pred"]["away"]}',
                                   "tier": c.get("tier"), "pts": c.get("pts", 0)})
                break
    clavaron = [a["nombre"] for a in predijeron if a["tier"] == "exacto"]
    camp_elim = [Q["nombre"] for Q in parts.values() if elim and _norm(Q.get("campeon")) == _norm(elim)]
    return {"local": local, "visitante": visitante, "marcador": f"{gl}-{gv}",
            "avanza": gan, "eliminado": elim, "n_participantes": len(parts),
            "predijeron_cruce": predijeron, "clavaron_marcador": clavaron,
            "campeon_eliminado": camp_elim}


if __name__ == "__main__":
    import sys
    d = cargar(sys.argv[1] if len(sys.argv) > 1 else None)
    print("=== JORNADAS ===")
    for j in (1, 2, 3):
        s = stats_jornada(d, j)
        if not s["n_partidos"]:
            continue
        top = s["ranking_jornada"][0]
        print(f"\nJ{j}: {s['n_partidos']} partidos | mejor de la jornada: {top['nombre']} ({top['pts']} pts, {top['clavados']} clavados)")
        print("  upsets (menos acertaron signo):")
        for u in s["upsets"][:3]:
            print(f"    {u['local']} {u['marcador']} {u['visitante']}  -> signo: {u['acertaron_signo']}/{u['n']}, clavado: {u['clavaron']}")
    print("\n=== FASE DE GRUPOS ===")
    g = stats_grupos(d)
    for r in g["resumen_grupos"][:5]:
        print(f"  {r['nombre']:<10} {r['pts']} pts | clavados {r['clavados']} | dif {r['dif']} | signo {r['signo']}")
