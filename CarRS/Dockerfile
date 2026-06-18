FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-container.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY car_rental_recommender_core.py .
COPY run_recommendations.py .
COPY run_cleaning_pipeline.py .
COPY pricing_config.json .
COPY settings.json .
COPY components ./components
COPY ["22 - Sheet1.csv", "./22 - Sheet1.csv"]
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh && chmod +x /docker-entrypoint.sh

# Headless CLI — GUI (tkinter) is not supported in this image without X11.
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python run_recommendations.py --distance 10 --duration 2 --top 1 || exit 1

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["recommend", "--distance", "50", "--duration", "3"]
