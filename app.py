#!/usr/bin/env python3
"""Compresor de imágenes — aplicación de escritorio."""

import multiprocessing
import os
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

VERSION = "1.0.0"
AUTHOR = "Asier Ortiz"

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif",
    ".webp", ".avif", ".gif", ".heic", ".heif",
}

FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "WebP": ".webp",
    "AVIF": ".avif",
    "PNG": ".png",
    "TIFF": ".tiff",
}

EXTENSION_TO_FORMAT = {
    ".jpg": "JPEG", ".jpeg": "JPEG",
    ".png": "PNG",
    ".bmp": "BMP",
    ".tiff": "TIFF", ".tif": "TIFF",
    ".webp": "WebP",
    ".avif": "AVIF",
    ".gif": "GIF",
    ".heic": "JPEG", ".heif": "JPEG",
}

TOOLTIPS = {
    "formato": "Formato de salida de las imágenes comprimidas",
    "calidad": "Nivel de compresión: menor = archivo más ligero pero menos calidad",
    "subsampling": "Reducción de información de color (solo JPEG).\n4:2:0 = más agresivo, 4:4:4 = preserva todo el color",
    "mantener_formato": "Recomprime cada imagen en su formato original sin convertir",
    "preservar_metadatos": "Conserva datos EXIF embebidos (GPS, cámara, fecha, etc.)",
    "multiprocesado": "Usa todos los cores del equipo para comprimir en paralelo",
    "solo_impares": "Procesa solo las imágenes en posición impar (1ª, 3ª, 5ª...), descartando el resto",
}

WINDOW_SIZE = "620x530"


# ── Tooltip ────────────────────────────────────────────────────────────────


class Tooltip:
    """Tooltip that appears on hover over a widget."""

    def __init__(self, widget, text: str):
        self._widget = widget
        self._text = text
        self._tooltip_window = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event):
        x = self._widget.winfo_rootx() + self._widget.winfo_width() + 5
        y = self._widget.winfo_rooty()

        self._tooltip_window = tw = ctk.CTkToplevel(self._widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)

        label = ctk.CTkLabel(
            tw,
            text=self._text,
            font=("", 11),
            fg_color=("gray90", "gray20"),
            corner_radius=6,
            padx=10,
            pady=6,
        )
        label.pack()

    def _hide(self, _event):
        if self._tooltip_window:
            self._tooltip_window.destroy()
            self._tooltip_window = None


def info_icon(parent, tooltip_key: str) -> ctk.CTkLabel:
    """Create a small ⓘ label with a tooltip."""
    label = ctk.CTkLabel(
        parent,
        text="ⓘ",
        font=("", 13),
        text_color="gray",
        width=16,
    )
    Tooltip(label, TOOLTIPS[tooltip_key])
    return label


# ── Compression logic (top-level for multiprocessing) ──────────────────────


def compress_image(
    src_path: str,
    dst_path: str,
    fmt: str,
    quality: int,
    preserve_metadata: bool,
    subsampling: str,
) -> tuple[str, int, int]:
    """Compress a single image. Returns (filename, original_size, new_size)."""
    img = Image.open(src_path)
    original_size = os.path.getsize(src_path)

    save_kwargs: dict = {}

    if preserve_metadata:
        exif_data = img.info.get("exif")
        if exif_data:
            save_kwargs["exif"] = exif_data

    if fmt == "JPEG":
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        save_kwargs["quality"] = quality
        save_kwargs["optimize"] = True
        save_kwargs["subsampling"] = subsampling
    elif fmt == "WebP":
        save_kwargs["quality"] = quality
        save_kwargs["method"] = 4
    elif fmt == "AVIF":
        save_kwargs["quality"] = quality
    elif fmt == "PNG":
        if img.mode == "CMYK":
            img = img.convert("RGB")
        save_kwargs["optimize"] = True
    elif fmt == "TIFF":
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        save_kwargs["compression"] = "tiff_jpeg"
        save_kwargs["quality"] = quality
    elif fmt == "BMP":
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
    elif fmt == "GIF":
        if img.mode not in ("P", "L"):
            img = img.convert("P")

    img.save(dst_path, **save_kwargs)
    new_size = os.path.getsize(dst_path)
    return os.path.basename(src_path), original_size, new_size


