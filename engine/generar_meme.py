"""Genera una imagen tipo meme para una crónica usando el CLI de codex (que llama
a la API de imágenes de OpenAI, gpt-image-1) y la guarda en web/assets/noti-<id>.png.

- El "concepto" visual (en inglés) lo saca Claude a partir del titular/crónica.
- codex hace la imagen REAL (no SVG) y la guarda en la ruta indicada.
- Si algo falla, devuelve False sin romper nada (la web cae al diseño sin imagen).

Uso:  python3 engine/generar_meme.py <id> ["concepto visual en inglés opcional"]
"""
from __future__ import annotations
import glob
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "web" / "assets"


def _codex_bin():
    """Localiza el binario de codex (en cron el PATH no trae el bin de nvm)."""
    c = shutil.which("codex")
    if c:
        return c
    cands = sorted(glob.glob("/root/.nvm/versions/node/*/bin/codex"))
    return cands[-1] if cands else "codex"

# Estilo fijo: TODO es cabra (el universo de "El Salseo" y la 404). Si la escena pide
# otra cosa (un bicho, un objeto, un personaje), se hace la VERSIÓN CABRA de eso.
ESTILO_IMG = ("Everything is in the goat universe of 'El Salseo': characters are friendly cartoon "
              "goats with little horns and beards, wearing football kits where relevant. If the "
              "scene calls for an animal, creature or character (e.g. a mosquito, a robot, a king), "
              "draw a funny GOAT version of it, always keeping little goat horns and a beard. "
              "Modern flat cartoon caricature illustration, clean bold shapes, soft cel shading, "
              "expressive funny faces, humorous sports-meme vibe, warm cream background #f7f6f1, "
              "no text, no letters, no logos, no watermarks. "
              "Go for a FUNNY SITUATIONAL GAG (a comic action that roasts the loser or celebrates "
              "the winner) rather than goats merely posing in their kits. Make it RICH and DETAILED, "
              "like a busy comic poster: layered scene, expressive characters and fun background "
              "gags and props.")


def _claude(prompt, timeout=180, fallback=""):
    try:
        r = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "").strip().strip('"').replace("\n", " ") or fallback
    except Exception:
        return fallback


# Regla obligatoria: el generador de imágenes bloquea nombres de personas reales
# (futbolistas, entrenadores). Hay que representarlos por selección/camiseta y rasgos.
_NO_REALES = ("NUNCA nombres a personas reales (futbolistas, entrenadores, famosos): el generador "
              "de imágenes los bloquea. Represéntalos por su selección/camiseta, dorsal o rasgos "
              "genéricos (p.ej. 'una cabra con la camiseta de Argentina y barbita'), nunca por su "
              "nombre. Sí puedes usar los nombres de los participantes de la porra (son anónimos).")


def concepto_desde_cronica(titulo, primer_parrafo=""):
    """Concepto visual (inglés) para un meme puntual a partir de titular + entradilla."""
    return _claude(
        "Eres director de arte de un medio de humor futbolero gamberro (universo de cabras). A "
        "partir de este titular y entradilla de una crónica de una porra, dame UNA sola descripción "
        "visual en INGLÉS (2-3 frases) de un GAG visual con SITUACIÓN: una acción cómica concreta "
        "que se cebe con el que la cagó o celebre a lo bestia al héroe. El chiste sale del FÚTBOL "
        "(la cagada, el choke, el penalti fallado, la celebración, la fama del jugador), NUNCA de "
        "la raza/religión/nacionalidad de nadie. Nada de retratos posando; quiero situación. Solo "
        "la escena, sin texto en la imagen, sin estilo (eso lo pongo yo). " + _NO_REALES +
        " Devuelve solo la descripción, sin comillas.\n\n"
        f"TITULAR: {titulo}\nENTRADILLA: {primer_parrafo}", fallback=titulo)


