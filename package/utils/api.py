import requests
from dotmap import DotMap
from package.utils.helper import Alert
from package.utils.logger import Logger
from package.config import ConfigHelper


class APIHelper():
    def __init__(self,base_url=None, apiKey=None, headers=None):
        try:
            self.config = ConfigHelper()
            self.base_url = base_url if not base_url is None else self.config.read_config('schoolURL')
            self.apiKey = apiKey if not apiKey is None else self.config.read_config('apiKey')
            self.campusId = self.config.read_config('campusId')
            self.headers = headers or {}
            self.timeout = (5, 10)
        except Exception as e:
            Logger.error(f"Error in api helper init: {e}")
    
    # Makes an API call and returns the JSON response.
    # Args:
    #     endpoint (str): The API endpoint (appended to the base URL).
    #     method (str): HTTP method (GET, POST, PUT, DELETE).
    #     params (dict): Query parameters for GET requests.
    #     data (dict): Form-encoded data for POST/PUT requests.
    #     json (dict): JSON payload for POST/PUT requests.
    #     headers (dict): Additional headers for the request.

    # Returns:
    #     dict: The JSON response from the API.
    def request(self, endpoint, method="GET", params=None, data=None, json=None, headers=None):
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        if not self.base_url:
            return DotMap({"success":False,"code":400,"data":[],"error":"Missing schoolURL","response":None})
        if self.base_url.strip().lower().startswith('http://'):
            Logger.error("Blocked insecure HTTP schoolURL. Use HTTPS.")
            return DotMap({"success":False,"code":400,"data":[],"error":"Insecure schoolURL (HTTP). Use HTTPS.","response":None})
        headers = headers or self.headers
        if self.apiKey:
            headers = {**headers, "Authorization": f"Bearer {self.apiKey}"}
        response = None
        
        if(method=="GET"):
            if params :
                params['apikey'] = self.apiKey
            else:
                params = {"apikey" : self.apiKey}
                
        elif(method=="POST"):
            if data :
                data['apikey'] = self.apiKey
            else:
                data = {"apikey" : self.apiKey}

        try:
            response = requests.request(method, url, params=params, data=data, json=json, headers=headers, timeout=self.timeout)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
            return DotMap(response.json())  # Parse and return JSON response
        except requests.exceptions.RequestException as e:
            Logger.error(f"Error calling API: {e}")
            return DotMap({"success":False,"code":401,"data":[],"error":e,"response":response})
        except ValueError as e:
            Logger.error(f"Error parsing JSON response in api: {e}")
            return DotMap({"success":False,"code":401,"data":[],"error":e,"response":response})
      
    # ///////////////////////////////////////////////////////////
    #       Helper functions
    # /////////////////////////////////////////////////////////// 
    def downloadConfig(self,returnResponse=False): 
        status = True
        try: 
            response = self.request('/api/v1/biometric/config')
            if response.success is False:
                status = False 
                Logger.error(f"Configuration download error: {response}") 
            else:  
                if response.data.orgName is not None:
                    self.config.write_config('providerName',response.data.orgName)
                if response.data.parentLink is not None:
                    self.config.write_config('baseURL',response.data.parentLink)
                if response.data.providerEmail is not None:
                    self.config.write_config('providerEmail',response.data.providerEmail)
                if response.data.providerWebsite is not None:
                    self.config.write_config('providerWebsite',response.data.providerWebsite)                            
                if response.data.biometricTarget is not None:
                    self.config.write_config('biometricTarget',response.data.biometricTarget)
                if response.data.isBiometricEnabled is not None:
                    self.config.write_config('isBiometricEnabled',response.data.isBiometricEnabled)
                
                # return response for parsing
                if returnResponse:
                    return response
        except Exception as e: 
            Logger.error(f"Configuration download error: {e} {response}")
            status = False  
        return status

    def loadUser(self,id): 
        status = True
        try: 
            params = {"id" : id}
            response = self.request('/api/v1/biometric/loaduser',params=params)
            if response.success is False:
                status = False 
                Logger.error(f"Users download error: {response}") 
            else:  
                return response.data                           
        except Exception as e: 
            Logger.error(f"Users download error: {e} {response}")
            status = False  
        if status is False:
            return False

    def loadUsers(self,type=''): 
        status = True
        try: 
            params = {"type" : type}
            response = self.request('/api/v1/biometric/loadusers',params=params)
            if response.success is False:
                status = False 
                Logger.error(f"Users download error: {response}") 
            else:  
                return response.data                           
        except Exception as e: 
            Logger.error(f"Users download error: {e} {response}")
            status = False  
        if status is False:
            return False

    def postAttendance(self,attendance,type='checkin'): 
        # details of punches
        # check-in punch = 0
        # check-out punch = 1
        # overtime-in punch = 4
        # overtime-out punch = 5

        status = True
        try: 
            payload = {
                "type": type,
                "id": attendance.user_id,
                "timestamp": attendance.timestamp,
                "status": attendance.status,
                "punch": attendance.punch,
            }
            response = self.request('/api/v1/biometric/saveattendance',method="POST",data=payload)
            if response.success is False:
                status = False 
                Logger.error(f"Attendance posting error: {format(response or '')} with payload:{payload}") 
            else:  
                return True                           
        except Exception as e: 
            Logger.error(f"Attendance uploading error: {e}")
            status = False  
        if status is False:
            return False

    # ///////////////////////////////////////////////////////////////////////////////////////////////////

    # def loadUserOld(self,id):
    #     data = None
    #     try:
    #         payload = {"apikey": self.apiKey, "campusId": self.campusId, "id" : id}
    #         req = requests.get(self.baseURL + self.module + "loaduser", params = payload)
    #         if(req.status_code):
    #             response = req.json()
    #             data = response['data']
    #         req.close()
    #     except Exception as e:
    #         Logger.error(f"Error in loading a User: {format(e)}")
    #     return data

    # def loadUsersOld(self):
    #     data = None
    #     try:
    #         payload = {"apikey": self.apiKey, "campusId": self.campusId}
    #         req = requests.get(self.baseURL + self.module + "loadusers", params = payload)
    #         if(req.status_code):
    #             data = req.json()
    #         req.close()
    #     except Exception as e:
    #         Logger.error(f"Error in loading Users: {format(e)}")
    #     return data
        
    # def postAttendanceOld(self,attendance,type='checkin'):
    #     status = False
    #     # details of punches
    #     # check-in punch = 0
    #     # check-out punch = 1
    #     # overtime-in punch = 4
    #     # overtime-out punch = 5
    #     try:
    #         payload = {
    #             "apikey": self.apiKey, 
    #             "campusId": self.campusId,
    #             "type": type,
    #             "id": attendance.user_id,
    #             "timestamp": attendance.timestamp,
    #             "status": attendance.status,
    #             "punch": attendance.punch,
    #         }
    #         req = requests.post(self.baseURL + self.module + "saveattendance", data= payload)
    #         if(req.status_code):
    #             response = req.json()
    #             if response['code']== 200: status=True
    #         req.close()
    #     except Exception as e:
    #         Logger.error(f"Error in saving attendance: {format(e)}")
    #     return status