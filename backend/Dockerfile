FROM python:3.11-slim

WORKDIR /app

# No OS build deps needed: psycopg2-binary ships a precompiled wheel with
# libpq bundled in, and every other requirement has a prebuilt wheel for
# this image's platform too — an apt-get layer here would only add build
# time and a second package source to trust for nothing.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