def concepto_composite(titulo, cuerpo):
    """Concepto visual (inglés) para la imagen PRINCIPAL: un póster cómico RICO y detallado."""
    return _claude(
        "Eres director de arte de un medio de humor futbolero gamberro (universo de cabras). A partir "
        "de esta crónica de una porra, descríbeme en INGLÉS la escena de UN PÓSTER CÓMICO rico y muy "
        "detallado que combine los momentos clave del partido/ronda como GAGS visuales con situación. "
        "INSTRUCCIONES:\n"
        "- Convierte las coñas de la crónica en METÁFORAS VISUALES potentes (p.ej. un equipo soso = "
        "máquina oxidada que se desmonta; un killer frío = robot Terminator; un eliminado = Cenicienta "
        "huyendo a medianoche; un portero figura = muro de ladrillos o superhéroe; un penalti fallado "
        "= balón disparado a la luna).\n"
        "- Composición POR CAPAS: una acción principal en el centro, gags secundarios a los lados y "
        "DETALLES DE FONDO divertidos (aficionados, props, pequeñas escenas).\n"
        "- Que se cebe con el que la cagó y celebre al héroe. El chiste sale del FÚTBOL, nunca de "
        "raza/religión/nacionalidad.\n"
        "- Sin texto/letras en la imagen. No describas el estilo (lo pongo yo).\n"
        "- Refleja los hechos REALES (no inventes resultados, equipos ni jugadores). " + _NO_REALES + "\n"
        "Devuelve SOLO la descripción de la escena, 5-8 frases bien cargadas de detalle.\n\n"
        f"TITULAR: {titulo}\nCRÓNICA:\n{cuerpo[:1800]}", fallback=titulo)


def optimizar(path, ancho=1024):
    """Redimensiona y comprime el PNG (la columna web mide ~600px; no hace falta 1536)."""
    try:
        from PIL import Image
        im = Image.open(path).convert("RGB")
        if im.width > ancho:
            im = im.resize((ancho, round(im.height * ancho / im.width)), Image.LANCZOS)
        # cartoon plano -> paleta de 256 colores: calidad casi idéntica y peso mínimo
        im.convert("P", palette=Image.ADAPTIVE, colors=256).save(path, optimize=True)
        return True
    except Exception as e:
        print("no se pudo optimizar", path, e)
        return False


def _codex_prompt(out_path, concepto):
    # Codex (modo ChatGPT) genera la imagen con SU generador nativo si se le pide a pelo;
    # NO mencionar API/clave (el login OAuth no tiene permiso para la API de imágenes).
    return (
        "Genera una IMAGEN tipo meme con tu generador de imágenes y guárdala como PNG REAL "
        f"(rasterizado, generado por modelo de imágenes) en {out_path} (sobreescribe si existe). "
        "NADA de SVG ni de dibujar con código/PIL/canvas: tiene que ser una imagen generada por IA "
        "de verdad. Formato apaisado, ~1536x1024.\n\n"
        f"Imagen (en inglés): '{concepto} {ESTILO_IMG}'"
    )


def generar_meme(fase_id, concepto=None, titulo="", primer_parrafo="", timeout=300):
    ASSETS.mkdir(parents=True, exist_ok=True)
    out = ASSETS / f"noti-{fase_id}.png"
    if not concepto:
        concepto = concepto_desde_cronica(titulo or fase_id, primer_parrafo)
    try:
        subprocess.run([_codex_bin(), "exec", "--dangerously-bypass-approvals-and-sandbox",
                        _codex_prompt(str(out), concepto)],
                       capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        print("codex falló:", e)
        return False
    ok = out.exists() and out.stat().st_size > 20000
    if ok:
        optimizar(out)
    print(("OK meme " if ok else "NO se generó meme ") + str(out),
          f"({out.stat().st_size} bytes)" if out.exists() else "(no existe)")
    return ok


if __name__ == "__main__":
    fid = sys.argv[1] if len(sys.argv) > 1 else "grupos"
    con = sys.argv[2] if len(sys.argv) > 2 else None
    generar_meme(fid, concepto=con)
