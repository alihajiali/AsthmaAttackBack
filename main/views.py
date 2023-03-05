from pydoc import doc
from rest_framework.views import APIView
from rest_framework.response import Response
from jdatetime import datetime, timedelta
from rest_framework.status import *
from env import *
from utilities import *

# Create your views here.
class User(APIView):
    def get_user(self, type, username=None):
        query = {"match_all":{}}
        if type != "all":
            query = {"match":{"type.keyword":type}}
        if username is not None:
            query = {"match":{"username":username}}
        user_count = es.count(index="user_2", body={"query":query})["count"]
        users = es.search(index="user_2", query=query, size=user_count)["hits"]["hits"]
        data = []
        for user in users:
            user["_source"].pop("password")
            data.append(user)
        return {"users":data}, HTTP_200_OK

    def get(self, request):
        if Auth(jwt_checker(request.headers["Authorization"].split(" ")[1])):
            data = request.GET
            type = data["type"] if "type" in data else "all"
            username = data["username"] if "username" in data else None
            result = self.get_user(type=type, username=username)
            return Response(result[0], status=result[1])
        return Response({"message":"user is not Autorize"}, status=HTTP_401_UNAUTHORIZED)
    

    def register_user(self, email, password, username, phone_number, type, medical_system_number="", doctors=[]):
        self.email = email
        self.password = password
        self.username = username
        self.phone_number = phone_number
        self.type = type   #  [doctor , bimar]
        self.medical_system_number = medical_system_number
        self.doctors = doctors
        if es.count(index="user_2", body={"query":{"match":{"username.keyword":self.username}}})["count"] == 0:
            if es.count(index="user_2", body={"query":{"match":{"email.keyword":self.email}}})["count"] == 0:
                if es.count(index="user_2", body={"query":{"match":{"phone_number.keyword":self.phone_number}}})["count"] == 0:
                    if self.username not in ["admin", "user", "modir"]:
                        if "@gmail.com" in self.email:
                            if self.phone_number[:2] == "09" and self.phone_number[2:].isdigit() and len(self.phone_number) == 11:
                                if len(self.password) >= 8:
                                    self.data = {
                                        "email":self.email, 
                                        "password":hash_saz(self.password), 
                                        "username":self.username, 
                                        "phone_number": self.phone_number, 
                                        "type": self.type, 
                                        "medical_system_number": self.medical_system_number, 
                                        "doctors": self.doctors, 
                                        "other_data":"", 
                                        "status":"inactive"
                                    }
                                    es.index(index="user_2", document=self.data)
                                    return ({"message":"registered"}, HTTP_201_CREATED)
                                return ({"message":"password does not valid"}, HTTP_406_NOT_ACCEPTABLE)
                            return ({"message":"phone number does not valid"}, HTTP_406_NOT_ACCEPTABLE)
                        return ({"message":"email does not valid"}, HTTP_406_NOT_ACCEPTABLE)
                    return ({"message":"username does not valid"}, HTTP_406_NOT_ACCEPTABLE)
                return ({"message":"phone number is exists"}, HTTP_406_NOT_ACCEPTABLE)
            return ({"message":"email is exists"}, HTTP_406_NOT_ACCEPTABLE)
        return ({"message":"username is exists"}, HTTP_406_NOT_ACCEPTABLE)

    def post(self, request):
        data = request.data
        email = data["email"]
        username = data["username"]
        password = data["password"]
        phone_number = data["phone_number"]
        type = data["type"]
        medical_system_number = data["medical_system_number"]
        doctors = data["doctors"]
        result = self.register_user(email=email, password=password, username=username, phone_number=phone_number, type=type, medical_system_number=medical_system_number, doctors=doctors)
        return Response(result[0], status=result[1])


class ActivePhoneNumver(APIView):
    def get(self, request):
        data = request.GET
        user_data = es.search(index="user_2", query={"match":{"username.keyword":data["username"]}})["hits"]["hits"]
        if len(user_data) == 0:
            return Response({"message":"username not exists"}, status=HTTP_403_FORBIDDEN)
        if check_code(data["username"], data["code"]):
            es.update(index="user_2", id=user_data[0]["_id"], doc={"status":"active"})
            return Response({"message":"user activate"}, status=HTTP_200_OK)
        return Response({"message":"code is wrong"}, status=HTTP_400_BAD_REQUEST)

    def post(self, request):
        username = request.data["username"]
        user_data = es.search(index="user_2", query={"match":{"username.keyword":username}})["hits"]["hits"]
        if len(user_data)>0 and user_data[0]["_source"]["status"] == "inactive": 
            phone_number = user_data[0]["_source"]["phone_number"]
            code = generate_code(username)
            if code:
                send_sms(phone_number, f"کد ارسالی برای شما عبارت است از :\n{code}")
                return Response({"message":"code sended"}, status=HTTP_200_OK)
            return Response({"message":"code is not expire"}, status=HTTP_403_FORBIDDEN)
        return Response({"message":"user is active"}, status=HTTP_403_FORBIDDEN)


