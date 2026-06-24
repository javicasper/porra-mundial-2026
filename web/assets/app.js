/* Utilidades compartidas entre las dos páginas. Sin lógica de render: cada página la suya. */
/* Banderas como SVG (flag-icons) en vez de emoji: se ven igual en todos los SO (Windows no pinta emoji-bandera). */
const FLAG_CODES = {
  "México":"mx","Sudáfrica":"za","Corea del Sur":"kr","República Checa":"cz","Canadá":"ca",
  "Catar":"qa","Suiza":"ch","Bosnia y Herzegovina":"ba","Brasil":"br","Marruecos":"ma",
  "Escocia":"gb-sct","Haití":"ht","Estados Unidos":"us","Turquía":"tr","Paraguay":"py",
  "Australia":"au","Alemania":"de","Costa de Marfil":"ci","Ecuador":"ec","Curazao":"cw",
  "Países Bajos":"nl","Suecia":"se","Túnez":"tn","Japón":"jp","Bélgica":"be",
  "Nueva Zelanda":"nz","Egipto":"eg","Irán":"ir","España":"es","Uruguay":"uy",
  "Arabia Saudita":"sa","Cabo Verde":"cv","Francia":"fr","Noruega":"no","Senegal":"sn",
  "Irak":"iq","Argentina":"ar","Austria":"at","Argelia":"dz","Jordania":"jo","Portugal":"pt",
  "Colombia":"co","RD Congo":"cd","Uzbekistán":"uz","Inglaterra":"gb-eng","Croacia":"hr",
  "Ghana":"gh","Panamá":"pa"
};
const fl = t => {
  const c = FLAG_CODES[t];
  return c ? `<img class="flag" src="assets/flags/${c}.svg" alt="" loading="lazy">` : "";
};

/* Iconos SVG (Lucide/Tabler/Phosphor, MIT). Color horneado: verde clavados, oro el resto. */
const _GOLD = "#bd9a2a", _GREEN = "#1d6b4c";
const ICON = {
  target: `<svg class="isvg" viewBox="0 0 24 24" fill="none" stroke="${_GREEN}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 12a1 1 0 1 0 2 0a1 1 0 1 0 -2 0"/><path d="M12 7a5 5 0 1 0 5 5"/><path d="M13 3.055a9 9 0 1 0 7.941 7.945"/><path d="M15 6v3h3l3 -3h-3v-3l-3 3"/><path d="M15 9l-3 3"/></svg>`,
  trophy: `<svg class="isvg" viewBox="0 0 24 24" fill="none" stroke="${_GOLD}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 14.66v1.626a2 2 0 0 1-.976 1.696A5 5 0 0 0 7 21.978"/><path d="M14 14.66v1.626a2 2 0 0 0 .976 1.696A5 5 0 0 1 17 21.978"/><path d="M18 9h1.5a1 1 0 0 0 0-5H18"/><path d="M4 22h16"/><path d="M6 9a6 6 0 0 0 12 0V3a1 1 0 0 0-1-1H7a1 1 0 0 0-1 1z"/><path d="M6 9H4.5a1 1 0 0 1 0-5H6"/></svg>`,
  boot: `<svg class="isvg" viewBox="0 0 256 256" fill="${_GOLD}" aria-hidden="true"><path d="M231.16,166.63l-28.63-14.31A47.74,47.74,0,0,1,176,109.39V80a8,8,0,0,0-8-8,48.05,48.05,0,0,1-48-48,8,8,0,0,0-12.83-6.37L30.13,76l-.2.16a16,16,0,0,0-1.24,23.75L142.4,213.66a8,8,0,0,0,5.66,2.34H224a16,16,0,0,0,16-16V180.94A15.92,15.92,0,0,0,231.16,166.63ZM224,200H151.37L40,88.63l12.87-9.76,38.79,38.79A8,8,0,0,0,103,106.34L65.74,69.11l40-30.31A64.15,64.15,0,0,0,160,87.5v21.89a63.65,63.65,0,0,0,35.38,57.24L224,180.94ZM70.8,184H32a8,8,0,0,1,0-16H70.8a8,8,0,1,1,0,16Zm40,24a8,8,0,0,1-8,8H48a8,8,0,0,1,0-16h54.8A8,8,0,0,1,110.8,208Z"/></svg>`,
  ball: `<svg class="isvg" viewBox="0 0 24 24" fill="none" stroke="${_GOLD}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 1 0 18 0a9 9 0 1 0 -18 0"/><path d="M12 7l4.76 3.45l-1.76 5.55h-6l-1.76 -5.55l4.76 -3.45"/><path d="M12 7v-4m3 13l2.5 3m-.74 -8.55l3.74 -1.45m-11.44 7.05l-2.56 2.95m.74 -8.55l-3.74 -1.45"/></svg>`,
  medal: pos => {
    const c = pos === 1 ? "#bd9a2a" : pos === 2 ? "#9aa1ac" : "#b3784a";
    return `<svg class="isvg medal" viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8.5 3l2.4 5.2M15.5 3l-2.4 5.2"/><circle cx="12" cy="14.5" r="5.3" fill="${c}" stroke="none"/><path d="M12 11.7l.85 1.72 1.9.28-1.37 1.34.32 1.9L12 16.34l-1.7.9.32-1.9-1.37-1.34 1.9-.28z" fill="#fffefb" stroke="none"/></svg>`;
  },
};

