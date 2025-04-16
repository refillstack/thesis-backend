FROM python:3.11

# Set working directory
WORKDIR /usr/src/app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables if they are not set
ENV SUPABASE_URL=${SUPABASE_URL:-"https://otkckrxodedjkipgnnqf.supabase.co"}
# Note: SUPABASE_SERVICE_ROLE_KEY must be set at runtime

# Expose the port
EXPOSE ${PORT:-5000}

# Start the application
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-5000}
