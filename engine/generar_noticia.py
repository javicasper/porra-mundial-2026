"""Crónicas de eliminatoria de "El Salseo" con el CLI de Claude (+ búsqueda web para
los motes) y memes con codex. Tres modos:

  python3 engine/generar_noticia.py auto          # orquesta todo (para el cron)
  python3 engine/generar_noticia.py dieciseisavos # crónica GENERAL de una ronda
  python3 engine/generar_noticia.py partido dieciseisavos BRA JPN  # un solo partido

'auto' genera la mini-crónica de cada partido jugado que aún no tenga, y cuando la
ronda está completa lanza la crónica general.
"""
from __future__ import annotations
import json
import random
import re
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from noticias_stats import cargar, stats_ko, stats_partido  # noqa: E402
from generar_meme import generar_meme, concepto_composite  # noqa: E402

TOKEN = re.compile(r"\[\[IMG:\s*(.*?)\]\]", re.S)
ROOT = Path(__file__).resolve().parent.parent
NOTI = ROOT / "web" / "noticias.json"
MAD = timezone(timedelta(hours=2))
FASES = {"dieciseisavos": "Dieciseisavos", "octavos": "Octavos",
         "cuartos": "Cuartos", "semifinales": "Semifinales"}
# Orden de portada (mayor = más arriba). Grupos/jornadas: 1-4. Cada ronda KO reserva
# un bloque: los partidos = base+nº de partido (por hora); la general = base+99.
KO_BASE = {"dieciseisavos": 500, "octavos": 600, "cuartos": 700, "semifinales": 800}

# Firmas: periodistas/tertulianos deportivos españoles retocados (parodia, no son los reales).
FIRMAS = ["Tomás Ronquero", "Josep Pedrebol", "Manolo Llama", "Edu Aguirné",
          "Cristóbal Suria", "Juanma Rodrigálvez", "Maldoni", "Paco Gonzálvez",
          "Manu Carraño", "Quim Doménec", "Mónica Marchanti", "Ciro Pérez",
          "Lobo Carrasca", "Pipi Estrado", "Iturralde Gonzálvez", "Roberto Palomir"]


def _firma():
    return random.choice(FIRMAS)

_TONO = '''IDIOMA Y TONO: español de España, coloquial y con mala leche cariñosa. Vacila con gracia a los que han fallado, ensalza a los cracks (con criterio), dramatiza las sorpresas y las eliminaciones, y cébate —con cariño— con quien tenga ya un campeón eliminado. Usa expresiones de aquí cuando peguen de forma natural (hacer el primo, pinchar, palmar, a llorar a la grada, de chiripa, ni de coña, menudo batacazo, vaya tela, irse de vacío, comerse los mocos). PROHIBIDO: anglicismos forzados (roast, hype, GOAT, epic, clutch...), tono de influencer o de TikTok, hashtags, y frases hechas que den cringe o suenen a IA. Nada de "agárrate", "prepárate para", "sin más dilación". Que suene a colega con gracia escribiendo en el grupo.'''

_MOTES = '''MOTES: para los jugadores que destaquen, BUSCA EN INTERNET (usa la herramienta de búsqueda web) su apodo o mote popular entre la afición, y aplícalo SEGÚN SU ACTUACIÓN REAL: si fue el héroe (marcó, paró, decidió), ensálzalo con guasa cariñosa aunque uses su mote; si jugó como el ojete (falló el penalti, vio roja, hizo el ridículo), ahí sí cébate. El mote TIENE que encajar con lo que hizo: no llames llorón ni paquete a quien acaba de bordarlo, que no tiene gracia. Si no encuentras mote, inventa un juego de palabras con su nombre al estilo (Penaldo, Pessi, Malicius).'''

_REGLA = '''MUY IMPORTANTE: los goles, resultados y jugadores son SOLO los que aparecen en los HECHOS REALES; no te inventes ninguno (los motes/apodos sí los puedes buscar en internet). Devuelve SOLO el markdown del artículo, sin comentarios, sin explicaciones y sin ```.'''

