# Use the official Ubuntu minimal image as the base
FROM python:3.11-slim 

# Set environment variables to prevent .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Python and necessary system dependencies
# Add CMake, Ninja, and other build tools required to build wheels from source
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev gcc g++ make cmake ninja-build \
    libpq-dev libffi-dev patchelf git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

#COPY wheels /app/wheels

# Install the wheels from the copied directory
#RUN pip3 install --no-cache-dir /app/wheels/*.whl

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies (with CMake and ninja already installed)
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir --prefer-binary -r requirements.txt

# Copy the application code into the container
COPY . .

# Expose the port your app will run on (adjust if necessary)
EXPOSE 8000

# Run the app using Uvicorn (adjust path to your entry point)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
