from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List

from promediopapp.core import PAPromediador

app = FastAPI(title="PromedioPApp API")


class Punto(BaseModel):
    ID: str = ""
    Y: float
    X: float
    Z: float
    DESC: str
    archivo: str = "api"
    linea: int = 0


class ProcesarRequest(BaseModel):
    puntos: List[Punto]
    aliases: Dict[str, str] = {}


@app.get("/")
def root():
    return {"ok": True, "app": "PromedioPApp API"}


@app.post("/procesar")
def procesar(req: ProcesarRequest):
    if not req.puntos:
        raise HTTPException(status_code=400, detail="Debes enviar puntos")
    import pandas as pd
    df = pd.DataFrame([p.model_dump() for p in req.puntos])
    df = PAPromediador.aplicar_alias(df, req.aliases)
    resumen = PAPromediador.promediar(df)
    detalle = PAPromediador.detalle(df)
    return {
        "resumen": resumen.to_dict(orient="records"),
        "detalle": detalle.to_dict(orient="records"),
        "txt_civil3d": PAPromediador.formatear_txt(resumen, "civil3d"),
        "txt_erdas": PAPromediador.formatear_txt(resumen, "erdas"),
    }
