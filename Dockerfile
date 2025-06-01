FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m patchright install chromium --with-deps

COPY *.py .

EXPOSE 50051
VOLUME /app/.cache

CMD ["python", "main.py"]