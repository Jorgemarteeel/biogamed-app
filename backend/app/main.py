import os
from urllib.parse import urlsplit, urlunsplit

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
# Importamos nuestro nuevo router
from app.routers import inmunoquest, auth, game, questions, subjects, topics
from app.routers import pasapalabra, practice, monitoring, users, question_import, trivial_board, user_import, academic_editions

# Las tablas se gestionan mediante `alembic upgrade head`.

app = FastAPI(title="BioGaMed API")


@app.exception_handler(RequestValidationError)
async def request_validation_error(request: Request, error: RequestValidationError):
    if request.url.path.startswith(("/auth/", "/user-imports/")):
        return JSONResponse({"detail": "La solicitud contiene campos inválidos."}, status_code=422)
    return await request_validation_exception_handler(request, error)

allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
if extra_origin := os.getenv("BIOGAMED_CORS_ORIGIN"):
    allowed_origins.append(extra_origin)
    # Two loopback origins provide independent browser auth storage in the demo.
    parsed = urlsplit(extra_origin)
    if parsed.hostname in {"localhost", "127.0.0.1"}:
        alternate = "127.0.0.1" if parsed.hostname == "localhost" else "localhost"
        netloc = alternate + (f":{parsed.port}" if parsed.port else "")
        allowed_origins.append(urlunsplit((parsed.scheme, netloc, "", "", "")))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enganchamos el router a la app principal
app.include_router(inmunoquest.router)
app.include_router(auth.router)
app.include_router(user_import.router)
app.include_router(academic_editions.router)
app.include_router(topics.router)
app.include_router(subjects.router)
app.include_router(questions.router)
app.include_router(game.router)
app.include_router(pasapalabra.router)
app.include_router(practice.router)
app.include_router(monitoring.router)
app.include_router(users.router)
app.include_router(question_import.router)
app.include_router(question_import.unclassified_router)
app.include_router(trivial_board.router)

@app.get("/")
def read_root():
    return {"message": "¡Bienvenido a la API de BioGaMed!"}
