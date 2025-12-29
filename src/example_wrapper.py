"""A simple FastAPI application"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_google_genai import GoogleGenerativeAI
from pydantic import AnyHttpUrl, BaseModel
from pydantic_settings import BaseSettings


class Question(BaseModel):
    """Request payload for asking a question."""

    question: str


class Settings(BaseSettings):
    """Application settings."""

    # API
    BACKEND_CORS_ORIGINS: list[str | AnyHttpUrl] = ["*"]

    # VERTEX AI
    GOOGLE_API_KEY: str
    VERTEX_AI_MODEL: str

    class Config:
        """Pydantic configuration for settings."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@asynccontextmanager
async def lifespan(app_context: FastAPI):
    """Lifespan context manager for the FastAPI application."""

    app_context.state.model = GoogleGenerativeAI(
        google_api_key=settings.GOOGLE_API_KEY,
        model=settings.VERTEX_AI_MODEL,
    )

    yield


settings = Settings()
app = FastAPI(lifespan=lifespan)


if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(origin) for origin in settings.BACKEND_CORS_ORIGINS
        ],
        allow_credentials=True,
        allow_methods=["*"],  # in production, specify allowed methods
        allow_headers=["*"],  # in production, specify allowed headers
    )


@app.post("/ask")
async def ask(payload: Question):
    """Ask a question to the Google Generative AI model."""

    async def generate():

        model: GoogleGenerativeAI = app.state.model

        async for chunk in model.astream(input=payload.question):
            if hasattr(chunk, "usage_metadata"):
                print("Tokens:", chunk.usage_metadata)

            yield f"data: {chunk}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
        media_type="text/event-stream",
    )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok"}, status_code=200)
