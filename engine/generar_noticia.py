"""Genera la crónica de una ronda de ELIMINATORIA con el CLI de Claude y la añade
a web/noticias.json. Pensado para llamarse desde cron cuando una ronda termina.

Uso:  python3 engine/generar_noticia.py dieciseisavos|octavos|cuartos|semifinales
"""
from __future__ import annotations
import json
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from noticias_stats import cargar, stats_ko  # noqa: E402
from generar_meme import generar_meme  # noqa: E402

TOKEN = re.compile(r"\[\[IMG:\s*(.*?)\]\]", re.S)

ROOT = Path(__file__).resolve().parent.parent
NOTI = ROOT / "web" / "noticias.json"
MAD = timezone(timedelta(hours=2))
FASES = {"dieciseisavos": "Dieciseisavos", "octavos": "Octavos",
         "cuartos": "Cuartos", "semifinales": "Semifinales"}
# Orden de portada (mayor = más reciente arriba); las de grupos las siembro a mano.
ORDEN = {"j1": 1, "j2": 2, "j3": 3, "grupos": 4, "dieciseisavos": 5,
         "octavos": 6, "cuartos": 7, "semifinales": 8, "final": 9}

ESTILO = '''Eres el cronista estrella de "El Salseo", el diario más gamberro de una porra de fútbol de oficina (13 compañeros que se la juegan por orgullo). Escribe la crónica de una ronda de eliminatorias del Mundial 2026 para la porra.

IDIOMA Y TONO: español de España, coloquial y con mala leche cariñosa. Vacila con gracia a los que han fallado, ensalza a los cracks (con criterio, no a todos), dramatiza las sorpresas y las eliminaciones, y cébate —con cariño— con quien tenga ya un campeón eliminado. Usa expresiones de aquí cuando peguen de forma natural (hacer el primo, pinchar, palmar, a llorar a la grada, de chiripa, ni de coña, menudo batacazo, vaya tela, irse de vacío, comerse los mocos). PROHIBIDO: anglicismos forzados (roast, hype, GOAT, epic, clutch...), tono de influencer o de TikTok, hashtags, y frases hechas que den cringe o suenen a IA. Nada de "agárrate", "prepárate para", "sin más dilación". Que suene a colega con gracia escribiendo en el grupo, no a community manager.

CONTENIDO: mezcla DOS cosas. (1) LA PORRA: quién acertó/falló los cruces, la clasificación general, campeones eliminados, francotiradores, colistas. (2) EL FÚTBOL REAL de los partidos (te paso los HECHOS REALES): héroes y paquetes — hat-tricks, dobletes, paradones, penaltis fallados o parados, tarjetas rojas, goles en propia, porteros-coladero.

MOTES: para los jugadores que destaquen, BUSCA EN INTERNET (usa la herramienta de búsqueda web) su apodo o mote popular entre la afición, y aplícalo SEGÚN SU ACTUACIÓN REAL en este partido: si fue el héroe (marcó, paró, decidió), ensálzalo con guasa cariñosa aunque uses su mote; si jugó como el ojete (falló el penalti, vio roja, hizo el ridículo), ahí sí cébate. El mote TIENE que encajar con lo que hizo: no llames llorón ni paquete a quien acaba de bordarlo, porque no tiene gracia. Si no encuentras mote, inventa un juego de palabras con su nombre al estilo (Penaldo, Pessi, Malicius).

MUY IMPORTANTE: los goles, resultados y jugadores son SOLO los que aparecen en los HECHOS REALES; no te inventes ninguno (los motes/apodos sí los puedes buscar en internet).

FORMATO: markdown. La PRIMERA línea es "# " + un titular gancho y gamberro. Después, secciones con "### Subtítulo" y uno o dos párrafos cada una. Usa **negritas** para nombres de participantes, equipos y datos. La longitud va según el número de partidos de la ronda (te lo digo abajo): cuando haya muchos partidos, la crónica puede y debe ser LARGA cubriéndolos todos; cuando haya pocos, más breve. Cubre todo lo reseñable pero sin paja. Como mucho UN emoji en toda la crónica, o ninguno.

IMÁGENES: puedes insertar marcadores de imagen, cada uno en su PROPIA línea (entre secciones, donde más gracia tenga), con este formato EXACTO: [[IMG: descripción visual en INGLÉS de una escena cartoon divertida que ilustre ese momento, sin texto en la imagen | pie de foto corto y gamberro en español]]. Cuántas puedes poner te lo digo abajo según la ronda; ponlas donde de verdad haya algo MUY reseñable (un bombazo, un campeón eliminado, un partidazo de un jugador, un cabezazo de la clasificación), no por rellenar. En la descripción en inglés NUNCA nombres a personas reales (futbolistas/entrenadores): represéntalos por su selección/camiseta o rasgos (el generador de imágenes bloquea nombres reales).

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
    # Hechos reales del fútbol (héroes/paquetes). Los motes los busca el cronista en internet.
    try:
        from futbol_stats import hechos_ronda
        hechos = hechos_ronda(d, fase)
    except Exception as e:
        print("aviso: sin hechos de fútbol (", e, ")")
        hechos = []
    n_part = len(st.get("resultados") or []) or len(hechos) or 1
    largo = ("MUY larga, no te cortes" if n_part >= 12 else
             "larga" if n_part >= 6 else
             "media" if n_part >= 3 else "más bien corta y al grano")
    ronda_info = (f"\n\nESTA RONDA: {n_part} partidos. Longitud de la crónica: {largo} "
                  f"(cubre todos los partidos con algo reseñable, de la porra o del fútbol). "
                  f"Puedes poner HASTA {n_part} imágenes inline [[IMG]], idealmente una por partido o "
                  f"momento MUY reseñable; solo donde aporte de verdad, no por rellenar.")
    prompt = (ESTILO + ronda_info + "\n\nRONDA: " + fase
              + "\nDATOS PORRA (JSON):\n" + json.dumps(st, ensure_ascii=False, indent=1)
              + "\nHECHOS REALES DE LOS PARTIDOS (JSON):\n" + json.dumps(hechos, ensure_ascii=False, indent=1))
    # --allowedTools WebSearch: para que busque los motes/apodos del momento de cada jugador.
    r = subprocess.run(["claude", "--allowedTools", "WebSearch", "-p", prompt],
                       capture_output=True, text=True, timeout=600)
    txt = (r.stdout or "").strip().strip("`").strip()
    if not txt:
        raise SystemExit("claude no devolvió nada. stderr: " + (r.stderr or "")[:300])
    lines = txt.split("\n")
    if lines[0].lstrip().startswith("#"):
        titulo = lines[0].lstrip("#").strip()
        cuerpo = "\n".join(lines[1:]).strip()
    else:
        titulo, cuerpo = fase, txt

    # Imágenes incrustadas: cada [[IMG: escena en inglés | pie]] -> meme propio + markdown ![pie](...)
    # Tope = un meme por partido de la ronda (en dieciseisavos pueden ser muchos).
    tokens = TOKEN.findall(cuerpo)[:max(n_part, 2)]
    for n, tok in enumerate(tokens, start=2):
        concepto, _, pie = tok.partition("|")
        concepto, pie = concepto.strip(), pie.strip()
        sub = f"{fase_id}-{n}"
        ok = generar_meme(sub, concepto=concepto)
        repl = f"![{pie}](assets/noti-{sub}.png)" if ok else ""
        cuerpo = cuerpo.replace(f"[[IMG: {tok}]]", repl, 1).replace(f"[[IMG:{tok}]]", repl, 1)
    cuerpo = TOKEN.sub("", cuerpo).strip()  # limpia marcadores sobrantes

    # Meme principal (cabecera): montaje que refleja TODOS los momentos de la crónica
    from generar_meme import concepto_composite
    generar_meme(fase_id, concepto=concepto_composite(titulo, cuerpo))

    doc = json.loads(NOTI.read_text(encoding="utf-8")) if NOTI.exists() else {"articulos": []}
    doc["articulos"] = [a for a in doc["articulos"] if a.get("id") != fase_id]
    doc["articulos"].append({"id": fase_id, "fase": fase, "fecha": fecha_fin(d, fase),
                             "orden": ORDEN.get(fase_id, 5), "titulo": titulo, "cuerpo": cuerpo})
    NOTI.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("OK noticia", fase_id, "->", titulo)


if __name__ == "__main__":
    generar(sys.argv[1] if len(sys.argv) > 1 else "dieciseisavos")