const $ = s => document.querySelector(s);
const MAD = { timeZone: "Europe/Madrid" };
const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
const hora   = u => u ? new Date(u).toLocaleTimeString("es-ES", { ...MAD, hour:"2-digit", minute:"2-digit" }) : "·";
const diaKey = u => u ? new Date(u).toLocaleDateString("sv-SE", MAD) : "9999";
const diaLbl = u => u ? cap(new Date(u).toLocaleDateString("es-ES", { ...MAD, weekday:"long", day:"numeric", month:"long" })) : "";

// Normaliza nombre de selección (sin acentos, minúsculas) para casar partido<->pronóstico.
const _norm = s => (s||"").normalize("NFKD").replace(/[\u0300-\u036f]/g,"").trim().toLowerCase();
// Clave de partido independiente del orden local/visitante.
const pkey = (a,b) => [_norm(a),_norm(b)].sort().join("|");
// Clave de partido para el DIRECTO: hora + código FIFA del local. Desambigua los
// partidos que se juegan a la misma hora (si no, el 2.º cogía los datos del 1.º).
const liveKey = p => (p.utc||"").slice(0,16) + "|" + (p.tlaLocal||"");

// Minuto EN VIVO estimado desde el inicio (la API gratis no da el minuto real).
// IN_PLAY -> minuto aproximado; PAUSED -> "Descanso".
function liveMinute(p) {
  if (p.minuto) return p.minuto;          // minuto real (ESPN)
  if (p.status === "PAUSED") return "Descanso";
  if (!p.utc) return "EN JUEGO";
  const elapsed = Math.floor((Date.now() - new Date(p.utc).getTime()) / 60000);
  if (elapsed < 0) return "EN JUEGO";
  if (elapsed <= 45) return "~" + Math.max(1, elapsed) + "'";
  if (elapsed < 60) return "Descanso";
  const m = elapsed - 15;                 // ~15 min de descanso
  return m >= 90 ? "90+'" : "~" + m + "'";
}

// Datos cacheados en memoria; cada página llama a getData() y luego render().
let _data = null;
async function getData() {
  if (_data) return _data;
  const r = await fetch("data.json?_=" + Date.now());
  if (!r.ok) throw new Error("HTTP " + r.status);
  _data = await r.json();
  return _data;
}

