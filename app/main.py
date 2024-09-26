import logging
import uuid
import zipfile
from contextlib import asynccontextmanager
from datetime import datetime
from io import BytesIO
from typing import List

from apscheduler.schedulers.background import BackgroundScheduler
from celery import Celery
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends
from google.cloud import storage
from sqlalchemy import asc
from sqlalchemy.orm import Session
from vertexai.generative_models import Image, GenerativeModel

from app.config import Settings
from app.db import get_db
from app.models import OpdRecord

# Load configuration
settings = Settings()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize services
scheduler = BackgroundScheduler()
celery_app = Celery('tasks', broker=settings.CELERY_BROKER_URL)
storage_client = storage.Client()

def upload_to_gcs(file: BytesIO, filename: str) -> str:
    """Upload a file to Google Cloud Storage."""
    try:
        bucket = storage_client.bucket(settings.GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_file(file)
        logger.info(f"Uploaded file {filename} to GCS")
        return filename
    except Exception as e:
        logger.error(f"Failed to upload {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload {filename}")

def get_files_with_null_value_ai(db: Session, limit: int = 10) -> [OpdRecord]:
    """Fetch records from the database where value_ai is NULL."""
    return (db.query(OpdRecord)
            .filter(OpdRecord.value_ai == None)
            .order_by(asc(OpdRecord.created_at))
            .limit(limit)
            .all())

@celery_app.task
def process_single_file(file_path: str, record_id: uuid.UUID, field1: str):
    """Process a single image, call Google Vision API, and update DB."""
    with get_db() as db:
        try:
            image_bytes = fetch_image_from_bucket(settings.GCS_BUCKET_NAME, file_path)
            vertex_image = Image.from_bytes(image_bytes)
            vision_model = GenerativeModel(settings.VISION_MODEL_NAME)

            response = vision_model.generate_content([
                vertex_image,
                f"Extract {field1} from the image as a string value without adding any other English text:"
            ])

            if response:
                extracted_text = response.text
                extracted_text = extracted_text.replace(' ', '')

                confidence_score = process_confidence_score(response)
                logger.info(f"Extracted {field1}: {extracted_text}, confidence: {confidence_score}")

                record = db.query(OpdRecord).filter(OpdRecord.id == record_id).first()
                if record:
                    record.value_ai = extracted_text
                    timestamp = datetime.now().strftime("%d-%m-%Y-%H.%M.%S")
                    extension = file_path.split('.')[-1]
                    final_path = f"{record.institution_id}/{extracted_text}/{timestamp}.{extension}"
                    move_file_in_bucket(settings.GCS_BUCKET_NAME, file_path, final_path)
                    record.file_path = final_path
                    db.commit()
                    logger.info(f"Updated record {record_id} with AI result")
                else:
                    logger.warning(f"Record {record_id} not found")
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")

def process_confidence_score(response, threshold: float = -0.5) -> float:
    try:
        avg_logprobs = response.candidates[0].avg_logprobs
        if avg_logprobs < threshold:
            logger.warning(f"Low confidence: {avg_logprobs}. Consider extra processing.")
        return avg_logprobs
    except (KeyError, IndexError) as e:
        logger.error(f"Error extracting confidence score: {str(e)}")
        return None

def process_files():
    """Fetch files and offload processing to background tasks."""
    with get_db() as db:
        try:
            records = get_files_with_null_value_ai(db)
            for record in records:
                process_single_file.delay(str(record.file_path), record.id, "UHID")
        except Exception as e:
            logger.error(f"Error processing files: {str(e)}")

def fetch_image_from_bucket(bucket_name: str, file_path: str) -> bytes:
    """Fetch image bytes from Google Cloud Storage."""
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_path)
    return blob.download_as_bytes()

def move_file_in_bucket(bucket_name: str, source_path: str, destination_path: str):
    """Move a file in Google Cloud Storage by copying and deleting the original."""
    bucket = storage_client.bucket(bucket_name)
    source_blob = bucket.blob(source_path)
    bucket.copy_blob(source_blob, bucket, destination_path)
    source_blob.delete()
    logger.info(f"File moved from {source_path} to {destination_path}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting the application")
    scheduler.add_job(process_files, 'interval', seconds=60)
    scheduler.start()
    yield
    logger.info("Shutting down the application")
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post("/upload-images/")
async def upload_images(
        files: List[UploadFile] = File(...),
        username: str = Header(None),
        hospital: int = Header(1),
        db: Session = Depends(get_db)
):
    """Endpoint to upload multiple image files to Google Cloud Storage."""
    uploaded_files = []
    for file in files:
        if file.content_type == "application/zip":
            zip_buffer = BytesIO(await file.read())
            with zipfile.ZipFile(zip_buffer, "r") as zip_ref:
                for zip_info in zip_ref.infolist():
                    if zip_info.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                        with zip_ref.open(zip_info.filename) as img_file:
                            img_buffer = BytesIO(img_file.read())
                            gcs_path = upload_to_gcs(img_buffer, zip_info.filename)
                            uploaded_files.append(gcs_path)
                            add_file_to_db(db, username, hospital, gcs_path)
        else:
            file_buffer = BytesIO(await file.read())
            gcs_path = upload_to_gcs(file_buffer, file.filename)
            uploaded_files.append(gcs_path)
            add_file_to_db(db, username, hospital, gcs_path)

    return {"uploaded_files": uploaded_files}

def add_file_to_db(db: Session, username: str, institution_id: int, file_path: str):
    """Insert the uploaded file info into the database."""
    new_record = OpdRecord(
        username=username,
        institution_id=institution_id,
        file_path=file_path
    )
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    logger.info(f"Added new record to database: {new_record.id}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
