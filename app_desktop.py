from __future__ import annotations

import os
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional

import pandas as pd

from promediopapp.core import EXPORT_PROFILES, PAPromediador


@dataclass
class AppState:
    archivos: List[str] = field(default_factory=list)
    aliases: Dict[str, str] = field(default_factory=dict)
    detalle: pd.DataFrame = field(default_factory=pd.DataFrame)
    resumen: pd.DataFrame = field(default_factory=pd.DataFrame)


class EditableTreeview(ttk.Treeview):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._entry: Optional[ttk.Entry] = None
        self.bind("<Double-1>", self._begin_edit)

    def _begin_edit(self, event):
        region = self.identify("region", event.x, event.y)
        if region != "cell":
            return
        rowid = self.identify_row(event.y)
        column = self.identify_column(event.x)
        if not rowid or column == "#0":
            return

        x, y, width, height = self.bbox(rowid, column)
        value = self.set(rowid, column)
        self._entry = ttk.Entry(self)
        self._entry.place(x=x, y=y, width=width, height=height)
        self._entry.insert(0, value)
        self._entry.focus()
        self._entry.bind("<Return>", lambda e: self._save_edit(rowid, column))
        self._entry.bind("<FocusOut>", lambda e: self._save_edit(rowid, column))

    def _save_edit(self, rowid, column):
        if not self._entry:
            return
        self.set(rowid, column, self._entry.get())
        self._entry.destroy()
        self._entry = None
        self.event_generate("<<CellEdited>>")


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PromedioPApp | Promediador de Puntos de Apoyo")
        self.geometry("1380x820")
        self.minsize(1240, 720)
        self.state = AppState()
        self.logic = PAPromediador()
        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Button(top, text="Cargar .txt", command=self.cargar_archivos).pack(side="left", padx=4)
        ttk.Button(top, text="Procesar / Promediar", command=self.procesar).pack(side="left", padx=4)
        ttk.Button(top, text="Exportar Excel", command=self.exportar_excel).pack(side="left", padx=4)
        ttk.Button(top, text="Exportar TXT", command=self.exportar_txt).pack(side="left", padx=4)
        ttk.Button(top, text="Cargar aliases", command=self.cargar_aliases).pack(side="left", padx=4)
        ttk.Button(top, text="Guardar aliases", command=self.guardar_aliases).pack(side="left", padx=4)
        ttk.Button(top, text="Limpiar", command=self.limpiar).pack(side="left", padx=4)

        self.export_profile_var = tk.StringVar(value="civil3d")
        ttk.Label(top, text="Formato salida:").pack(side="left", padx=(18, 6))
        ttk.Combobox(
            top,
            textvariable=self.export_profile_var,
            state="readonly",
            width=38,
            values=[f"{k} | {v.label}" for k, v in EXPORT_PROFILES.items()],
        ).pack(side="left")
        self.export_profile_var.set("civil3d | " + EXPORT_PROFILES["civil3d"].label)

        main = ttk.Panedwindow(self, orient="horizontal")
        main.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left = ttk.Frame(main, padding=8)
        right = ttk.Frame(main, padding=8)
        main.add(left, weight=1)
        main.add(right, weight=4)

        ttk.Label(left, text="Archivos cargados").pack(anchor="w")
        self.lst_archivos = tk.Listbox(left, height=8)
        self.lst_archivos.pack(fill="x", pady=(4, 10))

        alias_box = ttk.LabelFrame(left, text="Aliases de descriptor", padding=8)
        alias_box.pack(fill="both", expand=True)
        frm = ttk.Frame(alias_box)
        frm.pack(fill="x", pady=(0, 8))
        ttk.Label(frm, text="Origen").grid(row=0, column=0, sticky="w")
        ttk.Label(frm, text="Destino").grid(row=0, column=1, sticky="w")
        self.ent_origen = ttk.Entry(frm)
        self.ent_destino = ttk.Entry(frm)
        self.ent_origen.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        self.ent_destino.grid(row=1, column=1, sticky="ew", padx=(4, 4))
        ttk.Button(frm, text="Agregar", command=self.agregar_alias).grid(row=1, column=2, padx=(4, 0))
        frm.columnconfigure(0, weight=1)
        frm.columnconfigure(1, weight=1)

        self.tree_alias = ttk.Treeview(alias_box, columns=("origen", "destino"), show="headings", height=14)
        self.tree_alias.heading("origen", text="Origen")
        self.tree_alias.heading("destino", text="Destino")
        self.tree_alias.pack(fill="both", expand=True)
        ttk.Button(alias_box, text="Eliminar alias seleccionado", command=self.eliminar_alias).pack(anchor="e", pady=(8, 0))

        notebook = ttk.Notebook(right)
        notebook.pack(fill="both", expand=True)

        tab_res = ttk.Frame(notebook, padding=6)
        tab_det = ttk.Frame(notebook, padding=6)
        tab_pre = ttk.Frame(notebook, padding=6)
        notebook.add(tab_res, text="Promedios editables")
        notebook.add(tab_det, text="Detalle")
        notebook.add(tab_pre, text="Vista previa TXT")

        self.tree_resumen = EditableTreeview(tab_res, show="headings")
        self.tree_resumen.pack(fill="both", expand=True)
        self.tree_resumen.bind("<<CellEdited>>", self.sincronizar_resumen_desde_tree)

        self.tree_detalle = ttk.Treeview(tab_det, show="headings")
        self.tree_detalle.pack(fill="both", expand=True)

        actions = ttk.Frame(tab_pre)
        actions.pack(fill="x")
        ttk.Button(actions, text="Generar vista previa", command=self.actualizar_preview).pack(side="left")
        ttk.Label(actions, text="Revisa el formato antes de exportar.").pack(side="left", padx=10)

        self.txt_preview = tk.Text(tab_pre, wrap="none")
        self.txt_preview.pack(fill="both", expand=True, pady=(8, 0))

        self.status = tk.StringVar(value="Listo")
        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w").pack(fill="x", side="bottom")

    def perfil_exportacion_key(self) -> str:
        return self.export_profile_var.get().split(" | ", 1)[0]

    def cargar_archivos(self):
        paths = filedialog.askopenfilenames(
            title="Seleccionar archivos TXT",
            filetypes=[("Archivos TXT", "*.txt"), ("Todos", "*.*")],
        )
        if not paths:
            return
        self.state.archivos = list(paths)
        self.lst_archivos.delete(0, tk.END)
        for p in self.state.archivos:
            self.lst_archivos.insert(tk.END, p)
        self.status.set(f"{len(self.state.archivos)} archivo(s) cargado(s)")

    def agregar_alias(self):
        origen = self.ent_origen.get().strip()
        destino = self.ent_destino.get().strip()
        if not origen or not destino:
            messagebox.showwarning("Alias", "Debes ingresar origen y destino.")
            return
        self.state.aliases[origen] = destino
        self.refrescar_aliases()
        self.ent_origen.delete(0, tk.END)
        self.ent_destino.delete(0, tk.END)

    def eliminar_alias(self):
        sel = self.tree_alias.selection()
        if not sel:
            return
        item = self.tree_alias.item(sel[0], "values")
        if item:
            self.state.aliases.pop(item[0], None)
        self.refrescar_aliases()

    def refrescar_aliases(self):
        for item in self.tree_alias.get_children():
            self.tree_alias.delete(item)
        for k, v in sorted(self.state.aliases.items()):
            self.tree_alias.insert("", tk.END, values=(k, v))

    def procesar(self):
        if not self.state.archivos:
            messagebox.showwarning("Procesar", "Primero carga al menos un archivo .txt")
            return
        base = self.logic.consolidar(self.state.archivos)
        detalle = self.logic.aplicar_alias(base, self.state.aliases)
        resumen = self.logic.promediar(detalle)
        self.state.detalle = self.logic.detalle(detalle)
        self.state.resumen = resumen
        self.poblar_tree(self.tree_resumen, self.state.resumen)
        self.poblar_tree(self.tree_detalle, self.state.detalle)
        self.actualizar_preview()
        self.status.set(f"Procesados {len(self.state.detalle)} registros | {len(self.state.resumen)} PA promediados")

    def poblar_tree(self, tree: ttk.Treeview, df: pd.DataFrame):
        tree.delete(*tree.get_children())
        tree["columns"] = list(df.columns)
        for col in df.columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor="center")
        for _, row in df.iterrows():
            vals = []
            for value in row.tolist():
                vals.append(f"{value:.3f}" if isinstance(value, float) else value)
            tree.insert("", tk.END, values=vals)

    def sincronizar_resumen_desde_tree(self, _event=None):
        cols = list(self.tree_resumen["columns"])
        rows = []
        for item in self.tree_resumen.get_children():
            values = list(self.tree_resumen.item(item, "values"))
            rows.append(values)
        if not rows:
            self.state.resumen = pd.DataFrame(columns=cols)
            return
        df = pd.DataFrame(rows, columns=cols)
        for c in ["P", "Y", "X", "Z", "N"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        self.state.resumen = df
        self.actualizar_preview()

    def actualizar_preview(self):
        self.txt_preview.delete("1.0", tk.END)
        if self.state.resumen.empty:
            return
        key = self.perfil_exportacion_key()
        contenido = self.logic.formatear_txt(self.state.resumen, profile_key=key)
        self.txt_preview.insert("1.0", contenido)

    def exportar_excel(self):
        if self.state.resumen.empty:
            messagebox.showwarning("Exportar", "No hay resultados para exportar.")
            return
        path = filedialog.asksaveasfilename(
            title="Guardar Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="PA_PROMEDIOS.xlsx",
        )
        if not path:
            return
        self.logic.exportar_excel(self.state.resumen, self.state.detalle, path)
        messagebox.showinfo("Exportación", f"Excel generado:\n{path}")

    def exportar_txt(self):
        if self.state.resumen.empty:
            messagebox.showwarning("Exportar", "No hay resultados para exportar.")
            return
        key = self.perfil_exportacion_key()
        profile = EXPORT_PROFILES[key]
        path = filedialog.asksaveasfilename(
            title="Guardar TXT",
            defaultextension=profile.extension,
            filetypes=[("TXT", "*.txt")],
            initialfile=f"{profile.filename_suffix}{profile.extension}",
        )
        if not path:
            return
        self.logic.exportar_txt(self.state.resumen, path, profile_key=key)
        messagebox.showinfo("Exportación", f"TXT generado:\n{path}")

    def guardar_aliases(self):
        path = filedialog.asksaveasfilename(
            title="Guardar aliases",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="aliases_pa.json",
        )
        if not path:
            return
        self.logic.guardar_aliases(path, self.state.aliases)
        messagebox.showinfo("Aliases", f"Aliases guardados en:\n{path}")

    def cargar_aliases(self):
        path = filedialog.askopenfilename(
            title="Cargar aliases",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")],
        )
        if not path:
            return
        self.state.aliases = self.logic.cargar_aliases(path)
        self.refrescar_aliases()
        self.status.set("Aliases cargados")

    def limpiar(self):
        self.state = AppState()
        self.lst_archivos.delete(0, tk.END)
        self.refrescar_aliases()
        self.tree_resumen.delete(*self.tree_resumen.get_children())
        self.tree_detalle.delete(*self.tree_detalle.get_children())
        self.txt_preview.delete("1.0", tk.END)
        self.status.set("Limpio")


if __name__ == "__main__":
    App().mainloop()
