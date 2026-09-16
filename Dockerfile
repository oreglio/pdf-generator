FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY pdf_generator_ui.py .
COPY generator-pdf-todo-boox-double-details_16.py .

# Create directories for configs
RUN mkdir -p saved_configs

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "pdf_generator_ui.py", "--server.port=8501", "--server.address=0.0.0.0"]