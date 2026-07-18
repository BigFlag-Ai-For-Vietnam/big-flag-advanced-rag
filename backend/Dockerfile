FROM python:3.11-slim

# pdfplumber render ảnh cần một số lib hệ thống (ghostscript giúp một số PDF phức tạp).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ghostscript \
    libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-kg.txt ./
RUN pip install --no-cache-dir -r requirements-kg.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
