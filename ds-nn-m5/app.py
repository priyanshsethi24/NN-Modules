from fastapi import FastAPI
from routes.module_router import router
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Document Format Checker API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add a root endpoint for testing
@app.get("/")
async def root():
    return {"message": "Document Format Checker API is running"}

# Add routes
app.include_router(router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    
    # Get host and port from environment variables with defaults
    host = os.getenv('APP_HOST', '0.0.0.0')
    port = int(os.getenv('APP_PORT', 8000))
    
    uvicorn.run(app, host=host, port=port)
