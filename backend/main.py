from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

app = FastAPI(
    title="FurNet API",
    description="A simple FastAPI backend",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to FurNet API"}

@app.get("/health")
async def health_check():
    """
    General health check endpoint for docker-compose and simple monitoring.
    Returns a simple status indicating the service is healthy.
    """
    return {"status": "healthy"}

@app.get("/health/live")
async def liveness_check():
    """
    Liveness probe endpoint for Kubernetes.
    Indicates if the application is running and should not be restarted.
    """
    return {"status": "alive"}

@app.get("/health/ready")
async def readiness_check():
    """
    Readiness probe endpoint for Kubernetes.
    Indicates if the application is ready to receive traffic.
    This can be extended to check database connections, external services, etc.
    """
    # TODO: Add checks for dependencies (database, external services, etc.)
    # For now, if the app is running, it's ready
    return {"status": "ready"}
