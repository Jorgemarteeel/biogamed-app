import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Importamos nuestro nuevo router
from app.routers import auth, game, questions, subjects, topics
from app.routers import pasapalabra

# Las tablas se gestionan mediante `alembic upgrade head`.

app = FastAPI(title="BioGaMed API")

allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
if extra_origin := os.getenv("BIOGAMED_CORS_ORIGIN"):
    allowed_origins.append(extra_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enganchamos el router a la app principal
app.include_router(auth.router)
app.include_router(topics.router)
app.include_router(subjects.router)
app.include_router(questions.router)
app.include_router(game.router)
app.include_router(pasapalabra.router)

@app.get("/")
def read_root():
    return {"message": "¡Bienvenido a la API de BioGaMed!"}
