"""A simple FastAPI application"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from google import genai
from langsmith.run_trees import RunTree
from langsmith.schemas import UsageMetadata
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

    app_context.state.genai_client = genai.Client(
        api_key=settings.GOOGLE_API_KEY,
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

        rt = RunTree(
            name="Gemini Stream Call",
            run_type="llm",
            inputs={"prompt": payload.question},
            extra={
                "metadata": {
                    "ls_model_name": settings.VERTEX_AI_MODEL,
                    "ls_model_type": "llm",
                    "ls_provider": "google_genai",
                    "ls_run_depth": 0,
                    "ls_temperature": 0.7,
                },
                "invocation_params": {
                    "_type": "google_gemini",
                    "candidate_count": 1,
                    "image_config": None,
                    "max_output_tokens": None,
                    "model": settings.VERTEX_AI_MODEL,
                    "stop": None,
                    "temperature": 0.7,
                    "top_k": None,
                    "top_p": None,
                },
                "options": {"streaming": True, "stop": None},
            },
        )
        rt.post()
        genai_client: genai.Client = app.state.genai_client

        full_content = ""
        input_tokens = 0
        output_tokens = 0
        first_token = None
        try:
            async for (
                chunk
            ) in await genai_client.aio.models.generate_content_stream(
                model=settings.VERTEX_AI_MODEL,
                contents=payload.question,
            ):
                if first_token is None:
                    first_token = chunk
                    rt.add_event({"name": "new_token"})

                if chunk.usage_metadata:
                    input_tokens = chunk.usage_metadata.prompt_token_count
                    output_tokens = chunk.usage_metadata.candidates_token_count

                text = chunk.text if chunk.text else ""
                full_content += text

                yield f"data: {text}\n\n"

            yield "data: [DONE]\n\n"

            rt.end(
                outputs={"output": full_content},
                metadata={
                    "usage_metadata": UsageMetadata(
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        total_tokens=input_tokens + output_tokens,
                    ),
                },
            )

            rt.patch()

        except Exception as e:
            print(e)
            rt.end(error=str(e))
            rt.patch()
            yield "data: [ERROR]\n\n"

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
