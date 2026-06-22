"""Tests del cableado de ELIMINATORIAS (engine/ko_resultados.py + scoring por equipos).

Regla: el marcador de un cruce puntúa si esa PAREJA de equipos se enfrenta de
verdad en esa ronda (cualquier orden, cualquier posición); si no, 0.

Estrategia: Mundial sintético terminado cuya "realidad" es el cuadro de un
participante. Ese participante debe sacar el máximo, y debe dar igual:
  - que la API ponga los equipos en orden invertido (local/visitante),
  - que los partidos de la ronda vengan en otra posición/orden de lista.
Y build_ko(realidad=A) debe ser equivalente a usar las predicciones de A como
resultados (puntuar a cualquier B da lo mismo).

Uso: python engine/test_ko.py
"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scoring import puntuar, buscar_cruce, _equipos  # noqa: E402
from ko_resultados import build_ko, _norm  # noqa: E402

PRED = json.loads((Path(__file__).resolve().parent.parent / "data" / "predicciones.json").read_text(encoding="utf-8"))
RONDAS = [("cruces_dieciseisavos", "Dieciseisavos", "clasif_octavos"),
          ("cruces_octavos", "Octavos", "clasif_cuartos"),
          ("cruces_cuartos", "Cuartos", "clasif_semis"),
          ("cruces_semis", "Semifinales", "finalistas")]


def _side(local, ganador):
    return "local" if _norm(local) == _norm(ganador) else "visitante"


def synth_partidos(X, flip=False, shuffle=False):
    """Partidos (formato build_web_data) desde el cuadro de X."""
    ps = []

    def add(fase, grupo, h, a, pr, gan, idx):
        gl, gv = pr["home"], pr["away"]
        if flip and idx % 2 == 0:            # la API invierte local/visitante en alternos
            h, a, gl, gv = a, h, gv, gl
            gan = {"local": "visitante", "visitante": "local"}.get(gan)
        ps.append({"fase": fase, "grupo": grupo, "local": h, "visitante": a,
                   "golesLocal": gl, "golesVisitante": gv, "jugado": True, "ganador": gan})

    for i, g in enumerate(X["grupos"]):
        h, a = [t.strip() for t in g["match"].split("-", 1)]
        add("Grupos", g["code"][0], h, a, g["pred"], {"1": "local", "2": "visitante"}.get(g["pred"]["sign"]), i)
    for cru, fase, clas_sig in RONDAS:
        adv = {_norm(t) for t in X.get(clas_sig, [])}
        ties = list(enumerate(X[cru]))
        if shuffle:
            ties = ties[::-1]                # misma ronda, otra posición/orden de lista
        for i, tie in ties:
            h, a = [t.strip() for t in tie["match"].split("-", 1)]
            gan = "local" if _norm(h) in adv else ("visitante" if _norm(a) in adv else None)
            add(fase, "", h, a, tie["pred"], gan, i)
    for key, fase, hon in [("partido_final", "Final", "campeon"), ("partido_34", "3er puesto", "tercero")]:
        d = X[key]; h, a = [t.strip() for t in d["match"].split("-", 1)]
        add(fase, "", h, a, d["pred"], _side(h, X[hon]), 1)
    return ps


def synth_posiciones(X):
    return list(X["posiciones_grupos"])


def res_ideal(X):
    """Resultados 'perfectos' = predicciones de X como realidad (cruces como lista
    de partidos reales, igual que produce build_ko)."""
    cru = {pk: [{"local": _equipos(t["match"]) and t["match"].split("-", 1)[0].strip(),
                 "visitante": t["match"].split("-", 1)[1].strip(), "pred": t["pred"]}
                for t in X[pk]] for pk, _, _ in RONDAS}
    return {
        "grupos": [{"pred": g["pred"]} for g in X["grupos"]],
        "posiciones_grupos": X["posiciones_grupos"],
        "clasif_dieciseisavos": X["clasif_dieciseisavos"], "cruces_dieciseisavos": cru["cruces_dieciseisavos"],
        "clasif_octavos": X["clasif_octavos"], "cruces_octavos": cru["cruces_octavos"],
        "clasif_cuartos": X["clasif_cuartos"], "cruces_cuartos": cru["cruces_cuartos"],
        "clasif_semis": X["clasif_semis"], "cruces_semis": cru["cruces_semis"],
        "clasif_34": X["clasif_34"], "finalistas": X["finalistas"],
        "partido_34": X["partido_34"], "partido_final": X["partido_final"],
        "campeon": X["campeon"], "subcampeon": X["subcampeon"], "tercero": X["tercero"],
        "bota_oro": X["bota_oro"], "bota_plata": X["bota_plata"], "bota_bronce": X["bota_bronce"],
        "balon_oro": X["balon_oro"], "balon_plata": X["balon_plata"], "balon_bronce": X["balon_bronce"],
    }


def build_full(X, flip=False, shuffle=False):
    ko = build_ko(synth_partidos(X, flip, shuffle), {}, posiciones=synth_posiciones(X))
    res = {"grupos": [{"pred": g["pred"]} for g in X["grupos"]], **ko}
    for k in ("bota_oro", "bota_plata", "bota_bronce", "balon_oro", "balon_plata", "balon_bronce"):
        res[k] = X[k]
    return res


def main():
    fails = []

    # 0) buscar_cruce: orden invertido suma; cruce inexistente no
    real = [{"local": "Croacia", "visitante": "Francia", "pred": {"sign": "2", "home": 0, "away": 1}}]
    inv = buscar_cruce("Francia-Croacia", real)
    if inv != {"sign": "1", "home": 1, "away": 0}:
        fails.append(f"buscar_cruce orden invertido mal: {inv}")
    if buscar_cruce("España-Portugal", real) is not None:
        fails.append("buscar_cruce: un cruce inexistente debería dar None")

    # 1) Cada participante contra su propio cuadro = máximo, con orden invertido y reordenado
    for name, X in sorted(PRED.items()):
        target = puntuar(X, res_ideal(X))["total"]
        for flip, shuf in [(False, False), (True, False), (False, True), (True, True)]:
            got = puntuar(X, build_full(X, flip, shuf))["total"]
            if got != target:
                fails.append(f"{name} flip={flip} shuffle={shuf}: got={got} target={target}")

    # 2) build_ko(realidad=A) equivale a usar las predicciones de A como resultados
    names = sorted(PRED)
    for A in names[:4]:
        res = build_full(PRED[A])
        ideal = res_ideal(PRED[A])
        for Bn in names:
            if puntuar(PRED[Bn], res)["total"] != puntuar(PRED[Bn], ideal)["total"]:
                fails.append(f"equivalencia realidad={A} scoring={Bn}")

    # 3) Cruce INEXISTENTE: si un cruce de X no se da en la realidad, pierde justo su marcador
    X = PRED[names[0]]
    base = puntuar(X, build_full(X))["total"]
    ps = synth_partidos(X)
    # cambiar los equipos de un dieciseisavos por una pareja que X no predijo en esa ronda
    d16 = [p for p in ps if p["fase"] == "Dieciseisavos"]
    victim = d16[0]
    pred_tie = X["cruces_dieciseisavos"][0]
    h, a = [t.strip() for t in pred_tie["match"].split("-", 1)]
    # puntos de marcador que daba ese cruce contra sí mismo:
    from scoring import puntos_partido, REGLAS
    lost, _ = puntos_partido(pred_tie["pred"], pred_tie["pred"], REGLAS["partidos"]["r32"])
    victim["local"], victim["visitante"] = "ZZ_Inventado_1", "ZZ_Inventado_2"  # ese cruce ya no existe
    ko = build_ko(ps, {}, posiciones=synth_posiciones(X))
    res = {"grupos": [{"pred": g["pred"]} for g in X["grupos"]], **ko}
    for k in ("bota_oro", "bota_plata", "bota_bronce", "balon_oro", "balon_plata", "balon_bronce"):
        res[k] = X[k]
    got = puntuar(X, res)["total"]
    # pierde el marcador de ese cruce y, además, los 2 equipos dejan de estar en R32 (clasif)
    if got >= base:
        fails.append(f"cruce inexistente: el total no bajó ({got} >= {base})")
    if base - got < lost:
        fails.append(f"cruce inexistente: bajó {base-got}, esperado >= {lost} (marcador perdido)")

    # 4) Parcial: sin KO, sin puntos de KO ni crash
    solo_grupos = [p for p in synth_partidos(PRED[names[0]]) if p["fase"] == "Grupos"]
    ko_p = build_ko(solo_grupos, {}, posiciones=[])
    if any(ko_p[k] for k in ("clasif_dieciseisavos", "cruces_dieciseisavos", "finalistas")) or ko_p["campeon"]:
        fails.append("parcial: no debería haber datos de KO solo con grupos")

    if fails:
        print("FALLOS:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print(f"OK — {len(PRED)} participantes x4 (orden/posición) = máximo; "
          f"orden invertido, cruce inexistente, equivalencia y parcial correctos.")


if __name__ == "__main__":
    main()
