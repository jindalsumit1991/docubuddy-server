import logging
import uuid
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime
from io import BytesIO

from apscheduler.schedulers.background import BackgroundScheduler
from celery import Celery
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends
from google.cloud import storage
from sqlalchemy import asc
from sqlalchemy.orm import Session
from vertexai.generative_models import Image, GenerativeModel

from app.db import get_db, SessionLocal
from app.models import OpdRecord  # Assuming the table is defined in app/models.py

scheduler = BackgroundScheduler()
celery_app = Celery('tasks', broker='redis://localhost:6379/0')

logging.basicConfig(level=logging.INFO)

# Replace with your Google Cloud Storage bucket name
BUCKET_NAME = 'mehar-ocr-test'

# Initialize Google Cloud Storage client
storage_client = storage.Client()


def upload_to_gcs(file: BytesIO, filename: str):
    """Upload a file to Google Cloud Storage."""
    try:
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_file(file)
        logging.info(f">>> Inside upload_to_gcs, returning filename {filename}\n")
        return f"{filename}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload {filename}: {e}")


# Assuming your OpdRecord model has a value_ai column
def get_files_with_null_value_ai(db: Session, limit: int = 10):
    """Fetch records from the database where value_ai is NULL."""
    logging.info(">>> get_files_with_null_value_ai called...\n")

    # Query the database for records with value_ai set to NULL, ordered by created_at in ascending order
    records = (db.query(OpdRecord)
               .filter(OpdRecord.value_ai == None)
               .order_by(asc(OpdRecord.created_at))
               .limit(limit).all())

    logging.info(f">>> get_files_with_null_value_ai: found {records}.\n")
    return records


# Function to process image and update DB as a background task
@celery_app.task
def process_single_file(file_path: str, record_id: uuid, field1: str):
    """Process a single image, call Google Vision API, and update DB."""

    # Create a new database session manually
    db = SessionLocal()  # Use the session factory to create a session

    logging.info(f">>> Processing file {file_path} in background...\n")

    # Fetch the image bytes from the Google Cloud bucket
    image_bytes = fetch_image_from_bucket(BUCKET_NAME, file_path)

    # Create the Image instance for Vertex AI
    vertex_image = Image.from_bytes(image_bytes)

    # Instantiate the Vision model
    vision_model = GenerativeModel("gemini-1.5-flash")

    # Call the Google Vision API with the image and field1
    response = vision_model.generate_content(
        [vertex_image,
         f'''Extract {field1} from the image as a string value without adding any other English text:
            ''']
    )

    # Check if the response was successful
    if response:
        response_dict = response.to_dict()
        extracted_text = response_dict['candidates'][0]['content']['parts'][0]['text']
        confidence_score = process_confidence_score(response_dict)
        logging.info(f">>> Google returned UHID {str(extracted_text)} with confidence score {confidence_score}\n")
        # Update the DB record with the new value_ai value
        logging.info(f"Updating record {record_id} with AI result...\n")
        record = db.query(OpdRecord).filter(OpdRecord.id == record_id).first()
        record.value_ai = str(extracted_text)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        final_path = f"{record.institution_id}/{extracted_text}/{timestamp}"
        move_file_in_bucket(BUCKET_NAME, file_path, final_path)
        record.file_path = final_path
        db.commit()
    db.close()

def process_confidence_score(response, threshold=-0.5):
    try:
        avg_logprobs = response['candidates'][0]['avg_logprobs']

        # Check if the confidence is below the threshold
        if avg_logprobs < threshold:
            print(f"Low confidence: {avg_logprobs}. Consider extra processing.")
        return avg_logprobs
    except (KeyError, IndexError) as e:
        print(f"Error extracting confidence score: {e}")
        return None

# Function to process files from DB
def process_files():
    """Fetch files and offload processing to background tasks."""
    logging.info(">>> Fetching files to process...\n")

    # Create a new database session manually
    db = SessionLocal()  # Use the session factory to create a session

    try:
        # Fetch files with null value_ai
        records = get_files_with_null_value_ai(db)

        # Process each file
        for record in records:
            file_path = record.file_path
            record_id = record.id

            # Process the file and update the DB
            process_single_file.delay(str(file_path), record_id, "UHID")

    except Exception as e:
        logging.error(f"Error processing files: {e}")
    finally:
        db.close()  # Ensure the session is closed after processing


