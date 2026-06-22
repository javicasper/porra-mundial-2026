"""Motor de puntuacion de la Porra Mundial 2026.

Compara las predicciones de cada participante con los resultados reales y
devuelve un desglose por categoria + total. Soporta resultados PARCIALES:
solo puntua lo que ya este resuelto (campos None en `resultados` se ignoran).

Modelo de datos (predicciones y resultados comparten forma; ver data/predicciones.json):
  - grupos[72]            : {code, match, pred:{sign,home,away}}
  - posiciones_grupos[48] : {pos:"1º GRUPO A", team}
  - clasif_*              : [equipos] que alcanzan esa ronda
  - cruces_*              : [{match, pred:{sign,home,away}}]  (resultado 90'+prorroga)
  - finalistas / clasif_34: [equipos]
  - partido_34, partido_final : {match, pred:{...}}
  - campeon / subcampeon / tercero
  - bota_*/balon_*        : nombre de jugador

Reglas en data/reglas.json. Por partido se otorga la MEJOR categoria alcanzada
(exacto > diferencia > signo), no acumulan.
"""
from __future__ import annotations
import json, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGLAS = json.loads((ROOT / "data" / "reglas.json").read_text(encoding="utf-8"))


# ---------- normalizacion de texto (equipos / jugadores) ----------
def norm(s):
    if s is None:
        return None
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.strip().lower()


# ---------- comparacion de un partido ----------
def tier_partido(pred, real):
    """Devuelve 'exacto' | 'diferencia' | 'signo' | None segun la mejor categoria."""
    if not pred or not real or "sign" not in pred or "sign" not in real:
        return None
    if pred["home"] == real["home"] and pred["away"] == real["away"]:
        return "exacto"
    mismo_signo = pred["sign"] == real["sign"]
    misma_dif = (pred["home"] - pred["away"]) == (real["home"] - real["away"])
    if mismo_signo and misma_dif:
        return "diferencia"
    if mismo_signo:
        return "signo"
    return None


def puntos_partido(pred, real, tabla):
    """Puntos de un partido. Regla del concurso: el 'resultado exacto' ACUMULA
    los puntos de 'diferencia' (exacto = dif + exacto). El 'signo' no acumula."""
    t = tier_partido(pred, real)
    if t is None:
        return (0, None)
    if t == "exacto":
        return (tabla["diferencia"] + tabla["exacto"], t)
    return (tabla[t], t)


# ---------- helpers de conjuntos ----------
def aciertos_lista(pred_list, real_list):
    """Equipos del pronostico que SI estan en el conjunto real (orden irrelevante)."""
    real_set = {norm(x) for x in (real_list or []) if x}
    return [p for p in (pred_list or []) if p and norm(p) in real_set]


def rank_de_pos(pos_label):
    """'1º GRUPO A' -> '1'."""
    for r in ("1", "2", "3", "4"):
        if pos_label and pos_label.strip().startswith(r):
            return r
    return None


def _equipos(match):
    """'EquipoA-EquipoB' -> [normA, normB] (None si no parseable)."""
    if not match:
        return None
    parts = [norm(t) for t in match.split("-", 1)]
    return parts if len(parts) == 2 and all(parts) else None


def buscar_cruce(pred_match, real_list):
    """Marcador real de un cruce de eliminatoria, casado POR EQUIPOS (regla de la
    porra, confirmada en el Excel/oficial): busca en `real_list` (los partidos
    REALES de esa ronda) el que enfrenta a la MISMA pareja que `pred_match`, en
    CUALQUIER orden y sin importar la posición/fila. Devuelve el marcador real
    orientado al local del pronóstico, o None si ese enfrentamiento no existe
    ("si un partido no existe no suma puntos")."""
    te = _equipos(pred_match)
    if not te:
        return None
    ph, pa = te
    for b in real_list or []:
        rp = b.get("pred")
        if not rp:
            continue
        rl, rv = norm(b.get("local")), norm(b.get("visitante"))
        if {rl, rv} != {ph, pa}:
            continue
        if rl == ph:                      # mismo orden que el pronóstico
            return {"sign": rp["sign"], "home": rp["home"], "away": rp["away"]}
        # equipos invertidos respecto al pronóstico: giramos el marcador
        return {"sign": {"1": "2", "2": "1"}.get(rp["sign"], "X"),
                "home": rp["away"], "away": rp["home"]}
    return None


