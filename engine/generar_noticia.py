"""Genera la crónica de una ronda de ELIMINATORIA con el CLI de Claude y la añade
a web/noticias.json. Pensado para llamarse desde cron cuando una ronda termina.

Uso:  python3 engine/generar_noticia.py dieciseisavos|octavos|cuartos|semifinales
"""
from __future__ import annotations
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from noticias_stats import cargar, stats_ko  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NOTI = ROOT / "web" / "noticias.json"
MAD = timezone(timedelta(hours=2))
FASES = {"dieciseisavos": "Dieciseisavos", "octavos": "Octavos",
         "cuartos": "Cuartos", "semifinales": "Semifinales"}

ESTILO = '''Eres el cronista estrella de "El Salseo", el diario más gamberro de una porra de fútbol de oficina (13 compañeros que se la juegan por orgullo). Escribe la crónica de una ronda de eliminatorias del Mundial 2026 para la porra.

IDIOMA Y TONO: español de España, coloquial y con mala leche cariñosa. Vacila con gracia a los que han fallado, ensalza a los cracks (con criterio, no a todos), dramatiza las sorpresas y las eliminaciones, y cébate —con cariño— con quien tenga ya un campeón eliminado. Usa expresiones de aquí cuando peguen de forma natural (hacer el primo, pinchar, palmar, a llorar a la grada, de chiripa, ni de coña, menudo batacazo, vaya tela, irse de vacío, comerse los mocos). PROHIBIDO: anglicismos forzados (roast, hype, GOAT, epic, clutch...), tono de influencer o de TikTok, hashtags, y frases hechas que den cringe o suenen a IA. Nada de "agárrate", "prepárate para", "sin más dilación". Que suene a colega con gracia escribiendo en el grupo, no a community manager.

FORMATO: markdown. La PRIMERA línea es "# " + un titular gancho y gamberro. Después, 4-6 secciones, cada una con "### Subtítulo" y uno o dos párrafos. Usa **negritas** para nombres de participantes, equipos y datos. Entre 300 y 450 palabras. Que tenga chicha y variedad, no listas escuetas. Como mucho UN emoji en toda la crónica, o ninguno.

REGLA DE ORO: NO inventes NADA. Usa SOLO los datos del JSON que te paso (participantes, resultados, marcadores, puntos, eliminados, campeones eliminados). Si algo no está en los datos, no lo menciones. Devuelve SOLO el markdown del artículo, sin comentarios, sin explicaciones y sin ```.'''


def fecha_fin(d, fase):
    us = [p["utc"] for p in d["partidos"] if p.get("fase") == fase and p.get("jugado") and p.get("utc")]
    return datetime.fromisoformat(max(us).replace("Z", "+00:00")).astimezone(MAD).strftime("%Y-%m-%d") if us else ""


def generar(fase_id):
    if fase_id not in FASES:
        raise SystemExit("fase no soportada: " + fase_id)
    fase = FASES[fase_id]
    d = cargar()
    st = stats_ko(d, fase)
    if not st["resultados"]:
        raise SystemExit("ronda '%s' aún sin partidos jugados" % fase)
    prompt = ESTILO + "\n\nRONDA: " + fase + "\nDATOS (JSON):\n" + json.dumps(st, ensure_ascii=False, indent=1)
    r = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=300)
    txt = (r.stdout or "").strip().strip("`").strip()
    if not txt:
        raise SystemExit("claude no devolvió nada. stderr: " + (r.stderr or "")[:300])
    lines = txt.split("\n")
    if lines[0].lstrip().startswith("#"):
        titulo = lines[0].lstrip("#").strip()
        cuerpo = "\n".join(lines[1:]).strip()
    else:
        titulo, cuerpo = fase, txt
    doc = json.loads(NOTI.read_text(encoding="utf-8")) if NOTI.exists() else {"articulos": []}
    doc["articulos"] = [a for a in doc["articulos"] if a.get("id") != fase_id]
    doc["articulos"].append({"id": fase_id, "fase": fase, "fecha": fecha_fin(d, fase),
                             "titulo": titulo, "cuerpo": cuerpo})
    NOTI.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OK noticia", fase_id, "->", titulo)


if __name__ == "__main__":
    generar(sys.argv[1] if len(sys.argv) > 1 else "dieciseisavos")
