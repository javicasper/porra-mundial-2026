"""Tests del cableado de ELIMINATORIAS (engine/ko_resultados.py).

Estrategia: se fabrica un Mundial sintético YA TERMINADO cuya "realidad" es el
cuadro completo de un participante. Entonces:
  - ese participante debe sacar el MÁXIMO TEÓRICO (todo acertado),
  - build_ko debe reconstruir su cuadro slot a slot (orden + orientación),
  - y debe dar lo mismo aunque la API ponga local/visitante AL REVÉS,
  - y build_ko(realidad=A) debe ser equivalente a usar las predicciones de A
    como resultados (puntuar a cualquier B da igual con ambos).

Uso: python engine/test_ko.py
"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scoring import puntuar
from ko_resultados import build_ko, canonical_bracket, _norm

PRED = json.loads((Path(__file__).resolve().parent.parent / "data" / "predicciones.json").read_text(encoding="utf-8"))
B = canonical_bracket(PRED)


def _side(local, ganador):
    return "local" if _norm(local) == _norm(ganador) else "visitante"


def synth_partidos(X, flip=False):
    """Partidos (formato build_web_data) desde el cuadro de X. flip=True invierte
    local/visitante en partidos alternos (la API no respeta la orientación canónica)."""
    ps = []

    def add(fase, grupo, h, a, pr, gan, idx):
        gl, gv = pr["home"], pr["away"]
        loc, vis, gloc, gvis = h, a, gl, gv
        g_side = gan
        if flip and idx % 2 == 0:
            loc, vis, gloc, gvis = a, h, gv, gl
            g_side = {"local": "visitante", "visitante": "local"}.get(gan)
        ps.append({"fase": fase, "grupo": grupo, "local": loc, "visitante": vis,
                   "golesLocal": gloc, "golesVisitante": gvis, "jugado": True, "ganador": g_side})

    for i, g in enumerate(X["grupos"]):
        h, a = [t.strip() for t in g["match"].split("-", 1)]
        pr = g["pred"]
        add("Grupos", g["code"][0], h, a, pr, {"1": "local", "2": "visitante"}.get(pr["sign"]), i)
    rondas = [("cruces_dieciseisavos", "Dieciseisavos", "clasif_octavos"),
              ("cruces_octavos", "Octavos", "clasif_cuartos"),
              ("cruces_cuartos", "Cuartos", "clasif_semis"),
              ("cruces_semis", "Semifinales", "finalistas")]
    for cru, fase, clas_sig in rondas:
        adv = {_norm(t) for t in X.get(clas_sig, [])}
        for i, tie in enumerate(X[cru]):
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
    return {
        "grupos": [{"pred": g["pred"]} for g in X["grupos"]],
        "posiciones_grupos": X["posiciones_grupos"],
        "clasif_dieciseisavos": X["clasif_dieciseisavos"], "cruces_dieciseisavos": X["cruces_dieciseisavos"],
        "clasif_octavos": X["clasif_octavos"], "cruces_octavos": X["cruces_octavos"],
        "clasif_cuartos": X["clasif_cuartos"], "cruces_cuartos": X["cruces_cuartos"],
        "clasif_semis": X["clasif_semis"], "cruces_semis": X["cruces_semis"],
        "clasif_34": X["clasif_34"], "finalistas": X["finalistas"],
        "partido_34": X["partido_34"], "partido_final": X["partido_final"],
        "campeon": X["campeon"], "subcampeon": X["subcampeon"], "tercero": X["tercero"],
        "bota_oro": X["bota_oro"], "bota_plata": X["bota_plata"], "bota_bronce": X["bota_bronce"],
        "balon_oro": X["balon_oro"], "balon_plata": X["balon_plata"], "balon_bronce": X["balon_bronce"],
    }


def build_full(X, flip=False):
    """res completo = grupos + KO (build_ko) + botas/balones (fuera del alcance de build_ko)."""
    ko = build_ko(synth_partidos(X, flip), {}, PRED, bracket=B, posiciones=synth_posiciones(X))
    res = {"grupos": [{"pred": g["pred"]} for g in X["grupos"]]}
    res.update({k: v for k, v in ko.items() if k != "_warnings"})
    for k in ("bota_oro", "bota_plata", "bota_bronce", "balon_oro", "balon_plata", "balon_bronce"):
        res[k] = X[k]
    return res, ko


def main():
    assert not B["warnings"], f"bracket con avisos: {B['warnings']}"
    fails = []

    # 1) Cada participante contra su propio cuadro = máximo teórico, con y sin flip.
    for name, X in sorted(PRED.items()):
        target = puntuar(X, res_ideal(X), eliminatorias_por="slot")["total"]
        for flip in (False, True):
            res, ko = build_full(X, flip)
            got = puntuar(X, res, eliminatorias_por="slot")["total"]
            cru_ok = all(ko[f"cruces_{r}"][i]["pred"] == X[f"cruces_{r}"][i]["pred"]
                         for r in ("dieciseisavos", "octavos", "cuartos", "semis")
                         for i in range(len(X[f"cruces_{r}"])))
            if got != target or not cru_ok:
                fails.append(f"{name} flip={flip}: got={got} target={target} cruces_ok={cru_ok}")

    # 2) build_ko(realidad=A) equivale a usar las predicciones de A como resultados:
    #    puntuar a CUALQUIER B debe coincidir con ambos.
    names = sorted(PRED)
    for A in names[:4]:
        res, _ = build_full(PRED[A])
        ideal = res_ideal(PRED[A])
        for Bn in names:
            v1 = puntuar(PRED[Bn], res, eliminatorias_por="slot")["total"]
            v2 = puntuar(PRED[Bn], ideal, eliminatorias_por="slot")["total"]
            if v1 != v2:
                fails.append(f"equivalencia realidad={A} scoring={Bn}: build_ko={v1} ideal={v2}")

    # 3) Parcial: grupos incompletos => sin posiciones ni KO, sin reventar.
    ps_parcial = [p for p in synth_partidos(PRED[names[0]]) if p["fase"] == "Grupos"][:30]
    ko_p = build_ko(ps_parcial, {}, PRED, bracket=B, posiciones=[])
    if ko_p["posiciones_grupos"] or any(c["pred"] for c in ko_p["cruces_dieciseisavos"]):
        fails.append("parcial: no debería haber posiciones ni cruces con 30 partidos de grupos")

    if fails:
        print("FALLOS:")
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print(f"OK — {len(PRED)} participantes x2 (normal+flip) = máximo; equivalencia y parcial correctos.")


if __name__ == "__main__":
    main()