# ---------- motor principal ----------
def puntuar(pred, res):
    """Puntua una prediccion contra unos resultados (posiblemente parciales).

    Marcadores de eliminatorias: POR EQUIPOS. Un cruce pronosticado puntua su
    marcador solo si esa pareja de equipos se enfrenta de verdad en esa ronda
    (en cualquier orden y posicion); si no, 0. Los 'clasificados' van aparte.
    Devuelve dict con desglose y total.
    """
    R = REGLAS
    out = {"detalle": {}, "total": 0}

    def add(cat, pts, info=None):
        out["detalle"][cat] = {"puntos": pts, **({"info": info} if info else {})}
        out["total"] += pts

    # 1) Fase de grupos (72 partidos)
    pts = 0; brk = {"exacto": 0, "diferencia": 0, "signo": 0}
    for gp, gr in zip(pred.get("grupos", []), res.get("grupos", [])):
        if not gr.get("pred"):
            continue
        p, t = puntos_partido(gp.get("pred"), gr.get("pred"), R["partidos"]["grupos"])
        pts += p
        if t: brk[t] += 1
    add("grupos_partidos", pts, brk)

    # 2) Posiciones de grupo (48 slots)
    pts = 0; ok = 0
    real_pos = {p["pos"]: p["team"] for p in res.get("posiciones_grupos", []) if p.get("team")}
    for pp in pred.get("posiciones_grupos", []):
        rt = real_pos.get(pp["pos"])
        if rt and norm(pp["team"]) == norm(rt):
            pts += R["posicion_grupo"][rank_de_pos(pp["pos"])]; ok += 1
    add("posiciones_grupo", pts, {"aciertos": ok})

    # 3) Clasificados por ronda  +  4) marcadores de cruces
    rondas = [
        ("clasif_dieciseisavos", "clasificados", "dieciseisavos", "cruces_dieciseisavos", "r32"),
        ("clasif_octavos",       "clasificados", "octavos",       "cruces_octavos",       "r16"),
        ("clasif_cuartos",       "clasificados", "cuartos",       "cruces_cuartos",       "qf"),
        ("clasif_semis",         "clasificados", "semis",         "cruces_semis",         "sf"),
    ]
    for clasif_key, _, clasif_pts_key, cruces_key, tabla_key in rondas:
        # clasificados
        ac = aciertos_lista(pred.get(clasif_key), res.get(clasif_key))
        ppt = len(ac) * R["clasificados"][clasif_pts_key]
        add(f"clasif_{clasif_pts_key}", ppt, {"aciertos": len(ac)})
        # cruces (marcadores) — POR EQUIPOS: la pareja debe enfrentarse de verdad
        pts = 0; brk = {"exacto": 0, "diferencia": 0, "signo": 0}
        rc = res.get(cruces_key, [])
        for a in pred.get(cruces_key, []):
            rp = buscar_cruce(a.get("match"), rc)
            if not rp:
                continue
            p, t = puntos_partido(a.get("pred"), rp, R["partidos"][tabla_key])
            pts += p
            if t: brk[t] += 1
        add(f"cruces_{tabla_key}", pts, brk)

    # 5) Finalistas y 3º/4º (clasificados)
    ac = aciertos_lista(pred.get("finalistas"), res.get("finalistas"))
    add("clasif_final", len(ac) * R["clasificados"]["final"], {"aciertos": len(ac)})
    ac = aciertos_lista(pred.get("clasif_34"), res.get("clasif_34"))
    add("clasif_3y4", len(ac) * R["clasificados"]["tercer_cuarto_puesto"], {"aciertos": len(ac)})

    # 6) Partido 3º-4º puesto y Final (marcadores)
    p, t = puntos_partido((pred.get("partido_34") or {}).get("pred"),
                          (res.get("partido_34") or {}).get("pred"), R["partidos"]["tercer_puesto"])
    add("partido_3y4", p, t)
    p, t = puntos_partido((pred.get("partido_final") or {}).get("pred"),
                          (res.get("partido_final") or {}).get("pred"), R["partidos"]["final"])
    add("partido_final", p, t)

    # 7) Cuadro de honor
    for cat, key in (("campeon", "campeon"), ("subcampeon", "subcampeon"), ("tercero", "tercero")):
        rv = res.get(key)
        hit = rv and norm(pred.get(key)) == norm(rv)
        add(cat, R["cuadro_honor"][cat] if hit else 0)

    # 8) Botas y balones
    for key, pkey in (("bota_oro","bota_oro"),("bota_plata","bota_plata"),("bota_bronce","bota_bronce"),
                      ("balon_oro","balon_oro"),("balon_plata","balon_plata"),("balon_bronce","balon_bronce")):
        rv = res.get(key)
        hit = rv and norm(pred.get(key)) == norm(rv)
        add(key, R["especiales"][pkey] if hit else 0)

    return out


def clasificacion(predicciones, resultados, **kw):
    """Devuelve lista [(nombre, total, desglose)] ordenada desc."""
    tabla = []
    for nombre, pred in predicciones.items():
        r = puntuar(pred, resultados, **kw)
        tabla.append((nombre, r["total"], r))
    tabla.sort(key=lambda x: -x[1])
    return tabla
