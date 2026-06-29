"""Genera una imagen tipo meme para una crónica usando el CLI de codex (que llama
a la API de imágenes de OpenAI, gpt-image-1) y la guarda en web/assets/noti-<id>.png.

- El "concepto" visual (en inglés) lo saca Claude a partir del titular/crónica.
- codex hace la imagen REAL (no SVG) y la guarda en la ruta indicada.
- Si algo falla, devuelve False sin romper nada (la web cae al diseño sin imagen).

Uso:  python3 engine/generar_meme.py <id> ["concepto visual en inglés opcional"]
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "web" / "assets"

# Estilo fijo para que todos los memes peguen entre sí y con la cabra del 404.
ESTILO_IMG = ("Modern flat cartoon caricature illustration, clean bold shapes, soft cel shading, "
              "expressive funny faces, humorous sports-meme vibe, warm cream background #f7f6f1, "
              "no text, no letters, no logos, no watermarks.")


def concepto_desde_cronica(titulo, primer_parrafo=""):
    """Pide a Claude una descripción visual en inglés para el meme."""
    prompt = (
        "Eres director de arte de un medio de humor futbolero. A partir de este titular y "
        "entradilla de una crónica de una porra del Mundial, dame UNA sola descripción visual "
        "en INGLÉS (2-3 frases) para una ilustración tipo meme, divertida y cartoon, que la "
        "ilustre. Describe SOLO la escena (personajes, acción, gesto cómico); nada de texto en "
        "la imagen, nada de estilo (eso lo pongo yo). Devuelve solo la descripción, sin comillas.\n\n"
        f"TITULAR: {titulo}\nENTRADILLA: {primer_parrafo}"
    )
    try:
        r = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=180)
        c = (r.stdout or "").strip().strip('"').replace("\n", " ")
        return c or titulo
    except Exception:
        return titulo


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
    return (
        f"Tienes red. Llama a la API de imágenes de OpenAI (gpt-image-1) y guarda el PNG en "
        f"{out_path} (sobreescribe). API key en /root/.codex/auth.json campo OPENAI_API_KEY "
        "(Authorization: Bearer). Params: model=gpt-image-1, size=1536x1024, quality=high, n=1. "
        "La respuesta trae data[0].b64_json -> decodifícalo y escríbelo como PNG en esa ruta. "
        "NO dibujes formas con SVG/PIL; si la API falla, muéstrame el error tal cual.\n\n"
        f"Prompt de la imagen (en inglés): '{concepto} {ESTILO_IMG}'"
    )


def generar_meme(fase_id, concepto=None, titulo="", primer_parrafo="", timeout=300):
    ASSETS.mkdir(parents=True, exist_ok=True)
    out = ASSETS / f"noti-{fase_id}.png"
    if not concepto:
        concepto = concepto_desde_cronica(titulo or fase_id, primer_parrafo)
    try:
        subprocess.run(["codex", "exec", "--dangerously-bypass-approvals-and-sandbox",
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