ESTILO = f'''Eres el cronista estrella de "El Salseo", el diario más gamberro de una porra de fútbol de oficina (13 compañeros que se la juegan por orgullo). Escribe la crónica de una RONDA de eliminatorias del Mundial 2026 para la porra.

{_TONO}

CONTENIDO: mezcla DOS cosas. (1) LA PORRA: quién acertó/falló los cruces, la clasificación general, campeones eliminados, francotiradores, colistas. (2) EL FÚTBOL REAL de los partidos (te paso los HECHOS REALES): héroes y paquetes — hat-tricks, dobletes, paradones, penaltis fallados o parados, tarjetas rojas, goles en propia, porteros-coladero.

{_MOTES}

FORMATO: markdown. La PRIMERA línea es "# " + un titular gancho y gamberro. Después, secciones con "### Subtítulo" y uno o dos párrafos cada una. Usa **negritas** para nombres y datos. La longitud va según el número de partidos (te lo digo abajo): con muchos partidos, larga cubriéndolos todos; con pocos, más breve. Cubre lo reseñable sin paja. Como mucho UN emoji, o ninguno.

IMÁGENES: puedes insertar marcadores de imagen, cada uno en su PROPIA línea, con este formato EXACTO: [[IMG: descripción visual en INGLÉS de una escena cartoon divertida, sin texto en la imagen | pie corto y gamberro en español]]. Cuántas, te lo digo abajo según la ronda; solo donde haya algo MUY reseñable, no por rellenar. En la descripción en inglés NUNCA nombres a personas reales: represéntalos por su selección/camiseta o rasgos.

{_REGLA}'''

ESTILO_PARTIDO = f'''Eres el cronista estrella de "El Salseo", el diario más gamberro de una porra de fútbol de oficina. Escribe una MINI-CRÓNICA de UN SOLO partido de eliminatoria del Mundial 2026 (no de toda la ronda).

{_TONO}

CONTENIDO: (1) EL PARTIDO REAL (te paso los HECHOS, la CRONOLOGÍA con los minutos y las ALINEACIONES/titulares): cuenta cómo fue (quién empezó mandando, remontadas, el gol que lo decidió, el alargue), los héroes y los paquetes — goles, hat-tricks, asistencias, penaltis fallados/parados, tarjetas rojas, paradones, porteros-coladero, y cita a quien entró o salió del banquillo si tuvo su miga. (2) EL ÁNGULO PORRA de ESTE cruce (te paso los datos): quién predijo este cruce, quién clavó el marcador, a quién le eliminan un campeón.

{_MOTES}

FORMATO: markdown. La PRIMERA línea es "# " + titular gamberro con la clave del partido. Después, 2-3 párrafos cortos (sin subtítulos, o como mucho uno). Entre 110 y 200 palabras: al grano, que es un solo partido. **Negritas** para nombres y datos. Un emoji como mucho. NO pongas marcadores de imagen [[IMG]] (la imagen la pongo yo aparte).

{_REGLA}'''


def _fecha(utc):
    return datetime.fromisoformat(utc.replace("Z", "+00:00")).astimezone(MAD).strftime("%Y-%m-%d")


def _fecha_fin(d, fase):
    us = [p["utc"] for p in d["partidos"] if p.get("fase") == fase and p.get("jugado") and p.get("utc")]
    return _fecha(max(us)) if us else ""


def _slug(fase_id, p):
    return f"{fase_id}-{p['tlaLocal']}-{p['tlaVisitante']}".lower()


def _seq(d, fase, p):
    us = sorted(x["utc"] for x in d["partidos"] if x.get("fase") == fase and x.get("utc"))
    return (us.index(p["utc"]) + 1) if p["utc"] in us else 1


def _ids():
    try:
        return {a["id"] for a in json.loads(NOTI.read_text(encoding="utf-8")).get("articulos", [])}
    except Exception:
        return set()


def _upsert(article):
    doc = json.loads(NOTI.read_text(encoding="utf-8")) if NOTI.exists() else {"articulos": []}
    doc["articulos"] = [a for a in doc["articulos"] if a.get("id") != article["id"]]
    doc["articulos"].append(article)
    NOTI.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def _claude(prompt, timeout=600):
    r = subprocess.run(["claude", "--allowedTools", "WebSearch", "-p", prompt],
                       capture_output=True, text=True, timeout=timeout)
    txt = (r.stdout or "").strip().strip("`").strip()
    if not txt:
        raise SystemExit("claude no devolvió nada. stderr: " + (r.stderr or "")[:300])
    lines = txt.split("\n")
    if lines[0].lstrip().startswith("#"):
        return lines[0].lstrip("#").strip(), "\n".join(lines[1:]).strip()
    return None, txt


def _hechos_partido(p):
    try:
        from futbol_stats import hechos_partido, evento_id
        eid = evento_id(p["tlaLocal"], p["tlaVisitante"], p["utc"])
        return hechos_partido(eid) if eid else {}
    except Exception as e:
        print("aviso: sin hechos de fútbol (", e, ")")
        return {}


