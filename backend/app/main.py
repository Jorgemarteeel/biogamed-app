from fastapi import FastAPI, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Question

# Inicializamos la aplicación FastAPI
app = FastAPI(title="BioGaMed API")

# Ruta básica para comprobar que el servidor está vivo
@app.get("/")
def read_root():
    return {"mensaje": "¡El motor de la API está funcionando perfectamente!"}

# Nuestra primera ruta real: Obtener las preguntas
@app.get("/api/preguntas")
def obtener_preguntas(db: Session = Depends(get_db)):
    # Ejecutamos una consulta SQL encubierta: SELECT * FROM questions;
    preguntas = db.scalars(select(Question)).all()
    return preguntas