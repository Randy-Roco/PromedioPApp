from __future__ import annotations

import io
import json
import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd


PA_REGEX = re.compile(r"^PA[-_ ]?\d+$", flags=re.IGNORECASE)


@dataclass
class ExportProfile:
    key: str
    label: str
    filename_suffix: str
    extension: str = ".txt"
    encoding: str = "utf-8"
    include_header: bool = False
    columns: Tuple[str, ...] = ("Y", "X", "Z", "DESC_FINAL")
    rename_map: Optional[Dict[str, str]] = None
    float_decimals: int = 3
    sep: str = ","


EXPORT_PROFILES: Dict[str, ExportProfile] = {
    "civil3d": ExportProfile(
        key="civil3d",
        label="Civil 3D (.txt UTF-8 | Y,X,Z,DESC)",
        filename_suffix="PA_PROMEDIOS_CIVIL3D",
        encoding="utf-8",
        include_header=False,
        columns=("Y", "X", "Z", "DESC_FINAL"),
    ),
    "erdas": ExportProfile(
        key="erdas",
        label="ERDAS (.txt | P,Y,X,Z,DESC)",
        filename_suffix="PA_PROMEDIOS_ERDAS",
        encoding="utf-8",
        include_header=True,
        columns=("P", "Y", "X", "Z", "DESC_FINAL"),
        rename_map={"DESC_FINAL": "DESC"},
    ),
}


class PAPromediador:
    @staticmethod
    def es_pa(desc: str) -> bool:
        return bool(PA_REGEX.match(str(desc).strip()))

    @staticmethod
    def normalizar_descriptor(desc: str) -> str:
        s = str(desc).strip().upper()
        s = s.replace("_", "-").replace(" ", "")
        m = re.match(r"^PA-?(\d+)$", s)
        if not m:
            return s
        n = int(m.group(1))
        return f"PA{n:02d}"

    @staticmethod
    def _parse_line(parts: List[str], path: str, n_linea: int) -> Optional[dict]:
        if len(parts) == 5:
            punto_id, y, x, z, desc = parts
        elif len(parts) == 4:
            punto_id = ""
            y, x, z, desc = parts
        else:
            return None

        if str(desc).strip().upper() == "DESC":
            return None
        if not PAPromediador.es_pa(desc):
            return None

        try:
            return {
                "ID": str(punto_id).strip(),
                "Y": float(str(y).replace(";", "").strip()),
                "X": float(str(x).replace(";", "").strip()),
                "Z": float(str(z).replace(";", "").strip()),
                "DESC": str(desc).strip(),
                "archivo": os.path.basename(path),
                "linea": n_linea,
            }
        except ValueError:
            return None

    @staticmethod
    def leer_txt(path: str) -> pd.DataFrame:
        rows: List[dict] = []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for n_linea, raw in enumerate(f, start=1):
                line = raw.strip()
                if not line:
                    continue
                parts = [p.strip() for p in line.split(",")]
                parsed = PAPromediador._parse_line(parts, path, n_linea)
                if parsed:
                    rows.append(parsed)

        columns = ["ID", "Y", "X", "Z", "DESC", "archivo", "linea"]
        return pd.DataFrame(rows, columns=columns)

    @staticmethod
    def consolidar(paths: Iterable[str]) -> pd.DataFrame:
        frames = [PAPromediador.leer_txt(p) for p in paths]
        frames = [df for df in frames if not df.empty]
        if not frames:
            return pd.DataFrame(columns=["ID", "Y", "X", "Z", "DESC", "archivo", "linea"])
        return pd.concat(frames, ignore_index=True)

    @staticmethod
    def aplicar_alias(df: pd.DataFrame, aliases: Dict[str, str]) -> pd.DataFrame:
        out = df.copy()
        if out.empty:
            out["DESC_NORMALIZADO"] = []
            out["DESC_FINAL"] = []
            return out

        out["DESC_NORMALIZADO"] = out["DESC"].apply(PAPromediador.normalizar_descriptor)
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
                "P", "DESC_FINAL", "Y", "X", "Z", "N", "DESCRIPTORES_ORIGEN", "ARCHIVOS"
            ])

        resumen = (
            df.groupby("DESC_FINAL", as_index=False)
            .agg(
                Y=("Y", "mean"),
                X=("X", "mean"),
                Z=("Z", "mean"),
                N=("DESC", "count"),
                DESCRIPTORES_ORIGEN=("DESC", lambda s: ", ".join(sorted(set(map(str, s))))),
                ARCHIVOS=("archivo", lambda s: ", ".join(sorted(set(map(str, s))))),
            )
            .sort_values("DESC_FINAL")
            .reset_index(drop=True)
        )
        resumen.insert(0, "P", range(1, len(resumen) + 1))
        return resumen

    @staticmethod
    def detalle(df: pd.DataFrame) -> pd.DataFrame:
        cols = [
            "archivo", "linea", "ID", "DESC", "DESC_NORMALIZADO", "DESC_FINAL", "Y", "X", "Z"
        ]
        present = [c for c in cols if c in df.columns]
        return df[present].sort_values(["DESC_FINAL", "archivo", "linea"]).reset_index(drop=True) if not df.empty else pd.DataFrame(columns=present)

    @staticmethod
    def exportar_excel(resumen: pd.DataFrame, detalle: pd.DataFrame, ruta: str) -> None:
        with pd.ExcelWriter(ruta, engine="openpyxl") as writer:
            resumen.to_excel(writer, sheet_name="Promedios", index=False)
            detalle.to_excel(writer, sheet_name="Detalle", index=False)
            for sheet_name, df in {"Promedios": resumen, "Detalle": detalle}.items():
                ws = writer.book[sheet_name]
                for idx, col in enumerate(df.columns, start=1):
                    max_len = max([len(str(col))] + [len(str(v)) for v in df[col].astype(str).head(1000)])
                    ws.column_dimensions[chr(64 + idx)].width = min(max(max_len + 2, 10), 45)

    @staticmethod
    def formatear_txt(resumen: pd.DataFrame, profile_key: str = "civil3d") -> str:
        profile = EXPORT_PROFILES[profile_key]
        df = resumen.copy()
        if df.empty:
            return ""

        if "P" not in df.columns:
            df.insert(0, "P", range(1, len(df) + 1))

        export_df = df.loc[:, list(profile.columns)].copy()
        if profile.rename_map:
            export_df = export_df.rename(columns=profile.rename_map)

        float_cols = [c for c in export_df.columns if c in {"Y", "X", "Z"}]
        for c in float_cols:
            export_df[c] = export_df[c].map(lambda v: f"{float(v):.{profile.float_decimals}f}")

        buffer = io.StringIO()
        export_df.to_csv(
            buffer,
            sep=profile.sep,
            index=False,
            header=profile.include_header,
            lineterminator="\n",
        )
        return buffer.getvalue()

    @staticmethod
    def exportar_txt(resumen: pd.DataFrame, ruta: str, profile_key: str = "civil3d") -> None:
        profile = EXPORT_PROFILES[profile_key]
        contenido = PAPromediador.formatear_txt(resumen, profile_key=profile_key)
        with open(ruta, "w", encoding=profile.encoding, newline="") as f:
            f.write(contenido)

    @staticmethod
    def guardar_aliases(path: str, aliases: Dict[str, str]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(aliases, f, ensure_ascii=False, indent=2)

    @staticmethod
    def cargar_aliases(path: str) -> Dict[str, str]:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {str(k): str(v) for k, v in data.items()}


__all__ = ["PAPromediador", "EXPORT_PROFILES", "ExportProfile"]
