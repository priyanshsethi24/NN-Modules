from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.module_router import router
import uvicorn
from scripts.link_extractor import LinkExtractorFactory, LinkExtractorService
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = FastAPI(title="Link Extractor API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Link Extractor API is running"}

if __name__ == "__main__":
    # Get host and port from environment variables
    host = os.getenv('APP_HOST', '0.0.0.0')
    port = int(os.getenv('APP_PORT', 5000))
    
    uvicorn.run(app, host=host, port=port)