// Pinta cabecera (live + meta) común a las dos páginas.
function pintarMeta(d) {
  const m = d.meta, el = $("#meta");
  if (el) el.innerHTML =
    `<span class="live"><span class="dot"></span>EN VIVO</span>
     <span class="bul"></span><span><b>${m.jugados}</b>/${m.total_grupos}</span>
     <span class="bul"></span><span>Líder${m.n_lideres>1?"es":""} <b>${m.lider}</b></span>`;
  const f = $("#foot");
  if (f) f.innerHTML =
    `Resultados en directo · datos de football-data.org · hora peninsular<br>
     Actualizado ${new Date(d.generado).toLocaleString("es-ES", MAD)}`;
}

// Arranca una página. Refresca cada 30s, pero SOLO re-renderiza si los datos
// cambiaron (compara `generado`), preservando scroll y filas abiertas. Así el
// marcador en vivo entra solo sin cerrar lo que tengas abierto ni dar saltos.
let _lastSig = null;
// Firma del contenido que de verdad importa (ignora el timestamp `generado`, que
// cambia en cada regeneración aunque el marcador siga igual).
function _sig(d) {
  const r = d.ranking.map(x => `${x.id}:${x.puntos}:${x.clavados}`).join(",");
  const p = d.partidos.map(x => `${x.status}|${x.golesLocal}|${x.golesVisitante}|${x.minuto || ""}`).join(",");
  return d.meta.jugados + "#" + r + "#" + p;
}
/* ---- Motor de DIRECTO desde el cliente ----
   ESPN permite fetch directo (CORS *). Pedimos su marcador cada 10s (latencia
   casi nula) y, entre peticiones, un reloj corre cada segundo (MM:SS). Solo
   parchea las cajas .bx2[data-live] en sitio: ni re-render ni saltos. */
let _refresh = () => {};
const _EVBALL = `<svg class="evball" viewBox="0 0 24 24" fill="none" stroke="#15161b" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 1 0 18 0a9 9 0 1 0 -18 0"/><path d="M12 7l4.76 3.45l-1.76 5.55h-6l-1.76 -5.55l4.76 -3.45"/></svg>`;
async function _espnLive() {
  try {
    const r = await fetch("https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard", { cache: "no-store" });
    if (!r.ok) return {};
    const d = await r.json(), out = {};
    for (const e of d.events || []) {
      const comp = e.competitions[0], c = comp.competitors;
      const h = c.find(x => x.homeAway === "home"), a = c.find(x => x.homeAway === "away");
      const hid = h && h.team && h.team.id;
      const events = (comp.details || []).map(x => {
        const t = (x.type || {}).text || "", who = (x.athletesInvolved || []).map(z => z.displayName).filter(Boolean)[0] || "";
        let kind = null;
        if (x.scoringPlay || /Goal/.test(t)) kind = x.ownGoal ? "og" : (x.penaltyKick ? "pen" : "goal");
        else if (x.redCard || /Red/.test(t)) kind = "red";
        else if (x.yellowCard || /Yellow/.test(t)) kind = "yellow";
        else return null;
        return { kind, clock: (x.clock || {}).displayValue || "", side: ((x.team || {}).id === hid) ? "h" : "a", who };
      }).filter(Boolean);
      const stf = (team, name) => {
        const x = (team.statistics || []).find(z => z.name === name);
        if (!x) return null;
        const v = parseFloat(x.displayValue);
        return isNaN(v) ? x.displayValue : Math.round(v);
      };
      const stats = {
        posesion: [stf(h, "possessionPct"), stf(a, "possessionPct")],
        tiros: [stf(h, "totalShots"), stf(a, "totalShots")],
        aPuerta: [stf(h, "shotsOnTarget"), stf(a, "shotsOnTarget")],
        corners: [stf(h, "wonCorners"), stf(a, "wonCorners")],
        faltas: [stf(h, "foulsCommitted"), stf(a, "foulsCommitted")],
      };
      const hayStats = Object.values(stats).some(p => p.some(v => v != null));
      const colores = [_teamColor(h.team), _teamColor(a.team)];
      const ty = e.status.type;
      const clock = (ty.name === "STATUS_HALFTIME" || ty.shortDetail === "HT") ? "Descanso" : e.status.displayClock;
      const habbr = (h && h.team && h.team.abbreviation) || "";
      out[(e.date || "").slice(0, 16) + "|" + habbr] = { state: ty.state, clock, gl: h && h.score, gv: a && a.score, events, stats: hayStats ? stats : null, colores };
    }
    return out;
  } catch (e) { return {}; }
}

