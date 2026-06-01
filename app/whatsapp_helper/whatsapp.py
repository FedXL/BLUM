from time import sleep
import requests
from threading import Thread
import google_helper.sheets as sheets
import json

url = "https://api.nexmo.com/v0.1/messages"

def send_message(bot_phone, client_phone, auth, text, *args, **kwargs):
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
    }
    body = {
        "from": {
            "type": "whatsapp",
            "number": f"{bot_phone}"
        },
        "to": {
            "type": "whatsapp",
            "number": f"{client_phone}"
        },
        "message": {
            "content": {
                "type": "text",
                "text": f"{text}"
            }
        }
    }
    r = requests.post(url, json=body, headers=headers)
    if r.status_code == requests.codes.accepted:
        return 1
    return 0

def send_template(bot_phone, client_phone, template, auth, locale="ru", *args, **kwargs):
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
    }
    body = {
        "from": {
            "type": "whatsapp",
            "number": f"{bot_phone}"
        },
        "to": {
            "type": "whatsapp",
            "number": f"{client_phone}"
        },
        "message": {
            "content": {
                "type": "template",
                "template": {
                     "name": f"{template}"
                }
            },
            "whatsapp": {
                "locale": f"{locale}"
            }
        }
    }
    r = requests.post(url, json=body, headers=headers)
    if r.status_code == requests.codes.accepted:
        return 1
    return 0
    
def batch_send_template(bot_phone, client_phones, template, auth, fire_and_forget = True, *args, **kwargs):
    if fire_and_forget:
        for phone in client_phones:
            Thread(target=send_template, args=(bot_phone, phone, template, auth, )).start()
            sleep(0.033)
        return None
    succesful = 0
    for phone in client_phones:
        succesful += send_template(bot_phone, phone, template, auth)
        sleep(0.033)
    return succesful
