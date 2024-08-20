import os
import json
from datetime import datetime, timedelta


class SqTokenInfo:
    def __init__(self, token):
        self.refresh_token = token["refresh_token"]
        self.access_token = token["access_token"]
        self.access_token_expires_at = token["access_token_expires_at"]
        self.refresh_token_expires_at = token["refresh_token_expires_at"]
        self.client_id = token["client_id"]
        self.user_id = token["users_id"]
        self.app_id = token["apps_id"]
        self.granted_scopes = token["scopes"]


class SqAuthScopes:
    READ_BASIC_PROFILE = "user.basic_profile.read"
    READ_APP_ACHIEVEMENTS = "user.app_achievements.read"
    WRITE_APP_ACHIEVEMENTS = "user.app_achievements.write"
    USER_FRIENDS_READ = "user.friends.read"
    USER_FRIENDS_WRITE = "user.friends.write"
    USER_RICH_PRESENCE_WRITE = "user.rich_presence.write"
    USER_COMMUNITIES_READ = "user.communities.read"
    USER_COMMUNITIES_WRITE = "user.communities.write"
    USER_MESSAGES_RECEIVE = "user.messages.read"
    USER_MESSAGES_SEND = "user.messages.write"
    USER_MESSAGE_HISTORY = "user.messagehistory.read"
    USER_AVATAR_WRITE = "user.avatars.write"


class SqLoginCode:
    def __init__(self):
        self.code = None
        self.device_id = None
        self.expires_at = None
        self.poll_interval_seconds = None
        self.verification_url = None


class SqCreateUploadDone:
    def __init__(self):
        self.file_id = None
        self.name = None


class SqCreateUploadRequest:
    def __init__(self):
        self.space_slug = None
        self.name = None
        self.size = None
        self.type = None


class SqCreateUpload:
    def __init__(self):
        self.file_id = None
        self.path = None
        self.upload_uri = None
        self.communities_id = None


class SqUser:
    def __init__(self, user):
        self.user_id = user["users_id"]
        self.name = user["name"]


class SqAppApiConfig:
    def __init__(
        self, client_id, data_path, test_mode=False, data_file_name="sqappapi.json"
    ):
        if not os.path.exists(data_path):
            raise FileNotFoundError("Specified data path does not exist")
        if not data_file_name:
            raise ValueError("data_file_name must be provided.")
        if not client_id:
            raise ValueError("client_id must be specified")

        self.data_path = data_path
        self.data_file_name = data_file_name
        self.root_api_uri = "api.sidetestvr.com" if test_mode else "api.sidequestvr.com"
        self.root_cdn_uri = "cdn.sidetestvr.com" if test_mode else "cdn.sidequestvr.com"
        self.client_id = client_id


class UploadAvatarType:
    LOW = 1
    HIGH = 2