class UpdateUser(APIView):
    def get(self, request):
        data = request.GET
        user_data = es.search(index="user_2", query={"match":{"username.keyword":data["username"]}})["hits"]["hits"]
        if len(user_data) == 0:
            return Response({"message":"username not exists"}, status=HTTP_403_FORBIDDEN)
        if check_code(data["username"], data["code"]):
            user_data = {}
            if "new_username" in data:
                user_data[0]["_source"]["username"] = data["new_username"]
            if "new_phone_number" in data:
                user_data[0]["_source"]["phone_number"] = data["new_phone_number"]
            if "new_email" in data:
                user_data[0]["_source"]["email"] = data["new_email"]
            if "new_password" in data:
                user_data[0]["_source"]["password"] = hash_saz(data["new_password"])
            es.update(index="user_2", id=user_data[0]["_id"], doc=user_data[0])
            return Response({"message":"user updated"}, status=HTTP_200_OK)
        return Response({"message":"code is wrong"}, status=HTTP_400_BAD_REQUEST)

    def post(self, request):
        username = request.data["username"]
        user_data = es.search(index="user_2", query={"match":{"username.keyword":username}})["hits"]["hits"]
        if len(user_data)>0:
            phone_number = user_data[0]["_source"]["phone_number"]
            code = generate_code(username)
            if code:
                send_sms(phone_number, f"کد ارسالی برای شما عبارت است از :\n{code}")
                return Response({"message":"code sended"}, status=HTTP_200_OK)
            return Response({"message":"code is not expire"}, status=HTTP_403_FORBIDDEN)
        return Response({"message":"username not exists"}, status=HTTP_403_FORBIDDEN)


class DeleteUser(APIView):
    def get(self, request):
        data = request.GET
        user_data = es.search(index="user_2", query={"match":{"username.keyword":data["username"]}})["hits"]["hits"]
        if len(user_data) == 0:
            return Response({"message":"username not exists"}, status=HTTP_403_FORBIDDEN)
        if check_code(data["username"], data["code"]):
            es.delete(index="user_2", id=user_data[0]["_id"])
            return Response({"message":"user deleted"}, status=HTTP_200_OK)
        return Response({"message":"code is wrong"}, status=HTTP_400_BAD_REQUEST)

    def post(self, request):
        username = request.data["username"]
        user_data = es.search(index="user_2", query={"match":{"username.keyword":username}})["hits"]["hits"]
        if len(user_data)>0 and user_data[0]["_source"]["status"] == "active": 
            phone_number = user_data[0]["_source"]["phone_number"]
            code = generate_code(username)
            if code:
                send_sms(phone_number, f"کد ارسالی برای شما عبارت است از :\n{code}")
                return Response({"message":"code sended"}, status=HTTP_200_OK)
            return Response({"message":"code is not expire"}, status=HTTP_403_FORBIDDEN)
        return Response({"message":"user is active"}, status=HTTP_403_FORBIDDEN)


class Login(APIView):
    def post(self, request):
        data = request.data
        user_data = es.search(index="user_2", query={"match":{"username.keyword":data["username"]}})["hits"]["hits"]
        if user_data:
            if user_data[0]["_source"]["password"] == hash_saz(data["password"]):
                access = jwt_generator(data["username"])
                return Response({"access":access}, status=HTTP_200_OK)
            return Response({"message":"password is wrong"}, status=HTTP_401_UNAUTHORIZED)
        return Response({"message":"user is not exists"}, status=HTTP_401_UNAUTHORIZED)


class AsthmaData(APIView):
    def check(self, user_id, this_percent, days_ago, change_percent):
        gte_time = datetime.now() - timedelta(days=days_ago)
        data = [item["_source"]["percent"] for item in es.search(index="asthma_data", query={"bool":{"must":[
            {"match":{"user_id.keyword":user_id}}, 
            {"range":{"date":{"gte":gte_time}}}
        ]}})["hits"]["hits"]]
        data.append(this_percent)
        if abs(max(data) - min(data)) >= change_percent:
            user_data = es.get(index="user_2", id=user_id)["_source"]
            send_sms(user_data["phone_number"], "با سلام وضعیت آسم شما بحرانی میباشد")


    def get(self, request):
        if Auth(jwt_checker(request.headers["Authorization"].split(" ")[1])):
            user_id = request.GET["user_id"]
            query = {"match":{"user_id.keyword":user_id}}
            count = es.count(index="asthma_data", body={"query":query})["count"]
            data = es.search(index="asthma_data", query=query, size=count)["hits"]["hits"]
            response = []
            for item in data:
                response.append({
                    "date":item["_source"]["date"], 
                    "have_medicine":item["_source"]["have_medicine"], 
                    "medicine":item["_source"]["medicine"], 
                    "percent":item["_source"]["percent"]
                })
            return Response(response)
        return Response({"message":"user is not Autorize"}, status=HTTP_401_UNAUTHORIZED)


    def post(self, request):
        if Auth(jwt_checker(request.headers["Authorization"].split(" ")[1])):
            data = request.data
            result = {
                "percent":float(data["percent"]), 
                "date":datetime.now().isoformat(), 
                "have_medicine": data["have_medicine"], 
                "medicine": data["medicine"], 
                "user_id":data["user_id"] 
            }
            es.index(index="asthma_data", document=result)
            self.check(data["user_id"], data["percent"], 7, 4)
            self.check(data["user_id"], data["percent"], 30, 7)
            return Response({"message":"data added"}, status=HTTP_201_CREATED)
        return Response({"message":"user is not Autorize"}, status=HTTP_401_UNAUTHORIZED)