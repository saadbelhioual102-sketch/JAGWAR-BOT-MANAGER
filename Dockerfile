# Use Python 3.11 as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY bot_template/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir flask psutil aiohttp requests httpx google protobuf pycryptodome PyJWT urllib3 protobuf-decoder pytz cfonts huggingface_hub

# Copy the rest of the application
COPY . .

# Expose the port Hugging Face expects (7860)
EXPOSE 7860

# Set environment variable for Flask to run on 7860
ENV SERVER_PORT=7860

# Command to run the application
CMD ["python", "host/bot.py"]