# ── GUI ────────────────────────────────────────────────────────────────────


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Compresor de Imágenes")
        self.geometry(WINDOW_SIZE)
        self.resizable(False, False)
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")
        self._processing = False
        self._build_ui()
        self.createcommand("tkAboutDialog", self._show_about)

    # ── Build UI ───────────────────────────────────────────────────────

    def _build_ui(self):
        # — Input folder —
        fr_in = ctk.CTkFrame(self)
        fr_in.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(fr_in, text="Carpeta de origen:", font=("", 12, "bold")).pack(
            anchor="w", padx=10, pady=(8, 2)
        )
        row_in = ctk.CTkFrame(fr_in, fg_color="transparent")
        row_in.pack(fill="x", padx=10, pady=(0, 4))

        self.input_var = ctk.StringVar()
        entry_in = ctk.CTkEntry(
            row_in,
            textvariable=self.input_var,
            placeholder_text=r"Ruta local o de red (\\servidor\carpeta)...",
        )
        entry_in.pack(side="left", fill="x", expand=True, padx=(0, 8))
        entry_in.bind("<Return>", lambda _: self._update_input_info())
        entry_in.bind("<FocusOut>", lambda _: self._update_input_info())
        ctk.CTkButton(
            row_in, text="Examinar", width=90, command=self._browse_input
        ).pack(side="right")

        self.input_info = ctk.CTkLabel(
            fr_in, text="", font=("", 11), text_color="gray"
        )
        self.input_info.pack(anchor="w", padx=10, pady=(0, 8))

        # — Output folder —
        fr_out = ctk.CTkFrame(self)
        fr_out.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(fr_out, text="Carpeta de destino:", font=("", 12, "bold")).pack(
            anchor="w", padx=10, pady=(8, 2)
        )
        row_out = ctk.CTkFrame(fr_out, fg_color="transparent")
        row_out.pack(fill="x", padx=10, pady=(0, 8))

        self.output_var = ctk.StringVar()
        ctk.CTkEntry(
            row_out,
            textvariable=self.output_var,
            placeholder_text="Ruta de salida...",
        ).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            row_out, text="Examinar", width=90, command=self._browse_output
        ).pack(side="right")

        # — Options —
        fr_opts = ctk.CTkFrame(self)
        fr_opts.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(fr_opts, text="Opciones:", font=("", 12, "bold")).pack(
            anchor="w", padx=10, pady=(8, 0)
        )

        # -- Separator top --
        ctk.CTkFrame(fr_opts, height=1, fg_color=("gray75", "gray35")).pack(
            fill="x", padx=12, pady=(4, 6)
        )

        # -- Dropdowns/slider section --
        controls = ctk.CTkFrame(fr_opts, fg_color="transparent")
        controls.pack(fill="x", padx=10, pady=(0, 4))

        # Row: Formato + Subsampling
        row_top = ctk.CTkFrame(controls, fg_color="transparent")
        row_top.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(row_top, text="Formato:").pack(side="left", padx=(0, 5))
        self.format_var = ctk.StringVar(value="JPEG")
        self.format_menu = ctk.CTkOptionMenu(
            row_top,
            variable=self.format_var,
            values=["JPEG", "WebP", "AVIF", "PNG", "TIFF"],
            width=100,
            command=self._on_format_change,
        )
        self.format_menu.pack(side="left", padx=(0, 4))
        info_icon(row_top, "formato").pack(side="left", padx=(0, 20))

        ctk.CTkLabel(row_top, text="Subsampling:").pack(side="left", padx=(0, 5))
        self.subsampling_var = ctk.StringVar(value="4:2:0")
        self.subsampling_menu = ctk.CTkOptionMenu(
            row_top,
            variable=self.subsampling_var,
            values=["4:2:0", "4:2:2", "4:4:4"],
            width=80,
        )
        self.subsampling_menu.pack(side="left", padx=(0, 4))
        info_icon(row_top, "subsampling").pack(side="left")

        # Row: Calidad
        row_qual = ctk.CTkFrame(controls, fg_color="transparent")
        row_qual.pack(fill="x", pady=(0, 4))
        ctk.CTkLabel(row_qual, text="Calidad:").pack(side="left", padx=(0, 5))
        self.quality_var = ctk.IntVar(value=50)
        self.quality_slider = ctk.CTkSlider(
            row_qual,
            from_=10,
            to=100,
            number_of_steps=18,
            variable=self.quality_var,
            width=200,
            command=self._on_quality_change,
        )
        self.quality_slider.pack(side="left", padx=(0, 5))
        self.quality_label = ctk.CTkLabel(row_qual, text="50", width=24)
        self.quality_label.pack(side="left", padx=(0, 4))
        info_icon(row_qual, "calidad").pack(side="left")

        # -- Separator --
        ctk.CTkFrame(fr_opts, height=1, fg_color=("gray75", "gray35")).pack(
            fill="x", padx=12, pady=(4, 6)
        )

        # -- Checkboxes section --
        checks = ctk.CTkFrame(fr_opts, fg_color="transparent")
        checks.pack(fill="x", padx=10, pady=(0, 8))
        checks.columnconfigure(0, weight=1)
        checks.columnconfigure(1, weight=1)

        CHK_PAD = (0, 6)

        # Mantener formato original + ⓘ
        chk0_l = ctk.CTkFrame(checks, fg_color="transparent")
        chk0_l.grid(row=0, column=0, sticky="w", pady=CHK_PAD)
        self.keep_format_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            chk0_l,
            text="Mantener formato original",
            variable=self.keep_format_var,
            command=self._on_keep_format_change,
        ).pack(side="left", padx=(0, 4))
        info_icon(chk0_l, "mantener_formato").pack(side="left")

        # Preservar metadatos + ⓘ
        chk0_r = ctk.CTkFrame(checks, fg_color="transparent")
        chk0_r.grid(row=0, column=1, sticky="w", pady=CHK_PAD)
        self.metadata_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            chk0_r,
            text="Preservar metadatos",
            variable=self.metadata_var,
        ).pack(side="left", padx=(0, 4))
        info_icon(chk0_r, "preservar_metadatos").pack(side="left")

        # Multiprocesado + ⓘ
        chk1_l = ctk.CTkFrame(checks, fg_color="transparent")
        chk1_l.grid(row=1, column=0, sticky="w", pady=CHK_PAD)
        self.multiproc_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            chk1_l,
            text="Multiprocesado",
            variable=self.multiproc_var,
        ).pack(side="left", padx=(0, 4))
        info_icon(chk1_l, "multiprocesado").pack(side="left")

        # Solo impares + ⓘ
        chk1_r = ctk.CTkFrame(checks, fg_color="transparent")
        chk1_r.grid(row=1, column=1, sticky="w", pady=CHK_PAD)
        self.odd_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            chk1_r,
            text="Solo imágenes impares",
            variable=self.odd_var,
            command=self._update_input_info,
        ).pack(side="left", padx=(0, 4))
        info_icon(chk1_r, "solo_impares").pack(side="left")

        # — Compress button —
        self.compress_btn = ctk.CTkButton(
            self,
            text="Comprimir",
            height=40,
            font=("", 14, "bold"),
            command=self._start_compression,
        )
        self.compress_btn.pack(fill="x", padx=15, pady=(10, 8))

        # — Progress —
        self.progress = ctk.CTkProgressBar(self)
        self.progress.pack(fill="x", padx=15, pady=(0, 4))
        self.progress.set(0)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=15, pady=(0, 8))

        self.status_label = ctk.CTkLabel(bottom, text="", font=("", 11))
        self.status_label.pack(side="left")

        ctk.CTkButton(
            bottom,
            text="About",
            width=60,
            height=26,
            font=("", 11),
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            text_color="gray",
            command=self._show_about,
        ).pack(side="right")

    def _show_about(self):
        about = ctk.CTkToplevel(self)
        about.title("Acerca de Compresor de Imágenes")
        about.geometry("320x200")
        about.resizable(False, False)
        about.transient(self)
        about.grab_set()

        icon_path = Path(__file__).parent / "icon.png"
        if icon_path.exists():
            icon_img = ctk.CTkImage(Image.open(icon_path), size=(64, 64))
            ctk.CTkLabel(about, image=icon_img, text="").pack(pady=(20, 8))
        else:
            ctk.CTkLabel(about, text="").pack(pady=(20, 0))

        ctk.CTkLabel(
            about, text="Compresor de Imágenes", font=("", 16, "bold")
        ).pack()
        ctk.CTkLabel(about, text=f"Versión {VERSION}", font=("", 12)).pack(pady=(2, 0))
        ctk.CTkLabel(
            about,
            text=f"Desarrollado por {AUTHOR}",
            font=("", 12),
            text_color="gray",
        ).pack(pady=(2, 0))

    # ── Callbacks ──────────────────────────────────────────────────────

    def _on_quality_change(self, value):
        self.quality_label.configure(text=str(int(value)))

    def _on_format_change(self, fmt):
        if fmt == "PNG":
            self.quality_slider.configure(state="disabled")
            self.quality_label.configure(text="—")
        else:
            self.quality_slider.configure(state="normal")
            self._on_quality_change(self.quality_var.get())

        if fmt == "JPEG":
            self.subsampling_menu.configure(state="normal")
        else:
            self.subsampling_menu.configure(state="disabled")

    def _on_keep_format_change(self):
        if self.keep_format_var.get():
            self.format_menu.configure(state="disabled")
            self.subsampling_menu.configure(state="normal")
        else:
            self.format_menu.configure(state="normal")
            self._on_format_change(self.format_var.get())

    def _browse_input(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta de origen")
        if path:
            self.input_var.set(path)
            self._update_input_info()

    def _browse_output(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta de destino")
        if path:
            self.output_var.set(path)

    # ── Helpers ────────────────────────────────────────────────────────

    def _get_source_images(self) -> list[Path]:
        input_path = self.input_var.get().strip()
        if not input_path:
            return []
        src = Path(input_path)
        if not src.is_dir():
            return []

        images = sorted(
            f
            for f in src.rglob("*")
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        )

        if self.odd_var.get():
            images = images[::2]

        return images

    def _update_input_info(self):
        images = self._get_source_images()
        if images:
            total_mb = sum(f.stat().st_size for f in images) / (1024 * 1024)
            exts = sorted({f.suffix.lower() for f in images})
            self.input_info.configure(
                text=f"{len(images)} imágenes encontradas ({total_mb:.1f} MB) — Formatos: {', '.join(exts)}"
            )
        else:
            text = (
                "No se encontraron imágenes"
                if self.input_var.get().strip()
                else ""
            )
            self.input_info.configure(text=text)

    # ── Compression ───────────────────────────────────────────────────

    def _start_compression(self):
        if self._processing:
            return

        images = self._get_source_images()
        if not images:
            messagebox.showwarning(
                "Aviso", "No se encontraron imágenes en la carpeta de origen."
            )
            return

        output_path = self.output_var.get().strip()
        if not output_path:
            messagebox.showwarning("Aviso", "Selecciona una carpeta de destino.")
            return

        out_dir = Path(output_path)
        out_dir.mkdir(parents=True, exist_ok=True)

        quality = self.quality_var.get()
        preserve_metadata = self.metadata_var.get()
        keep_format = self.keep_format_var.get()
        subsampling = self.subsampling_var.get()
        use_multiproc = self.multiproc_var.get()
        fmt = self.format_var.get()
        src_root = Path(self.input_var.get().strip())

        tasks = []
        for img_path in images:
            rel = img_path.relative_to(src_root)
            if keep_format:
                img_fmt = EXTENSION_TO_FORMAT.get(img_path.suffix.lower(), "JPEG")
                dst = out_dir / rel
            else:
                img_fmt = fmt
                dst = out_dir / rel.with_suffix(FORMAT_EXTENSIONS[fmt])
            dst.parent.mkdir(parents=True, exist_ok=True)
            tasks.append((str(img_path), str(dst), img_fmt, quality, preserve_metadata, subsampling))

        self._processing = True
        self.compress_btn.configure(state="disabled")
        self.progress.set(0)
        self.status_label.configure(text=f"Comprimiendo 0/{len(tasks)}...")

        thread = threading.Thread(
            target=self._run_compression, args=(tasks, use_multiproc), daemon=True
        )
        thread.start()

    def _run_compression(self, tasks: list, use_multiproc: bool):
        total = len(tasks)
        completed = 0
        total_original = 0
        total_new = 0
        errors = []
        workers = min(os.cpu_count() or 4, total) if use_multiproc else 1

        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(compress_image, *t): t for t in tasks}
            for future in as_completed(futures):
                try:
                    _, orig_size, new_size = future.result()
                    total_original += orig_size
                    total_new += new_size
                except Exception as e:
                    src = Path(futures[future][0]).name
                    errors.append(f"{src}: {e}")

                completed += 1
                self.after(0, self._update_progress, completed, total)

        reduction = (1 - total_new / total_original) * 100 if total_original > 0 else 0
        orig_mb = total_original / (1024 * 1024)
        new_mb = total_new / (1024 * 1024)
        self.after(
            0, self._compression_done, total, orig_mb, new_mb, reduction, errors
        )

    def _update_progress(self, completed: int, total: int):
        self.progress.set(completed / total)
        self.status_label.configure(text=f"Comprimiendo {completed}/{total}...")

    def _compression_done(
        self,
        total: int,
        orig_mb: float,
        new_mb: float,
        reduction: float,
        errors: list[str],
    ):
        self._processing = False
        self.compress_btn.configure(state="normal")
        self.progress.set(1)

        ok_count = total - len(errors)
        self.status_label.configure(
            text=f"Completado: {ok_count}/{total} imágenes — {orig_mb:.1f} MB → {new_mb:.1f} MB ({reduction:.1f}% reducción)"
        )

        if errors:
            error_detail = "\n".join(errors[:20])
            if len(errors) > 20:
                error_detail += f"\n... y {len(errors) - 20} errores más."
            messagebox.showwarning(
                "Completado con errores",
                f"{ok_count} de {total} imágenes comprimidas.\n"
                f"{orig_mb:.1f} MB → {new_mb:.1f} MB ({reduction:.1f}% reducción)\n\n"
                f"Errores ({len(errors)}):\n{error_detail}",
            )
        else:
            messagebox.showinfo(
                "Completado",
                f"{total} imágenes comprimidas.\n"
                f"{orig_mb:.1f} MB → {new_mb:.1f} MB ({reduction:.1f}% reducción)",
            )


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = App()
    app.mainloop()
