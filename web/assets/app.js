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
     <span class="bul"></span><span><b>${m.jugados}</b>/${m.total_grupos} partidos</span>
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
  ciclo();
  setInterval(ciclo, 30000);
}