// color de selección (de ESPN); cae al alternativo si el principal es muy claro
function _teamColor(team) {
  const c = (team && team.color) || "", alt = (team && team.alternateColor) || "";
  const claro = x => { const n = parseInt(x, 16); if (isNaN(n) || x.length < 6) return true;
    return (0.2126 * (n >> 16) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255)) > 200; };
  const pick = (c && !claro(c)) ? c : ((alt && !claro(alt)) ? alt : (c || alt));
  return pick ? "#" + pick : null;
}
// ---- Panel del partido en vivo: eventos (colapsable) + estadísticas ----
const _panelOpen = {};   // key utc -> ¿eventos expandidos?
const _STAT_LBL = { posesion: "Posesión", tiros: "Tiros", aPuerta: "Tiros a puerta", corners: "Córners", faltas: "Faltas" };

function _evRows(events, limit) {
  if (!events || !events.length) return "";
  const mark = ev => ev.kind === "yellow" ? '<span class="evcard yel"></span>'
    : ev.kind === "red" ? '<span class="evcard red"></span>' : _EVBALL;
  const sfx = ev => ev.kind === "pen" ? " (pen.)" : ev.kind === "og" ? " (p.p.)" : "";
  let list = events.slice().reverse();           // más recientes arriba
  if (limit) list = list.slice(0, limit);
  return list.map(ev =>
    `<div class="evrow ${ev.side}"><span class="evmin">${ev.clock}</span>${mark(ev)}<span class="evwho">${ev.who}${sfx(ev)}</span></div>`
  ).join("");
}
function _statsHTML(stats, colores) {
  if (!stats) return "";
  const num = v => v == null ? "–" : v;
  const cH = (colores && colores[0]) || "var(--accent)", cA = (colores && colores[1]) || "#df9b7a";
  const pos = stats.posesion || [null, null];
  let h = "";
  if (pos[0] != null || pos[1] != null) {
    const ph = +pos[0] || 0, pa = +pos[1] || 0, tot = (ph + pa) || 1;
    h += `<div class="statposs"><span>${num(pos[0])}%</span><b>Posesión</b><span>${num(pos[1])}%</span></div>
      <div class="possbar" style="background:${cA}"><i style="width:${Math.round(100 * ph / tot)}%;background:${cH}"></i></div>`;
  }
  for (const k of ["tiros", "aPuerta", "corners", "faltas"]) {
    const v = stats[k]; if (!v || (v[0] == null && v[1] == null)) continue;
    h += `<div class="statrow"><span class="sh">${num(v[0])}</span><span class="sl">${_STAT_LBL[k]}</span><span class="sa">${num(v[1])}</span></div>`;
  }
  return h ? `<div class="statbox">${h}</div>` : "";
}
// Contenido del panel (eventos colapsables + stats). Lo usan servidor-render y cliente.
function livePanelInner(key, eventos, stats, colores) {
  const evs = eventos || [];
  let ev = "";
  if (evs.length) {
    const open = !!_panelOpen[key];
    ev = `<div class="evlist">${_evRows(evs, open ? 0 : 3)}</div>`;
    if (evs.length > 3) ev += `<button class="evmore" data-key="${key}">${open ? "Ocultar" : "Ver " + (evs.length - 3) + " más"}</button>`;
  }
  return ev + _statsHTML(stats, colores);
}
function livePanel(key, eventos, stats, colores) {
  const inner = livePanelInner(key, eventos, stats, colores);
  return inner ? `<div class="livepanel" data-key="${key}">${inner}</div>` : "";
}
// compat: el render de las páginas llama a esto por cada partido en vivo
function evlistHTML(p) {
  return livePanel(liveKey(p), p.eventos, p.stats, p.colores);
}

