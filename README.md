![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Pillow](https://img.shields.io/badge/Pillow-12.x-00599C?logo=python&logoColor=white)
![CustomTkinter](https://img.shields.io/badge/CustomTkinter-5.x-1F6FEB)
![PyInstaller](https://img.shields.io/badge/PyInstaller-6.x-FFCC00?logo=python&logoColor=black)
![uv](https://img.shields.io/badge/uv-package%20manager-DE5FE9)
![Platform](https://img.shields.io/badge/Platform-Windows%20|%20macOS%20|%20Linux-lightgrey)

# Compresor de Imágenes

Aplicación de escritorio para comprimir imágenes en lote sin modificar su resolución. Pensada para usuarios no técnicos.

## Características

- **Formatos de salida**: JPEG, WebP, AVIF, PNG y TIFF (o mantener el formato original)
- **Selector de calidad**: slider de 10 a 100
- **Subsampling de crominancia**: 4:2:0, 4:2:2 o 4:4:4 (solo JPEG)
- **Recorrido recursivo**: procesa subcarpetas y replica la estructura de directorios en la salida
- **Filtro de imágenes impares**: opción para procesar solo las imágenes en posición impar (1ª, 3ª, 5ª...)
- **Preserva metadatos EXIF** (coordenadas GPS, cámara, fecha, etc.)
- **Multiprocesado**: usa todos los cores del equipo para acelerar la compresión (desactivable)
- **Compatible con discos de red**: permite escribir rutas de red manualmente (ej. `\\servidor\carpeta`)
- **Modo claro/oscuro**: se adapta automáticamente al tema del sistema
- **Barra de progreso** y resumen final con tamaño antes/después

## Requisitos

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (gestor de paquetes)
- Python 3.11+
- tkinter (incluido en Windows; en macOS: `brew install python-tk@3.14`; en Linux: `sudo apt install python3-tk`)

## Instalación y ejecución

```bash
git clone <url-del-repositorio>
cd image-compressor
uv sync
uv run python app.py
```

## Generar ejecutable

El ejecutable incluye todo lo necesario (Python, dependencias, código). Se puede distribuir sin instalar nada.

```bash
uv run pyinstaller -y --onefile --windowed --name "Compresor de Imagenes" --icon icon.ico --add-data "icon.png:." app.py
```

El resultado queda en `dist/`:

| SO | Archivo | Uso |
|---|---|---|
| Windows | `Compresor de Imagenes.exe` | Doble clic |
| macOS | `Compresor de Imagenes.app` | Doble clic |
| Linux | `Compresor de Imagenes` | `./Compresor\ de\ Imagenes` |

> **Nota:** El build debe ejecutarse en cada sistema operativo. No se puede generar el `.exe` de Windows desde macOS o viceversa.
