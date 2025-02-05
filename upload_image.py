#upload/main.py
# From : https://tutorial101.blogspot.com/2023/02/fastapi-upload-image.html
from fastapi import FastAPI, File, HTTPException, UploadFile, status, Query
from fastapi.responses import FileResponse, StreamingResponse
import os
from random import randint
import uuid
from pymongo import MongoClient #connect to pymongo
from typing import Union, Optional
from pydantic import BaseModel
from bson.objectid import ObjectId
import gridfs # to store image in mongodb

#  uvicorn upload_image:app --reload


IMAGEDIR = "images/"

app = FastAPI()
 #
# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["CRUD"]
payments_collection = db["payment_data"]
files_collection = db["files"]
gridfs_obj = gridfs.GridFS(db) # create a GridFs obj from db

@app.get("/")
def read_root():
    return {"asdf": "zzzzz"}

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def update_payment_checks(payment_id, payment_status, file):
# check if payment exists
    payment = payments_collection.find_one( {"payment_id" : payment_id})
    if not payment:
            raise HTTPException(status_code=404, 
            detail="ERROR: Payment not found/does not exist")
    # check if status is valid or not.
    if payment_status not in ["pending", "completed", "due_now", 'overdue']: 
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
        detail="ERROR: Invalid status. Must be pending, completed, or failed")  

    # Ensure status is "completed" and file is uploaded
    if payment_status.lower() != "completed":
        print('just change the status')
        # return {"message": "Payment updated successfully!", "file_id": str(file_id)}
        # payments_collection.update_one(
        #     {"_id": payment_id},
        #     {"$set": {"payee_payment_status": "payment_status"}},
        # )
        return {"message": "Payment updated successfully!", "file_id": 'None'}

    else: # request to complete 
        if not file: # if no file, reject
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ERROR: Evidence file is required for completed payments",
            )
        # accept only PDF, PNG, JPG
        allowed_types = ["image/jpeg", "image/jpeg", "image/png", "application/pdf"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ERROR: Only PDF, PNG, and JPG files are allowed",
            )
        
@app.post("/update-payment/{payment_id}")
async def update_payment(
    payment_id : str,
    payment_status: str = Query(..., description="New status of the payment"),  
    file: UploadFile = File(None, description="Required for completing transaction")
):
        update_payment_checks(payment_id, payment_status, file)
        contents = await file.read()
        gridfs_obj.put(contents, filename=file.filename)
        print("Request to Complete: Success! (Valid file type)")

        # # store file metadata in mongo
        # file_data = {
        #     "payment_id": payment_id,
        #     "filename": file.filename,
        #     "content_type": file.content_type,
        #     "file_path": file_path,
        # }
        # file_id = files_collection.insert_one(file_data).inserted_id

        # # update payment status
        # payments_collection.update_one(
        #     {"_id": payment_id},
        #     {"$set": {"status": "completed", "evidence_file_id": str(file_id)}},
        # )

        return {"message": "Payment updated successfully~", "file_id": file.filename}

# @app.get("/download-file/{file_id}")
# async def download_file(file_id: str):
#     # Retrieve file metadata from MongoDB
#     file_data = files_collection.find_one({"_id": payment_id})
#     if not file_data:
#         raise HTTPException(status_code=404, detail="File not found")

#     return FileResponse(
#         file_data["file_path"],
#         media_type=file_data["content_type"],
#         filename=file_data["filename"],
#     )


@app.get("/download/{file_id}")
async def download_file(file_id: str):
    try:
        file = gridfs_obj.get(ObjectId(file_id))
        return StreamingResponse(
            file, 
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{file.filename}"'}
        )
    except gridfs.errors.NoFile:
        raise HTTPException(status_code=404, detail="File not found")







 
 