async function _pollLive() {
  const boxes = document.querySelectorAll(".bx2[data-live]");
  if (!boxes.length) return;
  const esp = await _espnLive();
  let cambio = false;
  boxes.forEach(el => {
    const key = el.dataset.live, e = esp[key]; if (!e) return;
    const s = el.querySelector(".s"), lv = el.querySelector(".lv");
    if (e.state === "in") {
      if (s && e.gl != null) { const nuevo = `${e.gl}-${e.gv}`; if (s.textContent !== nuevo) cambio = true; s.textContent = nuevo; }
      if (lv && e.clock) lv.textContent = "● " + e.clock;     // minuto real de ESPN (sin inventar segundos)
    } else if (e.state === "post") {
      if (lv) lv.textContent = "● FINAL"; cambio = true;
    }
    const mt = el.closest(".mt");
    if (mt) {
      const inner = livePanelInner(key, e.events, e.stats, e.colores);
      // el panel de directo va tras la fila y, si existe, tras el de pronósticos
      let after = mt;
      if (after.nextElementSibling && after.nextElementSibling.classList.contains("preds")) after = after.nextElementSibling;
      let panel = after.nextElementSibling;
      const isPanel = panel && panel.classList && panel.classList.contains("livepanel");
      if (inner) {
        if (!isPanel) { panel = document.createElement("div"); panel.className = "livepanel"; panel.dataset.key = key; after.parentNode.insertBefore(panel, after.nextSibling); }
        if (panel.innerHTML !== inner) panel.innerHTML = inner;
      } else if (isPanel) { panel.remove(); }
    }
  });
  if (cambio) _refresh();   // un gol o el final: que el resto (ranking) se ponga al día ya
}
// Botón "Ver más / Ocultar" (delegado, sobrevive a re-render)
document.addEventListener("click", ev => {
  const b = ev.target.closest(".evmore"); if (!b) return;
  ev.preventDefault();
  const key = b.dataset.key;
  _panelOpen[key] = !_panelOpen[key];
  const panel = document.querySelector(`.livepanel[data-key="${key}"]`);
  const p = _data && (_data.partidos || []).find(x => liveKey(x) === key);
  if (panel && p) panel.innerHTML = livePanelInner(key, p.eventos, p.stats, p.colores);
});
function liveEngine() {
  _pollLive();
  setInterval(_pollLive, 10000);
}

function iniciar(render) {
  const ciclo = async () => {
    try {
      _data = null;
      const d = await getData();
      pintarMeta(d);
      const sig = _sig(d);
      if (sig === _lastSig) return;                 // nada nuevo: no tocar el DOM
      const y = window.scrollY;
      const abiertas = [...document.querySelectorAll(".lr.open")].map(r => r.dataset.id);
      render(d);
      // re-abrir las fichas que estaban desplegadas
      abiertas.forEach(id => {
        const r = document.querySelector(`.lr[data-id="${id}"]`);
        const pd = r && r.nextElementSibling;
        if (pd && pd.classList.contains("pdet")) {
          r.classList.add("open");
          if (!pd.dataset.built && typeof detalle === "function") {
            pd.innerHTML = detalle(d.participantes[id], d); pd.dataset.built = "1";
          }
        }
      });
      window.scrollTo(0, y);
      _lastSig = sig;
    } catch (e) {
      const v = $("#view"); if (v && !_lastSig) v.innerHTML = `<div class="err">No se pudo cargar data.json (${e.message}).</div>`;
    }
  };
  _refresh = ciclo;
  ciclo();
  setInterval(ciclo, 30000);
  liveEngine();
}
