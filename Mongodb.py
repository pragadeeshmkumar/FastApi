from fastapi import FastAPI
from pydantic import BaseModel, Field ,EmailStr
import pymongo
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = FastAPI()

myclient = pymongo.MongoClient("mongodb://localhost:27017/")
db = myclient["expense_managing_system"]

class Expense(BaseModel):
    transaction_type: str = Field(default='UPI')
    transaction_amount: float

def get_next_sequence(name: str):
    result = db['counters'].find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return result['seq']

def send_email(to_email, name, transaction_type, transaction_amount):
    from_email = " "
    password = " "
    html = f"""\
    <html>
        <body>
            <p>Name: {name}</p>
            <p>transaction_type: {transaction_type}</p>
            <p>transaction_amount: {transaction_amount }</p>
        </body>
    </html>"""
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = 'Expense Alert'
    msg.attach(MIMEText(html, 'html'))
    server = smtplib.SMTP('smtp.gmail.com', 25)
    server.ehlo()
    server.starttls()
    server.login(from_email, password)
    server.sendmail(from_email,to_email, msg.as_string())
    server.quit()
     
@app.post('/api/users')
def create_user(name: str,email: EmailStr):
    user_id = get_next_sequence("user_id")
    new_user = {"_id": user_id, "name": name,"email": email}
    result = db['users'].insert_one(new_user)
    return {'message':'user created'}

@app.post('/api/users/{user_id}/accounts')
def create_account(user_id:int,account_type: str):
    account_id = get_next_sequence("account_id")
    new_account = {"_id": account_id,"user_id": user_id,"account_type": account_type}
    result = db['accounts'].insert_one(new_account)
    return {'message':'account created'}

@app.post('/api/users/{user_id}/accounts/{account_id}/expenses')
def create_expense(user_id:int,account_id:int,request: Expense):
    expense_id = get_next_sequence("expense_id")
    new_expense = {"_id": expense_id,"transaction_type":request.transaction_type,"transaction_amount":request.transaction_amount,"user_id": user_id,"account_id": account_id}
    result = db['expenses'].insert_one(new_expense)
    if request.transaction_amount > 500:
        user = db.users.find_one({"_id": user_id})
        send_email(user['email'], user['name'], request.transaction_type, request.transaction_amount)
    return {'message':'expense created'}

@app.get('/api/users/{user_id}/accounts/{account_id}/expenses')
def expense(user_id:int,account_id:int):
    expense= db['expenses'].find({"account_id": account_id,"user_id":user_id})
    return list(expense)
