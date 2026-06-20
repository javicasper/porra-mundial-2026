"""Clasificacion EN VIVO de la porra con los resultados reales disponibles."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from scoring import clasificacion, puntuar

ROOT = Path(__file__).resolve().parent.parent
PRED = json.loads((ROOT / "data" / "predicciones.json").read_text(encoding="utf-8"))
RES = json.loads((ROOT / "data" / "resultados.json").read_text(encoding="utf-8"))

jugados = RES.get("_grupos_jugados", 0)
print(f"CLASIFICACIÓN EN VIVO — Porra Mundial 2026")
print(f"(resultados reales: {jugados}/72 partidos de grupos jugados)\n")

tabla = clasificacion(PRED, RES)
print(f"  {'#':>2}  {'Participante':<10} {'Pts':>4}   {'exact':>5} {'dif':>4} {'sig':>4}  (de {jugados} partidos)")
print("  " + "-" * 48)
for i, (nombre, total, r) in enumerate(tabla, 1):
    brk = r["detalle"]["grupos_partidos"].get("info", {})
    print(f"  {i:>2}  {nombre:<10} {total:>4}   {brk.get('exacto',0):>5} {brk.get('diferencia',0):>4} {brk.get('signo',0):>4}")

# Lider: aciertos exactos para verificar
print("\n  exact = marcador exacto (5 pts: dif+exacto) · dif = signo+diferencia (2) · sig = solo signo (1)")
