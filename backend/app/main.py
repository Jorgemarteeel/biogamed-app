from fastapi import FastAPI
# Importamos nuestro nuevo router
from app.routers import auth, game, questions, topics

# Las tablas se gestionan mediante `alembic upgrade head`.

app = FastAPI(title="BioGaMed API")

# Enganchamos el router a la app principal
app.include_router(auth.router)
app.include_router(topics.router)
app.include_router(questions.router)
app.include_router(game.router)

@app.get("/")
def read_root():
    return {"message": "¡Bienvenido a la API de BioGaMed!"}
