from time import sleep
import requests
from threading import Thread
import json

def send_message(bot_id, chat_id, message, *args, **kwargs):
    url = f"https://api.telegram.org/bot{bot_id}/sendMessage"
    body = {
        "chat_id": chat_id,
        "text": message
    }
    r = requests.post(url, data=body)
    return int(r.status_code == requests.codes.ok and r.json()["ok"])

def send_message_split(bot_id, chat_id, message, timeout=0.15, limit=3500, *args, **kwargs):
    arr = message.split('\n')
    arr2 = [arr[0]]
    for msg in arr[1:]:
        if len(arr2[-1]) + len(msg) < limit:
            arr2[-1] += "\n" + msg
        else:
            arr2.append(msg)
    suc = 0
    for msg in arr2:
        suc += send_message(bot_id, chat_id, msg)
        sleep(timeout)
    return suc == len(arr2)

def batch_send(bot_id, chat_ids, message, fire_and_forget = True, *args, **kwargs):
    if isinstance(chat_ids, str):
        chat_ids = json.loads(chat_ids)
    if fire_and_forget:
        for id in chat_ids:
            Thread(target=send_message, args=(bot_id, id, message, )).start()
            sleep(0.033)
        return None
    succesful = 0
    for id in chat_ids:
        succesful += send_message(bot_id, id, message)
        sleep(0.033)
    return succesful

def batch_send_unique(bot_id, chat_ids, messages, timeout=0.033, *args, **kwargs):
    if isinstance(chat_ids, str):
        chat_ids = json.loads(chat_ids)
    if isinstance(messages, str):
        messages = json.loads(messages)
    if len(chat_ids) != len(messages):
        raise ValueError('Please specify a message for every chat_id')
    succesful = []
    for chat, message in zip(chat_ids, messages):
        suc = False
        try:
            suc = send_message(bot_id, chat, message)
        except Exception as e:
            print(e)
        succesful.append(suc)
        sleep(timeout)
    return succesful
