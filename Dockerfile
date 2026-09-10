FROM python:3.12-slim
WORKDIR /code
RUN pip install --no-cache-dir uv
COPY pyproject.toml ./
RUN uv pip install --system -e ".[dev]"
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
