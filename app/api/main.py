from fastapi import FastAPI
from .routes import scan

app = FastAPI(title="Scanzo API", version="0.1.0")
app.include_router(scan.router, prefix="/api", tags=["scan"])

@app.get("/health")
def health():
    return {"status": "ok"}
