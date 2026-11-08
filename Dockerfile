FROM python:3.10-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY backend/ ./backend/
COPY data/ ./data/

# Initialize and seed database during build
RUN python backend/database.py

# Expose port 7860 (Hugging Face default)
EXPOSE 7860

# Run FastAPI app
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
