FROM arm32v7/python:3.11-alpine

#RUN apk add --no-cache build-base libffi-dev cmake

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install precompiled numpy and pandas wheels for ARM architecture
#RUN pip install --no-cache-dir numpy pandas

# Install any needed dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that your FastAPI app will run on
EXPOSE 8000

# Command to run the FastAPI app using Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
