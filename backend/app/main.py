from fastapi import FastAPI
from app.database import engine, Base
# Importamos nuestro nuevo router
from app.routers import auth

# Creamos las tablas si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(title="BioGaMed API")

# Enganchamos el router a la app principal
app.include_router(auth.router)

@app.get("/")
def read_root():
    return {"message": "¡Bienvenido a la API de BioGaMed!"}
