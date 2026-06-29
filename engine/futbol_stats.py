"""Hechos REALES de cada partido (héroes y paquetes) desde la API de ESPN, para
enriquecer las crónicas: goleadores, hat-tricks, asistencias, tarjetas rojas,
penaltis fallados/parados, goles en propia y porteros (paradón o coladero).

Se usa SOLO al generar la crónica de una ronda (no en el refresco de 30s).
"""
from __future__ import annotations
import json
import re
import unicodedata
import urllib.request
from datetime import datetime, timedelta

ESPN = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world"
GOL = ("Goal", "Goal - Header", "Goal - Free-kick", "Penalty - Scored")


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.load(urllib.request.urlopen(req, timeout=25))


def _norm(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().strip().lower()


def _ath(e):
    a = e.get("participants") or e.get("athletesInvolved") or []
    if not a:
        return ""
    x = a[0]
    return (x.get("athlete", {}) or {}).get("displayName") or x.get("displayName") or ""


def evento_id(tla_local, tla_visit, fecha_iso):
    """Busca el id de evento ESPN por TLAs y fecha (±1 día)."""
    d = datetime.fromisoformat(fecha_iso.replace("Z", "+00:00"))
    rng = f"{(d - timedelta(days=1)):%Y%m%d}-{(d + timedelta(days=1)):%Y%m%d}"
    sb = _get(f"{ESPN}/scoreboard?dates={rng}")
    want = {_norm(tla_local), _norm(tla_visit)}
    for ev in sb.get("events", []):
        comps = (ev.get("competitions") or [{}])[0].get("competitors", [])
        tlas = {_norm((c.get("team") or {}).get("abbreviation")) for c in comps}
        if want == tlas:
            return ev["id"]
    return None


def hechos_partido(event_id):
    """Devuelve héroes y paquetes de un partido a partir del summary de ESPN."""
    s = _get(f"{ESPN}/summary?event={event_id}")
    ke = s.get("keyEvents", [])
    goles, rojas, penal_fallados, propias = [], [], [], []
    contador = {}
    for e in ke:
        t = (e.get("type") or {}).get("text", "")
        who = _ath(e)
        minuto = (e.get("clock") or {}).get("displayValue", "")
        txt = e.get("text", "")
        if t in GOL:
            asis = ""
            m = re.search(r"[Aa]ssisted by ([^.,]+)", txt)
            if m:
                asis = re.split(r"\s+(?:with|following|after)\b", m.group(1))[0].strip()
            goles.append({"jugador": who, "min": minuto, "penalti": "Penalty" in t,
                          "cabeza": "Header" in t, "asistencia": asis})
            contador[who] = contador.get(who, 0) + 1
        elif t == "Own Goal":
            propias.append({"jugador": who, "min": minuto})
        elif t == "Red Card":
            rojas.append({"jugador": who, "min": minuto})
        elif t in ("Penalty - Saved", "Penalty - Missed"):
            penal_fallados.append({"jugador": who, "min": minuto, "tipo": t})
    hat = [j for j, n in contador.items() if n >= 3]
    dobletes = [j for j, n in contador.items() if n == 2]

    # porteros: solo los que tienen 'saves' (stat exclusiva de portero, evita los de campo)
    porteros = []
    for r in s.get("rosters", []):
        equipo = (r.get("team") or {}).get("displayName", "")
        for x in (r.get("roster") or []):
            st = {y.get("name"): y.get("value") for y in (x.get("stats") or [])}
            sav = st.get("saves")
            if sav is None:
                continue  # no es portero
            sav, enc = int(sav), int(st.get("goalsConceded") or 0)
            nm = (x.get("athlete") or {}).get("displayName", "")
            rol = "coladero" if enc >= 4 else ("paradón" if sav >= 5 else "")
            if rol:
                porteros.append({"jugador": nm, "equipo": equipo, "paradas": sav,
                                 "encajados": enc, "rol": rol})

    return {"event_id": event_id, "goles": goles, "hat_tricks": hat, "dobletes": dobletes,
            "rojas": rojas, "penaltis_fallados": penal_fallados, "goles_propia": propias,
            "porteros": porteros}


def hechos_ronda(d, fase):
    """Hechos de todos los partidos jugados de una fase (KO)."""
    out = []
    for p in d["partidos"]:
        if p.get("fase") != fase or not p.get("jugado"):
            continue
        try:
            eid = evento_id(p["tlaLocal"], p["tlaVisitante"], p["utc"])
            h = hechos_partido(eid) if eid else {}
        except Exception as e:
            h = {"error": str(e)}
        out.append({"local": p["local"], "visitante": p["visitante"],
                    "marcador": f"{p['golesLocal']}-{p['golesVisitante']}", **h})
    return out


if __name__ == "__main__":
    import sys
    print(json.dumps(hechos_partido(sys.argv[1] if len(sys.argv) > 1 else "760475"),
                     ensure_ascii=False, indent=2))
