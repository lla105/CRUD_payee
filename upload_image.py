#upload/main.py
# From : https://tutorial101.blogspot.com/2023/02/fastapi-upload-image.html
from fastapi import Body, FastAPI, File, Form, HTTPException, Path, UploadFile, status, Query
from fastapi.responses import FileResponse, StreamingResponse
import os
from random import randint
import uuid 
from pymongo import MongoClient, UpdateOne #connect to pymongo
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
payments_collection = db["test_transaction"] # retrieves/creates a collection inside CRUD db
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
        print('just change the status')
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
        



@app.post("/update-payment-status/{payment_id}")
async def update_payment_status(
    payment_id : str = Path(..., description = "Unique payment ID"),
    payment_status: str = Body(..., description="New status of the payment"),  
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
    
def calculate_tax(mongoObject):
    return mongoObject['total_due']

def filter_search(filters, search):
    print(' search : ', search)
    search_filter = {
        "$or": [
            {'payee_email': {'$regex': search, '$options': 'i'}},
            {'payment_id': {'$regex': search, '$options': 'i'}},
            {'payee_payment_status': {'$regex': search, '$options': 'i'}},
            {'payee_first_name': {'$regex': search, '$options': 'i'}},
            {'payee_last_name': {'$regex': search, '$options': 'i'}}

        ]
    }
    # print(f' SEARCH FILTER : ', type(search_filter))
    filters.update(search_filter)
    print(f' SEARCH FILTER : ', search_filter)
    return filters
def update_status(entries):
    curDate = datetime.now().date()
    faketoday = datetime(2020, 1, 16,15,15,15).date()
    due_now_payments = []
    overdue_payments = []
    update_operations = []
    for payment in entries:
        print('>>>> ', payment)
        payment_date = payment['payee_due_date'].date()
        if payment['payee_payment_status'] == 'completed':
            continue
        if faketoday == payment_date:
            print('111')
            update_operations.append(UpdateOne(
                {'payment_id': payment['payment_id']},
                {'$set': {'payee_payment_status': 'due_now'}}
            ))
            due_now_payments.append( ( payment['payment_id'], payment['payee_email']) )
        elif faketoday > payment_date :
            print('222')
            update_operations.append(UpdateOne(
                {'payment_id': payment['payment_id']},
                {'$set': {'payee_payment_status': 'overdue'}}
            ))
            overdue_payments.append( (payment['payment_id'], payment['payee_email']) )
        else:
            print('333')
            update_operations.append(UpdateOne(
                {'payment_id': payment['payment_id']},
                {'$set': {'payee_payment_status': 'pending'}}
            ))
    return update_operations
        
def bulk_write_changes(update_operations):
    affected_payments = []
    if update_operations:
        return_list = []
        for each in update_operations:
            # return_list.append( each['payment_id'])
            affected_payments.append(each._filter['payment_id'])
        payments_collection.bulk_write(update_operations)
    return affected_payments

@app.get("/getpayments")
def get_payments(
    payment_status: Optional[str] = Query(None),  
    search: Optional[str] = Query(None),
    page: int = 1,
    page_size: int = 20
):
    try:
        filters = {}
        if search:
            print('!!!!!!!!!')
            filters = filter_search(filters, search)
        print('FILTER : ', filters)
        entries = payments_collection.find(filters, {'_id':0}) #filters, and ignore _id(the type was causing issues)
        # print(' ENTRIES : ')
        # for each in entries:
        #     print('===========\n', each)
        update_operations = update_status(entries)
        print(' UPDATE OPERATIONS : ', update_operations)
        affected_payments = bulk_write_changes(update_operations)
        return {'message' : 'Update these: ', 
                # 'due now': due_now_payments, 
                # 'overdues' : overdue_payments,
                'updated payments' : affected_payments
                }
    except Exception as e:
        print(' transaction not found')
        print(' ERROR : ', e)
        raise HTTPException(status_code=404, detail="Transaction not found")

def printPayeeInfo( payment ):
    payee_info = ''
    payeeIdentifications = ['payee_first_name', 'payee_last_name', 'payment_id']
    for i in range(len(payeeIdentifications)):
        payee_info += payment[payeeIdentifications[i]] + ' '
    print(f'Payee info:', payee_info)

#update_payment updates the payment status and total_due
@app.post('/update-payment/{payment_id}')
def update_payment(
    payment_id : str,
    payment_status : str = Query(None),
    newDueDate : str = Query(None)
):
    payment = payments_collection.find_one( {'payment_id' : payment_id })
    printPayeeInfo(payment)
    if not payment:
            raise HTTPException(status_code=404, 
            detail="ERROR: Payment not found/does not exist")
    compare_date(payment)
    recalculateTotalDue(payment)
    return {'update_payment()' : 'testtt'}

def recalculateTotalDue(payment):
    dueAmount = float(payment['due_amount'])
    discountPercent = float(payment['discount_percent'])
    taxPercent = float(payment['tax_percent'])
    totalDue = dueAmount * ( 1- (discountPercent/100))
    totalDue *= 1 + taxPercent/100
    totalDue = round(totalDue,2)
    # print(' total Due : ', totalDue)
    payments_collection.update_many(
        { 'payment_id' : payment['payment_id'] } ,
        {'$set' : {'total_due':totalDue,
                   'discount_percent': discountPercent,
                   'tax_percent': taxPercent,
                   'due_amount' : dueAmount }}
    )

def compare_date(payment):
    dueDate = payment['payee_due_date'].date()
    curDate = datetime.now().date()
    # print(dueDate)
    print(curDate)
    if dueDate < curDate:
        newStatus = 'overdue'
    elif dueDate > curDate:
        newStatus = 'pending'
    else:
        newStatus = 'due_now'
    payments_collection.update_one(
        {'payment_id' : payment['payment_id']},
        {'$set' : {'payee_payment_status' : newStatus.lower()}}
    )
    print(f'Updated status to', newStatus)



 
 
