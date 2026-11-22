FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY analyzer ./analyzer
RUN useradd --create-home --uid 10001 app
USER app
EXPOSE 8001
CMD ["uvicorn", "analyzer.app:app", "--host", "0.0.0.0", "--port", "8001"]
