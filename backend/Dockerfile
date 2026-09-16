FROM python:3.12.10-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg espeak-ng fonts-dejavu-core python3-openshot=0.2.7+dfsg1-4+b1 python3-pyqt5 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY . .
ENV PYTHONUNBUFFERED=1 MEDIA_ROOT=/data
CMD ["uvicorn", "studio.api:app", "--host", "0.0.0.0", "--port", "8000"]
