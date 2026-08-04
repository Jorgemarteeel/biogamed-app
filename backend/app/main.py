from fastapi import FastAPI

app = FastAPI(title="BioGaMed API")

@app.get("/")
def read_root():
    return {"mensaje": "¡Backend de BioGaMed funcionando!"}