def fetch_image_from_bucket(bucket_name: str, file_path: str):
    """Fetch image bytes from Google Cloud Storage."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_path)

    # Download the image as bytes
    image_bytes = blob.download_as_bytes()

    return image_bytes

# Function to move file in GCS
def move_file_in_bucket(bucket_name: str, source_path: str, destination_path: str):
    """Move a file in Google Cloud Storage by copying and deleting the original."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    # Copy the blob (file) to the new destination
    source_blob = bucket.blob(source_path)
    destination_blob = bucket.copy_blob(source_blob, bucket, destination_path)

    # Delete the original file after the copy
    source_blob.delete()

    logging.info(f"File moved to {destination_path}")
    return destination_blob


# Function to call Google Vision API
def send_to_google_vision(file_path: str, field1: str):
    """Send image to Google Vision API using Vertex AI generative models."""
    bucket_name = BUCKET_NAME  # Set your Google Cloud Storage bucket name

    # Fetch image bytes from Google Cloud Storage
    image_bytes = fetch_image_from_bucket(bucket_name, file_path)

    # Create an instance of the Image class from the bytes
    vertex_image = Image.from_bytes(image_bytes)

    # Instantiate the Vision model (assuming you are using a generative model for image processing)
    vision_model = GenerativeModel("gemini-1.5-flash")

    # Call the Google Vision API (example query)
    response = vision_model.generate_content(
        [vertex_image,
         f'''Extract {field1} from the image as a string value:
			''']
    )

    logging.info(f">>>Received \"{response}\" from google")
    # Process and return the response as needed
    return response


# Scheduler setup
def start_scheduler():
    logging.info(">>> Starting scheduler on app startup...\n")

    # Schedule the process_files job to run every minute
    scheduler.add_job(process_files, 'interval', seconds=30)
    scheduler.start()


def stop_scheduler():
    logging.info(">>> Stopping scheduler on app shutdown...\n")
    scheduler.shutdown()


# Start the scheduler when the FastAPI app starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info(">>> Starting the application with lifespan event...\n")
    start_scheduler()
    yield
    logging.info(">>> Shutting down the application...\n")
    scheduler.shutdown()


# Set the FastAPI lifespan event handler
app = FastAPI(lifespan=lifespan)


@app.post("/upload-images/")
async def upload_images(
        files: list[UploadFile] = File(...),
        username: str = Header(None),
        hospital: int = Header(1),
        db: Session = Depends(get_db)  # Inject session
):
    logging.info(">>> upload-images called..\n")
    """Endpoint to upload multiple image files to Google Cloud Storage."""
    username: str = username,  # Optional username from headers
    hospital: int = hospital,  # Hospital header with int type and default value of 1

    uploaded_files = []
    for file in files:
        # if file.content_type not in ["image/jpeg", "image/png", "application/zip"]:
        #    raise HTTPException(status_code=400, detail="Only JPEG, PNG, or ZIP files are allowed.")

        if file.content_type == "application/zip":
            # Handle ZIP file
            zip_buffer = BytesIO(await file.read())
            with zipfile.ZipFile(zip_buffer, "r") as zip_ref:
                for zip_info in zip_ref.infolist():
                    if zip_info.filename.endswith(('.jpg', '.jpeg', '.png')):
                        with zip_ref.open(zip_info.filename) as img_file:
                            img_buffer = BytesIO(img_file.read())
                            # Upload each image in the zip to GCS
                            gcs_path = upload_to_gcs(img_buffer, zip_info.filename)
                            uploaded_files.append(gcs_path)
                            logging.info(f">>> Uploaded {zip_info.filename}, now saving to DB")
                            # Insert record in database for each uploaded image
                            add_file_to_db(db, username, hospital, gcs_path)
        else:
            # Handle individual images
            file_buffer = BytesIO(await file.read())
            gcs_path = upload_to_gcs(file_buffer, file.filename)
            uploaded_files.append(gcs_path)
            logging.info(f">>> Uploaded {gcs_path}, now saving to DB")
            # Insert record in database for each uploaded image
            add_file_to_db(db, username, hospital, gcs_path)

    return {"uploaded_files": uploaded_files}


def add_file_to_db(db: Session, username: str, institution_id: int, file_path: str):
    """Insert the uploaded file info into the database."""
    logging.info(">>> add_file_to_db called...\n")
    new_record = OpdRecord(
        username=username,  # You can add other fields as needed
        institution_id=institution_id,  # hospital value mapped to institution_id
        file_path=file_path
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)


# Run the server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