def generar_partido(fase_id, p):
    """Mini-crónica de un solo partido + su meme."""
    fase = FASES[fase_id]
    d = cargar()
    st = stats_partido(d, fase, p["local"], p["visitante"])
    if not st:
        print("partido sin datos:", p["local"], p["visitante"])
        return False
    prompt = (ESTILO_PARTIDO + f"\n\nPARTIDO: {p['local']} {st['marcador']} {p['visitante']}"
              + "\nDATOS PORRA DEL CRUCE (JSON):\n" + json.dumps(st, ensure_ascii=False)
              + "\nHECHOS REALES DEL PARTIDO (JSON):\n" + json.dumps(_hechos_partido(p), ensure_ascii=False))
    titulo, cuerpo = _claude(prompt, timeout=400)
    titulo = titulo or f"{p['local']} {st['marcador']} {p['visitante']}"
    cuerpo = TOKEN.sub("", cuerpo).strip()
    sub_id = _slug(fase_id, p)
    generar_meme(sub_id, concepto=concepto_composite(titulo, cuerpo))
    _upsert({"id": sub_id, "fase": fase, "fecha": _fecha(p["utc"]),
             "orden": KO_BASE.get(fase_id, 500) + _seq(d, fase, p),
             "firma": _firma(), "titulo": titulo, "cuerpo": cuerpo})
    print("OK partido", sub_id, "->", titulo)
    return True


def generar(fase_id):
    """Crónica GENERAL de una ronda (cuando ya ha terminado)."""
    if fase_id not in FASES:
        raise SystemExit("fase no soportada: " + fase_id)
    fase = FASES[fase_id]
    d = cargar()
    st = stats_ko(d, fase)
    if not st["resultados"]:
        raise SystemExit("ronda '%s' aún sin partidos jugados" % fase)
    try:
        from futbol_stats import hechos_ronda
        hechos = hechos_ronda(d, fase)
    except Exception as e:
        print("aviso: sin hechos de fútbol (", e, ")")
        hechos = []
    n_part = len(st.get("resultados") or []) or len(hechos) or 1
    largo = ("MUY larga, no te cortes" if n_part >= 12 else "larga" if n_part >= 6
             else "media" if n_part >= 3 else "más bien corta y al grano")
    ronda_info = (f"\n\nESTA RONDA: {n_part} partidos. Longitud: {largo} (cubre todos los partidos con "
                  f"algo reseñable). Puedes poner HASTA {n_part} imágenes inline [[IMG]], solo donde "
                  f"aporte de verdad, no por rellenar.")
    prompt = (ESTILO + ronda_info + "\n\nRONDA: " + fase
              + "\nDATOS PORRA (JSON):\n" + json.dumps(st, ensure_ascii=False, indent=1)
              + "\nHECHOS REALES DE LOS PARTIDOS (JSON):\n" + json.dumps(hechos, ensure_ascii=False, indent=1))
    titulo, cuerpo = _claude(prompt, timeout=600)
    titulo = titulo or fase

    # Imágenes incrustadas: [[IMG: escena | pie]] -> meme propio + ![pie](...)
    for n, tok in enumerate(TOKEN.findall(cuerpo)[:max(n_part, 2)], start=2):
        concepto, _, pie = tok.partition("|")
        sub = f"{fase_id}-{n}"
        ok = generar_meme(sub, concepto=concepto.strip())
        repl = f"![{pie.strip()}](assets/noti-{sub}.png)" if ok else ""
        cuerpo = cuerpo.replace(f"[[IMG: {tok}]]", repl, 1).replace(f"[[IMG:{tok}]]", repl, 1)
    cuerpo = TOKEN.sub("", cuerpo).strip()

    generar_meme(fase_id, concepto=concepto_composite(titulo, cuerpo))
    _upsert({"id": fase_id, "fase": fase + " · resumen", "fecha": _fecha_fin(d, fase),
             "orden": KO_BASE.get(fase_id, 500) + 99, "firma": _firma(),
             "titulo": titulo, "cuerpo": cuerpo})
    print("OK resumen", fase_id, "->", titulo)


def auto():
    """Para el cron: mini-crónica de cada partido jugado que falte; al cerrar la ronda, la general."""
    d = cargar()
    for fase_id, fase in FASES.items():
        ps = [p for p in d["partidos"] if p.get("fase") == fase]
        jug = [p for p in ps if p.get("jugado") and p.get("golesLocal") is not None]
        for p in sorted(jug, key=lambda x: x["utc"]):
            if _slug(fase_id, p) not in _ids():
                generar_partido(fase_id, p)
        if ps and len(jug) >= len(ps) and fase_id not in _ids():
            generar(fase_id)


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "auto"
    if a == "auto":
        auto()
    elif a == "partido" and len(sys.argv) >= 5:
        fid, tl, tv = sys.argv[2], sys.argv[3].upper(), sys.argv[4].upper()
        d = cargar()
        p = next((x for x in d["partidos"] if x.get("fase") == FASES.get(fid)
                  and x.get("tlaLocal") == tl and x.get("tlaVisitante") == tv), None)
        if not p:
            raise SystemExit("partido no encontrado")
        generar_partido(fid, p)
    elif a in FASES:
        generar(a)
    else:
        raise SystemExit("uso: auto | <ronda> | partido <ronda> <TLA_local> <TLA_visit>")
