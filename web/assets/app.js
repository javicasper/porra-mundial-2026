/* Utilidades compartidas entre las dos páginas. Sin lógica de render: cada página la suya. */
const FLAGS = {
  "México":"🇲🇽","Sudáfrica":"🇿🇦","Corea del Sur":"🇰🇷","República Checa":"🇨🇿","Canadá":"🇨🇦",
  "Catar":"🇶🇦","Suiza":"🇨🇭","Bosnia y Herzegovina":"🇧🇦","Brasil":"🇧🇷","Marruecos":"🇲🇦",
  "Escocia":"🏴󠁧󠁢󠁳󠁣󠁴󠁿","Haití":"🇭🇹","Estados Unidos":"🇺🇸","Turquía":"🇹🇷","Paraguay":"🇵🇾",
  "Australia":"🇦🇺","Alemania":"🇩🇪","Costa de Marfil":"🇨🇮","Ecuador":"🇪🇨","Curazao":"🇨🇼",
  "Países Bajos":"🇳🇱","Suecia":"🇸🇪","Túnez":"🇹🇳","Japón":"🇯🇵","Bélgica":"🇧🇪",
  "Nueva Zelanda":"🇳🇿","Egipto":"🇪🇬","Irán":"🇮🇷","España":"🇪🇸","Uruguay":"🇺🇾",
  "Arabia Saudita":"🇸🇦","Cabo Verde":"🇨🇻","Francia":"🇫🇷","Noruega":"🇳🇴","Senegal":"🇸🇳",
  "Irak":"🇮🇶","Argentina":"🇦🇷","Austria":"🇦🇹","Argelia":"🇩🇿","Jordania":"🇯🇴","Portugal":"🇵🇹",
  "Colombia":"🇨🇴","RD Congo":"🇨🇩","Uzbekistán":"🇺🇿","Inglaterra":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","Croacia":"🇭🇷",
  "Ghana":"🇬🇭","Panamá":"🇵🇦"
};
const fl = t => FLAGS[t] || "";
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

// Arranca una página: carga datos, llama render(d), y refresca cada 60s.
function iniciar(render) {
  const ciclo = async () => {
    try { _data = null; const d = await getData(); pintarMeta(d); render(d); }
    catch (e) { const v = $("#view"); if (v) v.innerHTML = `<div class="err">No se pudo cargar data.json (${e.message}).</div>`; }
  };
  ciclo();
  setInterval(ciclo, 60000);
}
