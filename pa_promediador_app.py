import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# =========================
# Núcleo de negocio
# =========================

@dataclass
class AliasRule:
    origen: str
    destino: str


@dataclass
class AppState:
    data: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())
    aliases: Dict[str, str] = field(default_factory=dict)
    archivos: List[str] = field(default_factory=list)


class PAPromediador:
    REQUIRED_COLS = ["ID", "Y", "X", "Z", "DESC", "archivo"]

    @staticmethod
    def leer_txt(path: str) -> pd.DataFrame:
        rows = []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for n_linea, raw in enumerate(f, start=1):
                line = raw.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.split(",")]
                if len(parts) != 5:
                    # Ignora líneas mal formadas, pero conserva trazabilidad si luego se requiere log.
                    continue

                punto_id, y, x, z, desc = parts

                # Los puntos de apoyo reales vienen como PA-xx / PAxx. Se ignoran AM u otros descriptores,
                # pero esto puede ajustarse si el usuario luego quiere incluirlos.
                if not PAPromediador.es_pa(desc):
                    continue

                try:
                    rows.append({
                        "ID": punto_id,
                        "Y": float(y),
                        "X": float(x),
                        "Z": float(z),
                        "DESC": desc,
                        "archivo": os.path.basename(path),
                        "linea": n_linea,
                    })
                except ValueError:
                    continue

        df = pd.DataFrame(rows)
        if df.empty:
            return pd.DataFrame(columns=["ID", "Y", "X", "Z", "DESC", "archivo", "linea"])

        return df

    @staticmethod
    def es_pa(desc: str) -> bool:
        return bool(re.match(r"^PA[-_ ]?\d+$", str(desc).strip(), flags=re.IGNORECASE))

    @staticmethod
    def normalizar_descriptor(desc: str) -> str:
        """
        Convierte variantes equivalentes a un formato canónico.
        Ejemplos:
        - PA-01  -> PA01
        - pa01   -> PA01
        - PA001  -> PA01
        - PA 1   -> PA01
        """
        s = str(desc).strip().upper()
        s = s.replace("_", "-").replace(" ", "")
        m = re.match(r"^PA-?(\d+)$", s)
        if not m:
            return s
        n = int(m.group(1))
        return f"PA{n:02d}"

    @staticmethod
    def aplicar_alias(df: pd.DataFrame, aliases: Dict[str, str]) -> pd.DataFrame:
        if df.empty:
            return df.copy()

        out = df.copy()
        out["DESC_NORMALIZADO"] = out["DESC"].apply(PAPromediador.normalizar_descriptor)

        # Normalizar también los alias ingresados por el usuario.
        aliases_norm = {
            PAPromediador.normalizar_descriptor(k): PAPromediador.normalizar_descriptor(v)
            for k, v in aliases.items()
            if str(k).strip() and str(v).strip()
        }
        out["DESC_FINAL"] = out["DESC_NORMALIZADO"].replace(aliases_norm)
        return out

    @staticmethod
    def promediar(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=[
                "DESC_FINAL", "Y_PROM", "X_PROM", "Z_PROM", "N", "DESCRIPTORES_ORIGEN", "ARCHIVOS"
            ])

        resumen = (
            df.groupby("DESC_FINAL", as_index=False)
              .agg(
                  Y_PROM=("Y", "mean"),
                  X_PROM=("X", "mean"),
                  Z_PROM=("Z", "mean"),
                  N=("DESC", "count"),
                  DESCRIPTORES_ORIGEN=("DESC", lambda s: ", ".join(sorted(set(map(str, s))))),
                  ARCHIVOS=("archivo", lambda s: ", ".join(sorted(set(map(str, s)))))
              )
              .sort_values("DESC_FINAL")
              .reset_index(drop=True)
        )
        return resumen

    @staticmethod
    def detalle_por_punto(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=["archivo", "linea", "ID", "Y", "X", "Z", "DESC", "DESC_NORMALIZADO", "DESC_FINAL"])
        cols = [c for c in ["archivo", "linea", "ID", "Y", "X", "Z", "DESC", "DESC_NORMALIZADO", "DESC_FINAL"] if c in df.columns]
        return df[cols].sort_values(["DESC_FINAL", "archivo", "linea"]).reset_index(drop=True)

    @staticmethod
    def exportar_excel(resumen: pd.DataFrame, detalle: pd.DataFrame, ruta_salida: str) -> None:
        with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
            resumen.to_excel(writer, sheet_name="Promedios", index=False)
            detalle.to_excel(writer, sheet_name="Detalle", index=False)

            # Ajuste básico de ancho de columnas
            for sheet_name, df in {"Promedios": resumen, "Detalle": detalle}.items():
                ws = writer.book[sheet_name]
                for i, col in enumerate(df.columns, start=1):
                    max_len = max([len(str(col))] + [len(str(v)) for v in df[col].astype(str).head(500)])
                    ws.column_dimensions[chr(64+i)].width = min(max(max_len + 2, 12), 40)

    @staticmethod
    def guardar_aliases(path: str, aliases: Dict[str, str]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(aliases, f, ensure_ascii=False, indent=2)

    @staticmethod
    def cargar_aliases(path: str) -> Dict[str, str]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {str(k): str(v) for k, v in data.items()}


# =========================
# Interfaz Tkinter
# =========================

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Promediador de Puntos de Apoyo (PA)")
        self.geometry("1180x720")
        self.minsize(1080, 680)

        self.state = AppState()
        self.logic = PAPromediador()

        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Button(top, text="Cargar archivos .txt", command=self.cargar_archivos).pack(side="left", padx=4)
        ttk.Button(top, text="Cargar aliases JSON", command=self.cargar_aliases).pack(side="left", padx=4)
        ttk.Button(top, text="Guardar aliases JSON", command=self.guardar_aliases).pack(side="left", padx=4)
        ttk.Button(top, text="Procesar / Promediar", command=self.procesar).pack(side="left", padx=4)
        ttk.Button(top, text="Exportar Excel", command=self.exportar_excel).pack(side="left", padx=4)
        ttk.Button(top, text="Limpiar", command=self.limpiar).pack(side="left", padx=4)

        main = ttk.Panedwindow(self, orient="horizontal")
        main.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.Frame(main, padding=8)
        right = ttk.Frame(main, padding=8)
        main.add(left, weight=1)
        main.add(right, weight=3)

        ttk.Label(left, text="Archivos cargados").pack(anchor="w")
        self.lst_archivos = tk.Listbox(left, height=10)
        self.lst_archivos.pack(fill="x", pady=(4, 10))

        alias_box = ttk.LabelFrame(left, text="Aliases de descriptor", padding=8)
        alias_box.pack(fill="both", expand=True)

        frm_alias = ttk.Frame(alias_box)
        frm_alias.pack(fill="x", pady=(0, 8))
        ttk.Label(frm_alias, text="Origen").grid(row=0, column=0, sticky="w")
        ttk.Label(frm_alias, text="Destino").grid(row=0, column=1, sticky="w")

        self.ent_origen = ttk.Entry(frm_alias)
        self.ent_destino = ttk.Entry(frm_alias)
        self.ent_origen.grid(row=1, column=0, sticky="ew", padx=(0, 4))
        self.ent_destino.grid(row=1, column=1, sticky="ew", padx=(4, 4))
        ttk.Button(frm_alias, text="Agregar alias", command=self.agregar_alias).grid(row=1, column=2, padx=(4, 0))
        frm_alias.columnconfigure(0, weight=1)
        frm_alias.columnconfigure(1, weight=1)

        self.tree_alias = ttk.Treeview(alias_box, columns=("origen", "destino"), show="headings", height=12)
        self.tree_alias.heading("origen", text="Origen")
        self.tree_alias.heading("destino", text="Destino")
        self.tree_alias.pack(fill="both", expand=True)
        ttk.Button(alias_box, text="Eliminar alias seleccionado", command=self.eliminar_alias).pack(anchor="e", pady=(8, 0))

        ttk.Label(right, text="Resultado promedio por descriptor").pack(anchor="w")
        self.tree_resumen = ttk.Treeview(right, columns=("desc", "y", "x", "z", "n", "origen", "archivos"), show="headings")
        headers = [
            ("desc", "Descriptor final"),
            ("y", "Y promedio"),
            ("x", "X promedio"),
            ("z", "Z promedio"),
            ("n", "N"),
            ("origen", "Descriptores origen"),
            ("archivos", "Archivos"),
        ]
        for col, txt in headers:
            self.tree_resumen.heading(col, text=txt)
            self.tree_resumen.column(col, width=120 if col in {"desc", "y", "x", "z", "n"} else 220, anchor="center")
        self.tree_resumen.pack(fill="both", expand=True, pady=(4, 10))

        ttk.Label(right, text="Log").pack(anchor="w")
        self.txt_log = tk.Text(right, height=8)
        self.txt_log.pack(fill="x")

    def log(self, msg: str):
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")

    def cargar_archivos(self):
        paths = filedialog.askopenfilenames(filetypes=[("TXT", "*.txt")])
        if not paths:
            return

        dfs = []
        for path in paths:
            df = self.logic.leer_txt(path)
            dfs.append(df)
            self.state.archivos.append(path)
            self.lst_archivos.insert("end", os.path.basename(path))
            self.log(f"Cargado: {os.path.basename(path)} ({len(df)} registros PA válidos)")

        if dfs:
            base = pd.concat([self.state.data] + dfs, ignore_index=True) if not self.state.data.empty else pd.concat(dfs, ignore_index=True)
            self.state.data = base
            self.log(f"Total acumulado: {len(self.state.data)} registros")

    def agregar_alias(self):
        origen = self.ent_origen.get().strip()
        destino = self.ent_destino.get().strip()
        if not origen or not destino:
            messagebox.showwarning("Faltan datos", "Debes ingresar origen y destino.")
            return

        self.state.aliases[origen] = destino
        self.tree_alias.insert("", "end", values=(origen, destino))
        self.log(f"Alias agregado: {origen} -> {destino}")
        self.ent_origen.delete(0, "end")
        self.ent_destino.delete(0, "end")

    def eliminar_alias(self):
        selected = self.tree_alias.selection()
        if not selected:
            return
        for item in selected:
            origen, destino = self.tree_alias.item(item, "values")
            self.tree_alias.delete(item)
            self.state.aliases.pop(origen, None)
            self.log(f"Alias eliminado: {origen} -> {destino}")

    def cargar_aliases(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            aliases = self.logic.cargar_aliases(path)
            self.state.aliases.update(aliases)
            for item in self.tree_alias.get_children():
                self.tree_alias.delete(item)
            for k, v in self.state.aliases.items():
                self.tree_alias.insert("", "end", values=(k, v))
            self.log(f"Aliases cargados desde {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el JSON:\n{e}")

    def guardar_aliases(self):
        if not self.state.aliases:
            messagebox.showinfo("Sin aliases", "No hay aliases para guardar.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], initialfile="aliases_pa.json")
        if not path:
            return
        try:
            self.logic.guardar_aliases(path, self.state.aliases)
            self.log(f"Aliases guardados en {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el JSON:\n{e}")

    def procesar(self):
        if self.state.data.empty:
            messagebox.showwarning("Sin datos", "Primero debes cargar uno o más archivos TXT.")
            return

        procesado = self.logic.aplicar_alias(self.state.data, self.state.aliases)
        resumen = self.logic.promediar(procesado)

        self._resumen = resumen
        self._detalle = self.logic.detalle_por_punto(procesado)

        for item in self.tree_resumen.get_children():
            self.tree_resumen.delete(item)

        for _, row in resumen.iterrows():
            self.tree_resumen.insert(
                "", "end",
                values=(
                    row["DESC_FINAL"],
                    f"{row['Y_PROM']:.4f}",
                    f"{row['X_PROM']:.4f}",
                    f"{row['Z_PROM']:.4f}",
                    int(row["N"]),
                    row["DESCRIPTORES_ORIGEN"],
                    row["ARCHIVOS"],
                )
            )

        self.log(f"Procesamiento completado: {len(resumen)} PA promediados.")

    def exportar_excel(self):
        if not hasattr(self, "_resumen") or self._resumen.empty:
            messagebox.showwarning("Sin resultado", "Primero debes procesar los datos.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile="promedio_pa.xlsx"
        )
        if not path:
            return

        try:
            self.logic.exportar_excel(self._resumen, self._detalle, path)
            self.log(f"Excel exportado: {os.path.basename(path)}")
            messagebox.showinfo("Éxito", "Archivo exportado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar el Excel:\n{e}")

    def limpiar(self):
        self.state = AppState()
        self.lst_archivos.delete(0, "end")
        self.txt_log.delete("1.0", "end")
        for tree in (self.tree_alias, self.tree_resumen):
            for item in tree.get_children():
                tree.delete(item)
        if hasattr(self, "_resumen"):
            del self._resumen
        if hasattr(self, "_detalle"):
            del self._detalle


if __name__ == "__main__":
    app = App()
    app.mainloop()
