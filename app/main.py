from fastapi import FastAPI

app = FastAPI(
    title="BHOODEVI Warehouse Intelligence Platform",
    description="AI-powered Warehouse Demand Intelligence Platform",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "application": "BWIP",
        "message": "Welcome to BHOODEVI Warehouse Intelligence Platform",
        "status": "Running",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "application": "BWIP",
    }