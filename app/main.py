import base64

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {"message": "Welcome to Face Recognition API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/image-to-base64")
async def image_to_base64(file: UploadFile = File(...)):
    """
    Convert an uploaded image to base64 string.

    Args:
        file: Image file to convert

    Returns:
        dict: Contains the base64 encoded string and file info
    """
    contents = await file.read()
    base64_encoded = base64.b64encode(contents).decode("utf-8")

    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "base64": base64_encoded,
    }
