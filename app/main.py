from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models.database import init_db
from app.api.v1 import ingest, query, generate
from app.api.admin import apps, clients, providers, usage

app = FastAPI(
    title="Black Box API",
    description="Multi-tenant AI engine for Augmex products",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_db()


# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "service": "blackbox-api"}


# API v1 routes
app.include_router(ingest.router, prefix="/v1", tags=["ingestion"])
app.include_router(query.router, prefix="/v1", tags=["query"])
app.include_router(generate.router, prefix="/v1", tags=["generation"])

# Admin routes
app.include_router(apps.router, prefix="/admin/v1", tags=["admin-apps"])
app.include_router(clients.router, prefix="/admin/v1", tags=["admin-clients"])
app.include_router(providers.router, prefix="/admin/v1", tags=["admin-providers"])
app.include_router(usage.router, prefix="/admin/v1", tags=["admin-usage"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)