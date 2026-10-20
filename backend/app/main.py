from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Importamos nuestro nuevo router
from app.routers import auth, game, questions, topics

# Las tablas se gestionan mediante `alembic upgrade head`.

app = FastAPI(title="BioGaMed API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enganchamos el router a la app principal
app.include_router(auth.router)
app.include_router(topics.router)
app.include_router(questions.router)
app.include_router(game.router)

@app.get("/")
def read_root():
    return {"message": "¡Bienvenido a la API de BioGaMed!"}
