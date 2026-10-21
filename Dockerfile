FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV PORT=8501
EXPOSE 8501

CMD python scripts/seed_if_empty.py && streamlit run dashboard.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true
