from time import sleep
import requests
from threading import Thread
import google_helper.sheets as sheets
import json
from django.conf import settings

def terra_motors_sheet_id():
    sheet_id = getattr(settings, "TERRA_MOTORS_SHEET_ID", "")
    if not sheet_id:
        raise RuntimeError("Missing required setting: TERRA_MOTORS_SHEET_ID")
    return sheet_id

def send_message(bot_phone, client_phone, client_row, template, auth, *args, **kwargs):
    url = "https://api.nexmo.com/v0.1/messages"
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
                "locale": "ru"
            }
        }
    }
    r = requests.post(url, json=body, headers=headers)
    if r.status_code == requests.codes.accepted:
        sheets.update_cells(terra_motors_sheet_id(), "Лист1", [(client_row, 2)], ["Доставлено"])
        return 1
    sheets.update_cells(terra_motors_sheet_id(), "Лист1", [(client_row, 2)], ["Сбой"])
    return 0
    
def batch_send(bot_phone, client_phones, template, auth, fire_and_forget = True, *args, **kwargs):
    if fire_and_forget:
        for (id, row) in client_phones:
            Thread(target=send_message, args=(bot_phone, id, row, template, auth, )).start()
            sleep(0.033)
        return None
    succesful = 0
    for (id, row) in client_phones:
        succesful += send_message(bot_phone, id, row, template, auth)
        sleep(0.033)
    return succesful

def get_and_send(bot_phone, template, auth, *args, **kwargs):
    data = sheets.get_list(terra_motors_sheet_id(), "Лист1")[2:]
    client_list = []
    for row in range(len(data)):
        if data[row][1] != "Доставлено":
            client_list.append((data[row][0], row + 3))
    batch_send(bot_phone, client_list, template, auth, args, kwargs)
