from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base # ¡Esta es la herramienta clave!

# Conexión a la base de datos PostgreSQL dentro de Docker
SQLALCHEMY_DATABASE_URL = "postgresql://admin:adminpassword@db:5432/biogamed"

# Creamos el motor de la base de datos
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Creamos la fábrica de sesiones
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# AQUÍ DECLARAMOS 'Base'. Esto es lo que main.py estaba buscando desesperadamente.
Base = declarative_base()

# Dependencia para obtener la sesión de la base de datos en cada petición
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
