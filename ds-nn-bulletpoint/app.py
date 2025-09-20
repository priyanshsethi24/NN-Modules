from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from common.logs import logger
from routes.module_router import router
import uvicorn
from dotenv import load_dotenv
import os

load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Get host and port from environment variables, use defaults if not set
app_host = os.getenv("APP_HOST", "127.0.0.1")  # Default host
app_port = os.getenv("APP_PORT", 8000)  # Default port

# Register routes
app.include_router(router)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def hello():
    logger.info('--- Started app ---')
    return {
        "message": "Hello, World!",
        "usage": [
            "/check_format"
        ]
    }

if __name__ == '__main__':
    # Convert app_port to int, in case it's fetched as a string
    uvicorn.run(app, host=app_host, port=int(app_port))
    logger.info("--- Started app.py ---")
