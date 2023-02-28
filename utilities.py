from datetime import datetime, timedelta
from uuid import uuid4
from env import *
import requests
import hashlib
import json
import jwt



def hash_saz(matn):
    return hashlib.sha256(str(matn).encode()).hexdigest()




def send_sms(phone_number, text):
    reqUrl = "https://api.sms.ir/v1/send/bulk"
    headersList = {
        "X-API-KEY": "ofoWKIvPSd5zgMSFPw8wy2ZexcNteutALn3yka595N3vSRAIF1JhaMNzU5UnPrfI",
        "Content-Type": "application/json" 
    }
    payload = json.dumps({
        "lineNumber": 30007732006181,
        "messageText": text,
        "mobiles": [
            phone_number
        ],
        "sendDateTime": None
    })
    response = requests.request("POST", reqUrl, data=payload,  headers=headersList)
    print(response.text)
    return response.status_code




def generate_code(username):
    if redis_cli.exists(username) == 0:
        code = str(uuid4().int)[:5]
        redis_cli.set(username, code, ex=86400)
        return code
    return False

def check_code(username, code):
    if redis_cli.get(username) == code:
        return True
    return False




def jwt_generator(username):
    expire = (datetime.now() + timedelta(minutes=1)).isoformat()
    token = jwt.encode({"username":username, "expire":expire}, DJANGO_SECRET_KEY, algorithm="HS256")
    return token

def jwt_checker(token):
    data = jwt.decode(token.encode(), DJANGO_SECRET_KEY, algorithms=["HS256"])
    return data



def Auth(jwt_json):
    if datetime.now().isoformat() < jwt_json["expire"]:
        return True
    return False
