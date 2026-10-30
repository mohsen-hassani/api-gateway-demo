# syntax=docker/dockerfile:1
# Build context is services/ (so that common/ can be copied in):
#   docker build -f pricing/Dockerfile services
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app
WORKDIR /app
COPY pricing/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY common ./common
COPY pricing/app ./app

# Used by "make test": docker build --target test
FROM base AS test
COPY requirements-test.txt ./requirements-test.txt
RUN pip install --no-cache-dir -r requirements-test.txt
COPY pricing/tests ./tests
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"]

FROM base AS runtime
USER 10001:10001
EXPOSE 8005
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005", "--no-access-log"]
