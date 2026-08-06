import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Obtenemos la URL de la base de datos desde las variables de entorno
# (Las definimos previamente en tu docker-compose.yml)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:adminpassword@localhost:5432/biogamed"
)

# Motor de la base de datos
engine = create_engine(DATABASE_URL)

# Fábrica de sesiones para interactuar con la base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependencia para obtener la sesión en los endpoints de FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()