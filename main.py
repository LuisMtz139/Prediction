from fastapi import FastAPI

app = FastAPI(title="Hello FastAPI", version="1.0.0")


@app.get("/")
def read_root():
    return {"message": "Hola desde el servidor"}
