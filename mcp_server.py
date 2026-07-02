"""Servidor MCP (Model Context Protocol) de solo lectura de La Porra del Mundial 2026.

Transporte: Streamable HTTP (JSON-RPC 2.0 por POST), solo stdlib. Sirve clasificación,
resultados, cruces, noticias y predicciones para enchufar la porra a ChatGPT / Claude / etc.

La gente lo añade así:
  Claude Code:  claude mcp add --transport http porra https://porra.javicasper.com/mcp
  ChatGPT:      Conectores -> añadir servidor MCP -> https://porra.javicasper.com/mcp
"""
from __future__ import annotations
import json
import unicodedata
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "web" / "data.json"
NOTI = ROOT / "web" / "noticias.json"
PROTO = "2025-06-18"
SERVER_INFO = {"name": "porra-mundial-2026", "version": "1.0.0"}


def _norm(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()


def _data():
    return json.loads(DATA.read_text(encoding="utf-8"))


def _noti():
    try:
        return json.loads(NOTI.read_text(encoding="utf-8")).get("articulos", [])
    except Exception:
        return []


def _marcador(p):
    s = f"{p['golesLocal']}-{p['golesVisitante']}"
    if p.get("golesLocalFull") is not None:
        tag = "pen" if p.get("penaltisLocal") is not None else "pró"
        s += f" (90') · final {p['golesLocalFull']}-{p['golesVisitanteFull']} {tag}"
    return s


# ---------------------------------------------------------------- herramientas
def t_resumen(_):
    d = _data()
    r = d.get("ranking", [])
    lider = r[0] if r else None
    live = [p for p in d["partidos"] if p.get("envivo")]
    prox = sorted([p for p in d["partidos"] if not p.get("jugado") and not p.get("envivo") and p.get("utc")],
                  key=lambda p: p["utc"])[:5]
    arts = sorted(_noti(), key=lambda a: a.get("orden", 0), reverse=True)
    return {
        "lider": {"nombre": lider["nombre"], "puntos": lider["puntos"]} if lider else None,
        "top3": [{"pos": x["pos"], "nombre": x["nombre"], "puntos": x["puntos"]} for x in r[:3]],
        "en_directo": [f"{p['local']} {p['golesLocal']}-{p['golesVisitante']} {p['visitante']} ({p.get('minuto')})" for p in live],
        "proximos_partidos": [f"{p['local']} vs {p['visitante']} — {p['utc']} ({p['fase']})" for p in prox],
        "ultima_noticia": (arts[0]["titulo"] if arts else None),
        "actualizado": d.get("actualizado") or d.get("generado"),
    }


def t_clasificacion(_):
    return [{"pos": x["pos"], "nombre": x["nombre"], "puntos": x["puntos"],
             "clavados": x.get("clavados"), "campeon": x.get("campeon")}
            for x in _data().get("ranking", [])]


def t_partidos(args):
    d = _data()
    fase = args.get("fase")
    solo = args.get("solo_jugados", False)
    out = []
    for p in d["partidos"]:
        if fase and _norm(p.get("fase")) != _norm(fase):
            continue
        if solo and not p.get("jugado"):
            continue
        row = {"fase": p.get("fase"), "grupo": p.get("grupo") or None, "utc": p.get("utc"),
               "local": p.get("local"), "visitante": p.get("visitante"),
               "jugado": p.get("jugado"), "envivo": p.get("envivo")}
        if p.get("jugado") or p.get("envivo"):
            row["marcador"] = _marcador(p)
            if p.get("ganador"):
                row["avanza"] = p["local"] if p["ganador"] == "local" else p["visitante"]
        out.append(row)
    return out


def t_en_directo(_):
    d = _data()
    live = [p for p in d["partidos"] if p.get("envivo")]
    if not live:
        return {"mensaje": "No hay partidos en directo ahora mismo."}
    return [{"local": p["local"], "visitante": p["visitante"], "marcador": f"{p['golesLocal']}-{p['golesVisitante']}",
             "minuto": p.get("minuto"), "fase": p.get("fase")} for p in live]


def t_participante(args):
    nombre = args.get("nombre", "")
    d = _data()
    P = next((x for x in d["participantes"].values() if _norm(x["nombre"]) == _norm(nombre)
              or _norm(nombre) in _norm(x["nombre"])), None)
    if not P:
        nombres = [x["nombre"] for x in d["participantes"].values()]
        return {"error": f"No encuentro a '{nombre}'.", "participantes": nombres}
    rk = next((x for x in d["ranking"] if x["id"] == P["id"]), {})
    return {
        "nombre": P["nombre"], "posicion": rk.get("pos"), "puntos": rk.get("puntos"),
        "clavados": rk.get("clavados"), "diferencias": rk.get("diferencias"), "signos": rk.get("signos"),
        "campeon": P.get("campeon"), "subcampeon": P.get("subcampeon"), "tercero": P.get("tercero"),
        "bota_oro": P.get("bota_oro"), "balon_oro": P.get("balon_oro"),
        "desglose": (P.get("ko") or {}).get("rows"),
    }


def t_cruces(args):
    d = _data()
    fase = args.get("fase")
    fases_ko = ("Dieciseisavos", "Octavos", "Cuartos", "Semifinales", "3er puesto", "Final")
    out = []
    for p in d["partidos"]:
        if p.get("fase") not in fases_ko:
            continue
        if fase and _norm(p.get("fase")) != _norm(fase):
            continue
        row = {"fase": p["fase"], "utc": p.get("utc"), "local": p.get("local"), "visitante": p.get("visitante")}
        if p.get("jugado"):
            row["marcador"] = _marcador(p)
            row["avanza"] = p["local"] if p.get("ganador") == "local" else (p["visitante"] if p.get("ganador") == "visitante" else None)
        out.append(row)
    return out


def t_noticias(args):
    n = int(args.get("n", 3) or 3)
    arts = sorted(_noti(), key=lambda a: a.get("orden", 0), reverse=True)[:max(1, min(n, 20))]
    return [{"titulo": a["titulo"], "fase": a.get("fase"), "fecha": a.get("fecha"),
             "firma": a.get("firma"), "cuerpo": a.get("cuerpo")} for a in arts]


TOOLS = [
    ("resumen", "Resumen rápido de la porra: líder, top 3, partidos en directo, próximos partidos y última noticia.",
     {"type": "object", "properties": {}}, t_resumen),
    ("clasificacion", "Clasificación completa de la porra (posición, nombre, puntos, clavados, campeón elegido).",
     {"type": "object", "properties": {}}, t_clasificacion),
    ("partidos", "Partidos del Mundial con su marcador. Filtra por fase y por si ya se jugaron.",
     {"type": "object", "properties": {
         "fase": {"type": "string", "description": "Grupos, Dieciseisavos, Octavos, Cuartos, Semifinales, Final..."},
         "solo_jugados": {"type": "boolean", "description": "Solo los ya jugados"}}}, t_partidos),
    ("en_directo", "Partidos que se están jugando ahora mismo (marcador y minuto).",
     {"type": "object", "properties": {}}, t_en_directo),
    ("participante", "Puntos y predicciones de un participante de la porra por su nombre.",
     {"type": "object", "properties": {"nombre": {"type": "string"}}, "required": ["nombre"]}, t_participante),
    ("cruces", "Cuadro de eliminatorias (quién juega contra quién y resultados).",
     {"type": "object", "properties": {"fase": {"type": "string"}}}, t_cruces),
    ("noticias", "Últimas crónicas de 'El Salseo' (el noticiero gamberro de la porra).",
     {"type": "object", "properties": {"n": {"type": "integer", "description": "Cuántas (por defecto 3)"}}}, t_noticias),
]
TOOL_DEFS = [{"name": n, "description": d, "inputSchema": s} for (n, d, s, _) in TOOLS]
TOOL_FN = {n: f for (n, _, _, f) in TOOLS}


def handle_rpc(msg):
    """Procesa un mensaje JSON-RPC. Devuelve dict de respuesta o None (notificación)."""
    mid = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": params.get("protocolVersion", PROTO),
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
            "instructions": "Datos de La Porra del Mundial 2026 (solo lectura). Usa 'resumen' para una vista rápida."}}
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOL_DEFS}}
    if method == "tools/call":
        name = params.get("name")
        fn = TOOL_FN.get(name)
        if not fn:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"Herramienta desconocida: {name}"}}
        try:
            data = fn(params.get("arguments") or {})
            text = json.dumps(data, ensure_ascii=False, indent=2)
            return {"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": text}]}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}}
    if mid is None:
        return None
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Método no soportado: {method}"}}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Mcp-Session-Id, MCP-Protocol-Version, Authorization")

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path.rstrip("/").endswith("/health"):
            return self._json({"ok": True, "server": SERVER_INFO})
        # Streamable HTTP GET (stream saliente) no lo usamos: servidor sin estado.
        self.send_response(405)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._json({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "JSON inválido"}}, 400)
        if isinstance(payload, list):
            out = [r for r in (handle_rpc(m) for m in payload) if r is not None]
            return self._json(out if out else {}, 200 if out else 202)
        resp = handle_rpc(payload)
        if resp is None:
            self.send_response(202)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._json(resp)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", "8000"))
    print(f"porra-mcp escuchando en :{port} (streamable HTTP)")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
