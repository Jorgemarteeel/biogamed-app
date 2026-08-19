from passlib.context import CryptContext

# Configuramos el motor de cifrado usando el algoritmo bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """
    Recibe una contraseña en texto plano y devuelve su versión cifrada (hash).
    """
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compara la contraseña que escribe el usuario con el hash guardado en la BD.
    """
    return pwd_context.verify(plain_password, hashed_password)