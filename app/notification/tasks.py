from django_app.celery import app
from django.conf import settings
from google_helper.sheets import get_list
from telegram_helper.telegram import send_message
from google_helper.sheets import update as gs_update
from google_helper.sheets import update_cells as gs_update_cells
from celery.schedules import crontab

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
def today():
    dt = datetime.now(ZoneInfo("Asia/Almaty"))
    return dt
def tomorrow(dt):
    return dt + timedelta(days=1)
def humanize(dt):
    return '.'.join([str(x) for x in [dt.day, dt.month, dt.year]])

def get_target_datehour():
    dt = datetime.now(ZoneInfo("Asia/Almaty")) + timedelta(days=1)
    return '.'.join([str(x) for x in [dt.day, dt.month, dt.year]]), str(dt.hour)

def required_setting(name):
    value = getattr(settings, name, "")
    if not value:
        raise RuntimeError(f"Missing required setting: {name}")
    return value

@app.task
def send_dentist_remainders(*args, **kwargs):
    bot_id = required_setting("DENTIST_TELEGRAM_BOT_ID")
    sheet_id = required_setting("DENTIST_SHEET_ID")
    message = "Добрый день! Напоминаем Вам, что вы записаны на завтра, {} в {} к {}"

    clients = get_list(sheet_id, "Клиенты")
    telegram_ids = dict([(x[0], x[2]) for x in clients[1:]])
    
    reservations = get_list(sheet_id, "Бронь")
    times = reservations[0]
    tomorrow, hour = get_target_datehour()
    j = 2
    while j < len(times):
        if (times[j].split(':')[0] == hour):
            break
        j += 1

    date = ""
    for i in range(2, len(reservations)):
        row = reservations[i]
        if (len(row) == 0):
            continue
        if (row[0] != ""):
            date = row[0]
        if (date != tomorrow):
            continue
        if (j >= len(row)):
            continue
        if (row[j] in telegram_ids):
            send_message(bot_id, telegram_ids[row[j]], message.format(tomorrow, hour, row[1]))

@app.task
def update_schedule(*args, **kwargs):
    sheet_id = required_setting("DENTIST_SHEET_ID")
    docs = ["Doctor A", "Doctor B", "Doctor C", "Doctor D"]
    data = []
    data.append(["Date", "Doc", "9:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"])
    length = len(data[0])
    data.append(["-" for _ in range(length)])
    date = today()
    for i in range(7):
        data.append([humanize(date), docs[0]] + [""] * (length - 2))
        for j in range(1, len(docs)):
            data.append(["", docs[j]] + [""] * (length - 2))
        data.append([""] * length)
        date = tomorrow(date)
    gs_update(sheet_id, "Бронь", data)

@app.task
def send_delivery_remainders(*args, **kwargs):
    bot_id = required_setting("DELIVERY_TELEGRAM_BOT_ID")
    sheet_id = required_setting("DELIVERY_SHEET_ID")
    tracked = get_list(sheet_id, "Отслеживаемые")
    settings = get_list(sheet_id, "Настройки")
    before_track = settings[23][6]
    after_track = settings[24][6]
    after_date = settings[25][6]
    allowed_status = []
    allowed_status.append(settings[6][9])
    allowed_status.append(settings[7][9])
    dt = today() - timedelta(days=2)
    to_upd_cells = []
    to_upd_vals = []
    i = 1
    for row in tracked[1:]:
        i += 1
        if (row[2] not in allowed_status):
            continue
        if (row[4] == "SENT"):
            continue
        update_date = datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("Asia/Almaty"))
        day_delta = (update_date - dt).days
        if (day_delta > 0):
            continue
        message = (before_track + " " + row[0] + " " + after_track
                    + " " + ".".join(str(x) for x in [update_date.day, update_date.month, update_date.year]) 
                    + after_date)
        res = send_message(bot_id, row[1], message)
        to_upd_cells.append([i, 5])
        to_upd_vals.append("SENT" if res == 1 else "ERROR")
    if (len(to_upd_cells) > 0):
        gs_update_cells(sheet_id, "Отслеживаемые", to_upd_cells, to_upd_vals)
