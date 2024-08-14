import os
import json
import http.client
from datetime import datetime, timedelta
from threading import Timer
from urllib.parse import *
from .sq_models import *
from .sq_exceptions import *
import bpy

PLUGIN_ID = "banter_avatar_plugin"

class SqAppApi:
    def __init__(self):
        self.user = None
        self.login_code = None
        self.token = None
        client_id = "client_85b087d9975cb8ca5bb575a2" # test
        # client_id = "client_0e4c67f9a6bbe12143870312" # prod
        self.config = SqAppApiConfig(client_id, bpy.utils.user_resource('EXTENSIONS', path=PLUGIN_ID, create=True), True, "sqappapi.json")
        self.load_data()

    def save_data(self):
        data = {
            "User": {
                "users_id": self.user.user_id,
                "name": self.user.name,
            },
            "Token": {
                "refresh_token": self.token.refresh_token,
                "access_token": self.token.access_token,
                "access_token_expires_at": self.token.access_token_expires_at_str,
                "refresh_token_expires_at": self.token.refresh_token_expires_at,
                "client_id": self.token.client_id,
                "users_id": self.token.user_id,
                "apps_id": self.token.app_id,
                "scopes": self.token.granted_scopes,
            }
        }
        f = open(os.path.join(self.config.data_path, self.config.data_file_name), "w")
        f.write(json.dumps(data))
        f.close()

    def load_data(self):
        path = os.path.join(self.config.data_path, self.config.data_file_name)
        self.check_code_timer = RepeatedTimer(10 if self.login_code is None else self.login_code.interval, self.check_login_code_complete)
        if os.path.exists(path):
            file = open(path, 'r')
            data = json.loads(file.read())
            file.close()
            self.user = SqUser(data["User"])
            self.token = SqTokenInfo(data["Token"])
            self.token.access_token_expires_at_str = self.token.access_token_expires_at
            self.token.access_token_expires_at = datetime.fromisoformat(self.token.access_token_expires_at.replace('Z', '+00:00')).replace(tzinfo=None)
            self.refresh_user_profile()
        else:
            self.get_login_code()
            self.check_code_timer.start()


    def set_my_avatar(self):
        if self.token is None:
            raise SqApiAuthException("No user logged in.")

        return SqUser(self.json_get("/v2/users/me/avatar/files", True)) # put - body {"high_avatar_files_id": files_id, "low_avatar_files_id": files_id, "is_public": true}

    def get_user_profile(self):
        if self.token is None:
            raise SqApiAuthException("No user logged in.")

        return SqUser(self.json_get("/v2/users/me", True))

    def logout(self):
        self.user = None
        self.token = None
        self.login_code = None
        os.remove(os.path.join(self.config.data_path, self.config.data_file_name))
        self.get_login_code()
        self.check_code_timer.start()

    def refresh_user_profile(self):
        self.user = self.get_user_profile()
        if str(self.user.user_id) != str(self.token.user_id):
            raise SqApiException("User refreshed data does not match user token ID!")

    def json_get(self, path, with_auth):
        conn = http.client.HTTPSConnection(self.config.root_api_uri)
        headers = {
            'Content-Type': 'application/json'
        }
        if(with_auth and self.token != None):
            headers["Authorization"] = "Bearer " + self.get_auth_token()
        
        conn.request("GET", path, headers=headers)
        res = conn.getresponse()
        data = res.read()
        return json.loads(data.decode("utf-8"))

    def upload_avatars(self, highpath, lowpath):
        high = highpath
        low = lowpath
        create_upload_high = json.loads(self.json_post("/create-upload", True, True, json.dumps({
            "name": "high_avatar.glb",
            "size": os.path.getsize(high),
            "type": "application/octet-stream",
            "purpose": "banter-avatar"
        })))

        create_upload_low = json.loads(self.json_post("/create-upload", True, True, json.dumps({
            "name": "low_avatar.glb",
            "size": os.path.getsize(low),
            "type": "application/octet-stream",
            "purpose": "banter-avatar"
        })))
        high_domain = urlparse(create_upload_high["upload_uri"]).netloc
        high_path = create_upload_high["upload_uri"].split(high_domain)[1]
        high_file = open(high, "rb")
        upload_high = self.json_post(high_path, False, False, high_file.read(), "PUT", high_domain, {
            'Content-Type': 'application/octet-stream'
        })
        high_file.close()

        low_domain = urlparse(create_upload_low["upload_uri"]).netloc
        low_path = create_upload_low["upload_uri"].split(low_domain)[1]
        low_file = open(low, "rb")
        upload_low = self.json_post(low_path, False, False, low_file.read(), "PUT", low_domain, {
            'Content-Type': 'application/octet-stream'
        })
        low_file.close()
        
        print("/v2/users/me/avatar/files", json.dumps({
            "high_avatar_files_id": create_upload_high["fileId"],
            "low_avatar_files_id": create_upload_low["fileId"],
            "is_public": True
        }))
        set_avatar = self.json_post("/v2/users/me/avatar/files", False, True, json.dumps({
            "high_avatar_files_id": create_upload_high["fileId"],
            "low_avatar_files_id": create_upload_low["fileId"],
            "is_public": True
        }), "PUT")

    def json_put(self, path, is_cdn, with_auth, body):
        self.json_post(self, path, is_cdn, with_auth, body, "PUT")

    def json_post(self, path, is_cdn, with_auth, body, method = "POST", url = None, headers = {
            'Content-Type': 'application/json'
        }):
        the_url = self.config.root_api_uri
        if not url is None:
            the_url = url
        elif is_cdn:
            the_url = self.config.root_cdn_uri
            
        conn = http.client.HTTPSConnection(the_url)

        if(with_auth and self.token != None):
            headers["Authorization"] = "Bearer " + self.get_auth_token()
        conn.request(method, path, body, headers)
        res = conn.getresponse()
        data = res.read()
        print(res.status, str(res.status)[:1]);
        if(str(res.status)[:1] == "4"):
            raise Exception("API Error: " + json.loads(data.decode("utf-8"))["detail"])
        elif(res.status != 204):
            return data.decode("utf-8")


    def post_form_encoded_string_no_auth(self, path, body):
        conn = http.client.HTTPSConnection(self.config.root_api_uri)
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        conn.request("POST", path, body, headers)
        res = conn.getresponse()
        data = res.read()
        return json.loads(data.decode("utf-8"))
            

    def get_login_code(self, scopes=None):
        if scopes is None:
            scopes = [
                SqAuthScopes.READ_BASIC_PROFILE,
                SqAuthScopes.READ_APP_ACHIEVEMENTS,
                SqAuthScopes.WRITE_APP_ACHIEVEMENTS,
                SqAuthScopes.USER_FRIENDS_READ,
                SqAuthScopes.USER_FRIENDS_WRITE,
                SqAuthScopes.USER_RICH_PRESENCE_WRITE,
                SqAuthScopes.USER_COMMUNITIES_READ,
                SqAuthScopes.USER_COMMUNITIES_WRITE,
                SqAuthScopes.USER_MESSAGES_RECEIVE,
                SqAuthScopes.USER_MESSAGES_SEND,
                SqAuthScopes.USER_MESSAGE_HISTORY,
                SqAuthScopes.USER_AVATAR_WRITE
            ]

        self._last_login_poll = datetime.now()
        response = json.loads(self.json_post("/v2/oauth/getshortcode", False, False, json.dumps({
            "client_id": self.config.client_id,
            "scopes": scopes
        })))
        self.login_code = SqLoginCode()
        self.login_code.__dict__.update(response)
        self.login_code.expires_at = datetime.fromisoformat(self.login_code.expires_at.replace('Z', '+00:00')).replace(tzinfo=None)
        print("Got login code: " + self.login_code.code + " with device id: " + self.login_code.device_id)
        
        # self.save_data()

    def check_login_code_complete(self):
        
        if (datetime.now() - self._last_login_poll).total_seconds() < self.login_code.interval:
            return False, None

        if self.login_code is None:
            raise Exception("There is not a code login in progress")
        
        if datetime.utcnow() > self.login_code.expires_at:
            return False, None

        print("checking code...")
        response_json = self.json_post("/v2/oauth/checkshortcode", False, False, json.dumps({
            "code": self.login_code.code,
            "device_id": self.login_code.device_id
        }))
        response = None if response_json is None else json.loads(response_json)

        if response is None:
            self._last_login_poll = datetime.now()
            return False, None

        self.check_code_timer.stop()
        self.user = None
        self.token = SqTokenInfo(response)
        self.token.access_token_expires_at_str = self.token.access_token_expires_at
        self.token.access_token_expires_at = datetime.fromisoformat(self.token.access_token_expires_at.replace('Z', '+00:00')).replace(tzinfo=None)

        self.refresh_user_profile()
        self.login_code = None

        self.save_data()
        return True, self.user


    def get_auth_token(self):
        if self.token is None or self.token.access_token_expires_at is None:
            raise SqApiAuthException("No user is logged in")

        if datetime.utcnow() < self.token.access_token_expires_at - timedelta(minutes=1) and self.token.access_token:
            return self.token.access_token

        if not self.token.refresh_token:
            self.logout()
            raise SqApiAuthException("User refresh token is missing, logging user out")

        response = self.post_form_encoded_string_no_auth("/v2/oauth/token", "grant_type=refresh_token&refresh_token=" + quote_plus(self.token.refresh_token) + "&client_id=" + self.token.client_id)

        if response is None or response.get("access_token") is None:
            raise SqApiAuthException("Failed to retrieve auth token")

        new_auth = {
            "refresh_token": self.token.refresh_token,
            "access_token": response["access_token"],
            "access_token_expires_at": datetime.fromisoformat(response["access_token_expires_at"].replace('Z', '+00:00')).replace(tzinfo=None),
            "access_token_expires_at_str": response["access_token_expires_at"],
            "refresh_token_expires_at": self.token.refresh_token_expires_at,
            "users_id": self.token.user_id,
            "client_id": self.token.client_id,
            "apps_id": self.token.app_id,
            "scopes": self.token.granted_scopes
        }
        self.token = SqTokenInfo(new_auth)
        return self.token.access_token



class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
    
    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)
    
    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True
    
    def stop(self):
        self._timer.cancel()
        self.is_running = False