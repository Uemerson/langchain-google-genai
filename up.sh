docker build -t langchain-google-genai -f Dockerfile.dev .
docker run --rm \
    --env-file .env \
    -p 8000:8000 \
    -v "$(pwd)/src:/app/src" \
    langchain-google-genai