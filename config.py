import os

class Config(object):
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    API_ID = int(os.environ.get("12475131"))
    API_HASH = os.environ.get("719171e38be5a1f500613837b79c536f")
    VIP_USER = os.environ.get('VIP_USERS', '').split(',')
    VIP_USERS = [int(1714266885) for user_id in VIP_USER]
