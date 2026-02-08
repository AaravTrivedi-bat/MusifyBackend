# Use a lightweight Python version to keep it fast and small
FROM python:3.10-slim

# Prevent python from buffering output (so logs appear instantly)
ENV PYTHONUNBUFFERED=1

# Install necessary system tools
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create a non-root user (Security Best Practice)
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

# Copy the rest of the app code
COPY --chown=user . .

# CRITICAL FIX: Listen on Port 8000 (Koyeb's Default)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
