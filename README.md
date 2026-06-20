![La Porra del Mundial](docs/banner.png)

# La Porra del Mundial 2026

Web autoalojada para seguir una **porra/quiniela de la Copa Mundial FIFA 2026**: clasificación de los participantes con **puntuación calculada en vivo**, resultados y calendario, tablas de grupos, goleadores y el cuadro de eliminatorias de cada uno.

Cada participante rellena su quiniela (campeón, marcadores de los 72 partidos de grupos, cruces de eliminatorias, Bota/Balón de Oro…) y la web cruza esos pronósticos con los **resultados reales** que se descargan automáticamente de una API, recalculando la clasificación cada minuto.

## Características

- 🏆 **Clasificación en vivo** de la porra, con desglose (clavados / diferencias / signos) y empates resueltos.
- 📊 **Evolución**: gráfico de puntos acumulados por partido, una línea por participante.
- 🧾 **Ficha por participante**: sus apuestas, su cuadro de eliminatorias y su quiniela partido a partido frente al resultado real.
- ⚽ **Resultados y calendario** con horario peninsular, partidos **en directo** y **minuto real**.
- 🗂️ **Tablas de grupos** (PJ · G · E · P · GF · GC · DG · Pts + forma) y **cuadro de cruces**.
- 🥇 **Goleadores** (Bota de Oro).
- Se **actualiza solo** cada minuto. Frontend estático (sin framework), un único `data.json`.

## Cómo funciona

```
football-data.org (estructura, grupos, goleadores)  ┐
                                                     ├─►  build_web_data.py  ─►  web/data.json  ─►  frontend estático
ESPN scoreboard (marcador + minuto en vivo)          ┘            │
                                                          engine/scoring.py (motor de puntuación)
```

- **`engine/scoring.py`** — motor de puntuación (reglas en `data/reglas.json`).
- **`web/build_web_data.py`** — descarga la API, fusiona ESPN para el directo, puntúa y genera `web/data.json`.
- **`web/index.html`** (La Porra) y **`web/mundial.html`** (Resultados) — dos páginas estáticas que leen `data.json`. CSS/JS en `web/assets/`.

## Puesta en marcha

Necesitas una clave gratuita de [football-data.org](https://www.football-data.org/client/register).

```bash
cp .env.example .env          # y pon tu FOOTBALLDATA_API_KEY
pip install  # (no hay dependencias: el generador usa solo la stdlib de Python)

# Genera data.json (usa data/predicciones.json si existe; si no, el ejemplo anonimizado)
FOOTBALLDATA_API_KEY=tu_clave python web/build_web_data.py

# Sirve la web estática
python -m http.server 8000 -d web   # abre http://localhost:8000
```

### Con Docker (nginx + refresco automático)

```bash
docker compose up -d
```

Levanta `porra-web` (nginx sirviendo `web/`) y `porra-refresh` (regenera `data.json` cada 60 s). Pensado para ir detrás de un reverse proxy (Traefik, etc.).

## Tus datos

Las predicciones reales van en **`data/predicciones.json`** (ignorado por git, son datos personales). El repo incluye **`data/predicciones.sample.json`** con 3 participantes ficticios para que puedas ver el formato y arrancar sin datos reales. Ese mismo formato lo produce, en este caso, una plantilla de Excel que cada participante rellena.

El motor está validado: cada quiniela puntuada contra sí misma da el máximo teórico (`python engine/test_motor.py`).

## Estructura

```
data/        reglas.json, equipos_map.json, predicciones.sample.json
engine/      scoring.py (motor) · test_motor.py · build_resultados.py
web/         index.html · mundial.html · assets/{style.css,app.js} · build_web_data.py
deploy/      nginx.conf
docs/        banner
docker-compose.yml
```

## Créditos

Datos de [football-data.org](https://www.football-data.org/) y [ESPN](https://www.espn.com/). Hecho por gusto para la porra de la oficina.

## Licencia

MIT — ver [LICENSE](LICENSE).
