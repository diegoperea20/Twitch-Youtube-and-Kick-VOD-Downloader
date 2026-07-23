# 🎬 Descargador de VODs — Twitch, Kick & YouTube

Descargador multi-plataforma de VODs para **Twitch**, **Kick** y **YouTube**. Proporciona tanto una **interfaz gráfica Streamlit** (`app.py`) como una **herramienta CLI** (`download_vod.py`) para descargar videos con aceleración GPU, selección de calidad y recorte por rango de tiempo.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red.svg)
![FFmpeg](https://img.shields.io/badge/FFmpeg-Required-orange.svg)
![yt-dlp](https://img.shields.io/badge/yt--dlp-2025.1+-green.svg)

<p align="center">
  <img src="README-images/tkyotubeDowloader.png" alt="Captura de la aplicación">
</p>

---

## ✨ Características

- **🎯 Multi-Plataforma**: Descarga desde Twitch, Kick y YouTube
- **🎬 Selección de Calidad**: Elige entre las calidades y FPS disponibles
- **⏱️ Recorte por Tiempo**: Descarga segmentos específicos del video
- **🚀 Aceleración GPU**: NVIDIA NVENC, AMD AMF, Intel VAAPI/QuickSync
- **🎨 Interfaz Moderna**: Tema oscuro Streamlit inspirado en Twitch
- **🖥️ Herramienta CLI**: Operación headless mediante argumentos de línea de comandos
- **🤖 Preparado para IA**: Incluye `AGENTS.md` y `SKILL.md` para agentes de código como opencode, Claude Code y Codex

---

## 📋 Requisitos

- Python 3.11 o superior
- [uv](https://docs.astral.sh/uv/) — Gestor de paquetes Python
- [FFmpeg](https://ffmpeg.org/download.html) — Procesamiento de video/audio

---

## 🔧 Instalación

```powershell
# Clonar o navegar al proyecto
cd downloadvods

# Instalar dependencias
uv sync
```

### Instalar FFmpeg

- **Windows**: `winget install Gyan.FFmpeg` o descargar desde [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

### Verificar instalación

```powershell
uv run python -c "import streamlit; print('Streamlit:', streamlit.__version__)"
ffmpeg -version
```

---

## 🎯 Uso

### Interfaz Gráfica (Streamlit)

```powershell
uv run streamlit run app.py
```

Se abre en `http://localhost:8501`. Pega una URL, selecciona calidad, recorta el rango, activa GPU y descarga.

### CLI (Línea de Comandos)

```powershell
uv run python download_vod.py --url <URL> [opciones]
```

#### Parámetros

| Argumento | Requerido | Default | Descripción |
|---|---|---|---|
| `--url` | Sí | — | URL del video (Twitch, Kick, YouTube) |
| `--quality` | No | `best` | Calidad: `1080p60`, `720p`, etc. Inválida → best |
| `--start` | No | `0` | Tiempo de inicio (segundos o `HH:MM:SS`) |
| `--end` | No | `0` | Tiempo de fin (`0` = video completo) |
| `--no-gpu` | No | off | Deshabilitar aceleración GPU |
| `--output` / `-o` | No | `.` | Ruta de salida (archivo `.mp4` o directorio) |
| `--browser` | No | — | Navegador para cookies de YouTube (`chrome`, `firefox`, etc.) |
| `--quiet` / `-q` | No | off | Suprimir salida de progreso |

> **Nota para PowerShell:** Las URLs que contengan `&` (ej. YouTube con `&list=...`) **deben** ir entre comillas dobles (`"url"`). PowerShell trata `&` como un carácter especial.

#### Ejemplos

```powershell
# Descarga básica (mejor calidad, video completo, GPU automático)
uv run python download_vod.py --url https://www.twitch.tv/videos/123456789

# YouTube con calidad, rango de tiempo y cookies del navegador
uv run python download_vod.py --url "https://youtube.com/watch?v=xxxx&list=...&start_radio=1" --quality 1080p --start 00:05:00 --end 00:10:00 --browser chrome

# Video de Kick con ruta personalizada y sin GPU
uv run python download_vod.py --url https://kick.com/video/xxx --output D:\videos --no-gpu

# Modo silencioso — solo la ruta final va a stdout
$ruta = uv run python download_vod.py --url "https://youtube.com/watch?v=xxxx" --browser chrome --quiet 2>$null
```

---

## 📁 Estructura del Proyecto

```
downloadvods/
├── app.py              # Interfaz gráfica Streamlit
├── download_vod.py     # Herramienta CLI (autónoma)
├── AGENTS.md           # Guía del proyecto para agentes IA
├── SKILL.md            # Definición de skill para agentes IA
├── pyproject.toml      # Dependencias y metadatos del proyecto
├── requirements.txt    # Dependencias fijadas
├── README.es.md        # Este archivo
├── README.md           # Documentación en inglés
├── .python-version     # Versión de Python
├── packages.txt        # Paquetes del sistema (ffmpeg)
├── .venv/              # Entorno virtual
├── uv.lock             # Archivo de bloqueo
└── README-images/      # Capturas de pantalla
```

---

## 🖥️ Aceleración GPU

Codificadores detectados automáticamente:

| Fabricante | Codificador |
|---|---|
| NVIDIA | `h264_nvenc` |
| AMD | `h264_amf` |
| Intel | `h264_vaapi` / `h264_qsv` |

La GPU está habilitada por defecto en el CLI. Usa `--no-gpu` para deshabilitarla.

---

## 🛠️ Detalles Técnicos

### Dependencias

- **Streamlit** — Framework de interfaz web
- **yt-dlp** — Extracción y descarga de video
- **FFmpeg** — Codificación, transcodificación, recorte
- **Python 3.11+** — Entorno de ejecución

### Arquitectura

- **GUI**: `app.py` — Streamlit con CSS personalizado (tema oscuro Twitch)
- **CLI**: `download_vod.py` — Herramienta autónoma con argparse, sin importar nada de `app.py`
- **Pipeline**: yt-dlp descarga → ffprobe detección de códec → ffmpeg transcodificación/recorte → salida H.264 MP4

### Formato de Salida

- **Contenedor**: MP4
- **Video**: H.264 (libx264 CPU / NVENC / AMF / QSV / VAAPI GPU)
- **Audio**: AAC 192 kbps

---

## 🤖 Integración con Agentes IA

El proyecto incluye:

- **`AGENTS.md`** — Guía del proyecto para agentes de código (convenciones, configuración, referencia CLI)
- **`SKILL.md`** — Definición de skill instalable para opencode / Claude Code / Codex

> El CLI (`download_vod.py`) es autónomo. Los cambios en él no afectan la GUI (`app.py`) y viceversa.

---

### 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author / Autor

**Diego Ivan Perea Montealegre**

- GitHub: [@diegoperea20](https://github.com/diegoperea20)

---

Created by [Diego Ivan Perea Montealegre](https://github.com/diegoperea20)