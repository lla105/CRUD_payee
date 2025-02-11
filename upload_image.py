#upload/main.py
# From : https://tutorial101.blogspot.com/2023/02/fastapi-upload-image.html
from fastapi import FastAPI, File, Form, HTTPException, Path, UploadFile, status, Query
from fastapi.responses import FileResponse, StreamingResponse
import os
from random import randint
import uuid 
from pymongo import MongoClient #connect to pymongo
from typing import Union, Optional
from pydantic import BaseModel
from bson.objectid import ObjectId
import gridfs # to store image in mongodb
from datetime import datetime
#  uvicorn upload_image:app --reload


IMAGEDIR = "images/"

app = FastAPI()

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["CRUD"] #selects or creates a db named "CRUD" in mongodb instance
payments_collection = db["payment_data"] # retrieves/creates a collection inside CRUD db
files_collection = db["fs.files"] #retrieves/creates a collection called 'files' inside CRUD db
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
    if payment_status.lower() not in ["pending", "completed", "due_now", 'overdue']: 
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
        detail="ERROR: Invalid status. Must be pending, completed, or failed")  

    # Ensure status is "completed" and file is uploaded
    if payment_status.lower() != "completed":
        # print('just change the status')
        return 'just update it'

    else: # Request is for status to become 'Completed'
        if not file: # if no file, reject
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ERROR: Evidence file is required for completed payments",
            )
        # accept only PDF, PNG, JPG
        allowed_types = ["image/jpeg", "image/jpeg", "image/png", "application/pdf"]
        if file.content_type.lower() not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ERROR: Only PDF, PNG, and JPG files are allowed",
            )
    return None
        



@app.post("/update-payment/{payment_id}")
async def update_payment(
    payment_id : str = Path(..., description = "Unique payment ID"),
    payment_status: str = Form(..., description="New status of the payment"),  
    file: UploadFile = File(None, description="Required for completing transaction")
):
        response = update_payment_checks(payment_id, payment_status, file) #
        if response: # Valid request that's not "completed". Just update the status.
            payments_collection.update_one(
                {"payment_id": payment_id},
                {"$set": {"payee_payment_status": payment_status.lower()}},
            )
            return {"message": f"Status updated to {payment_status}"}
        # request is to 'completed' and has file.
        contents = await file.read() # read file contents
        file_uuid = str(uuid.uuid4())
        gridfs_obj.put(contents, filename=file.filename, file_uuid=file_uuid)#save uuid as metadata, store file in gridfs
        # file_id = gridfs_obj.put(contents, filename=file.filename)
        print("Request to Complete: Success! (Valid file type)")

        payments_collection.update_one(
            {"payment_id": payment_id},
            {"$set": {"payee_payment_status": payment_status.lower() , "evidence_file_id": file_uuid}},
        )
        
        download_url = f'http://127.0.0.1:8000/download/{file_uuid}'
        return {"message" : "Payment updated successfully.", "download_url": download_url}
        # return {"message": "Payment updated successfully~", "file_id": file.filename}



@app.get("/download/{file_id}")
async def download_file(file_id: str):
    try:
        file_entry = files_collection.find_one({"file_uuid": file_id})
        file_id = ObjectId(file_entry["_id"])  # Ensure it’s an ObjectId
        file = gridfs_obj.get(file_entry['_id'])
        return StreamingResponse(
            file, 
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{file.filename}"'}
        )
    except gridfs.errors.NoFile:
        raise HTTPException(status_code=404, detail="File not found")
    
@app.get("/getpayments/{payment_id}")
def get_payments(payment_id: str):
    try:
        entries = payments_collection.find()
        curDate = datetime.now().date()
        faketoday = datetime(2024, 11, 27,15,15,15).date()
        due_now_payments = []
        overdue_payments = []
        for payment in entries:
            payment_date = payment['payee_due_date'].date()
            if faketoday == payment_date:
                # payment['payee_payment_status'] = 'due_now'
                payments_collection.update_one(
                    {'payment_id' : payment['payment_id']} ,
                    {'$set' : {'payee_payment_status' : 'due_now' } }
                )
                due_now_payments.append( ( payment['payment_id'], payment['payee_email']) )
            elif faketoday < payment_date :
                payments_collection.update_one (
                    {'payment_id' : payment['payment_id']} ,
                    {'$set' : {'payee_payment_status' : 'overdue'}}
                )
                overdue_payments.append( (payment['payment_id'], payment['payee_email']))
        print('updated these: ')
        # for payment in changed_payments:
        #     print('>> ', payment)
        return {'message' : 'Update these: ', 
                'due now': due_now_payments, 
                'overdues' : overdue_payments}
    except Exception as e:
        print(' transaction not found')
        print(' ERROR : ', e)
        raise HTTPException(statuscode=404, detail="Transaction not found")






 
 
