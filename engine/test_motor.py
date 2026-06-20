"""Valida el motor de puntuacion sin resultados reales.

1) AUTO-TEST: puntuar a cada participante contra SUS PROPIAS predicciones.
   Debe dar el maximo teorico (855) e identico para todos.
2) TEST CRUZADO: usar las predicciones de un participante como 'resultados'
   y rankear a todos. El usado como verdad debe quedar 1.o con el maximo.

Usa data/predicciones.json si existe; si no, el ejemplo anonimizado del repo.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from scoring import puntuar, clasificacion

ROOT = Path(__file__).resolve().parent.parent
PRED_FILE = ROOT / "data" / "predicciones.json"
if not PRED_FILE.exists():
    PRED_FILE = ROOT / "data" / "predicciones.sample.json"
PRED = json.loads(PRED_FILE.read_text(encoding="utf-8"))

MAX_TEORICO = 855  # el resultado exacto acumula la diferencia (regla confirmada)
REF = sorted(PRED)[0]  # participante de referencia (sin nombres hardcodeados)

print("=" * 60)
print("1) AUTO-TEST  (cada uno contra sus propias predicciones)")
print("=" * 60)
all_ok = True
for nombre, pred in PRED.items():
    r = puntuar(pred, pred)
    ok = r["total"] == MAX_TEORICO
    all_ok &= ok
    print(f"  {nombre:<10} total={r['total']:>4}  {'OK' if ok else 'ESPERADO ' + str(MAX_TEORICO)}")
print(f"\n  -> {'TODOS dan el maximo teorico (' + str(MAX_TEORICO) + ')' if all_ok else 'HAY FALLOS'}")

print("\n  Desglose (" + REF + " vs " + REF + "):")
for cat, d in puntuar(PRED[REF], PRED[REF])["detalle"].items():
    print(f"    {cat:<22} {d['puntos']:>4}   {d.get('info', '')}")

print()
print("=" * 60)
print(f"2) TEST CRUZADO  (resultados = predicciones de '{REF}')")
print("=" * 60)
tabla = clasificacion(PRED, PRED[REF])
print(f"  {'#':>2} {'Participante':<12} {'Puntos':>7}")
print("  " + "-" * 26)
for i, (nombre, total, _) in enumerate(tabla, 1):
    marca = "  <- verdad" if nombre == REF else ""
    print(f"  {i:>2} {nombre:<12} {total:>7}{marca}")
