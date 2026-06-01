# Blum Backend

Backend на Django для внутренних автоматизаций: Google Sheets, Telegram, WhatsApp/Vonage и фоновые уведомления через Celery.

## Как устроено

```text
nginx
  -> 127.0.0.1:8010
  -> blum-web, Django + Gunicorn
       -> Google Sheets API
       -> Telegram Bot API
       -> Vonage/Nexmo WhatsApp API
       -> Redis + Celery
```

Сервисы в `docker-compose.yml`:

| Сервис | Контейнер | Что делает |
| --- | --- | --- |
| `web` | `blum-web` | Django/Gunicorn, принимает HTTP-запросы. |
| `redis` | `blum-redis` | Брокер для Celery. |
| `celery-worker` | `blum-celery-worker` | Выполняет фоновые задачи. |
| `celery-beat` | `blum-celery-beat` | Запускает задачи по расписанию из `django-celery-beat`. |

## Структура

```text
app/django_app/         настройки Django, URL routes, Celery app
app/google_helper/     операции с Google Sheets
app/telegram_helper/   отправка сообщений Telegram
app/whatsapp_helper/   отправка WhatsApp через Vonage/Nexmo
app/notification/      Celery-задачи с уведомлениями
app/misc/              бизнес-логика China delivery и Terra Motors
app/webhook/           простой тестовый webhook с Fibonacci
config/settings.py     production-настройки для Docker
docker-compose.yml     запуск web/redis/celery
blum.md                заметки о переносе со старой systemd-схемы
```

Локальные runtime-данные не коммитятся:

```text
data/django_app.db     основная SQLite-база Django
data/celerybeat_schedule.db
                       служебная SQLite-база Celery Beat
data/media/            media-файлы
data/cache/            файловый cache Django
logs/                  логи
static/                collectstatic output
secrets/service.key    Google service account key
.env                   реальные переменные окружения
```

Внутри контейнера основная база доступна как `/data/django_app.db`.

## Переменные окружения

Скопировать пример:

```bash
cp .env.example .env
```

Заполнить:

| Переменная | Для чего |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django secret key. |
| `DJANGO_ALLOWED_HOSTS` | Разрешенные хосты через запятую. |
| `DENTIST_TELEGRAM_BOT_ID` | Telegram bot token для стоматологических напоминаний. |
| `DENTIST_SHEET_ID` | Google Sheet со стоматологическими клиентами и бронями. |
| `DELIVERY_TELEGRAM_BOT_ID` | Telegram bot token для delivery-уведомлений. |
| `DELIVERY_SHEET_ID` | Google Sheet с delivery-трекингом. |
| `TERRA_MOTORS_SHEET_ID` | Google Sheet для Terra Motors рассылки. |

Google credentials лежат файлом:

```text
./secrets/service.key -> /etc/opt/django_app/service.key
```

## HTTP API

Все рабочие endpoints принимают `POST` с JSON. CSRF отключен.

| Endpoint | Назначение |
| --- | --- |
| `/google` | Обертка над Google Sheets. |
| `/telegram` | Отправка Telegram-сообщений. |
| `/whatsapp` | Отправка WhatsApp через Vonage/Nexmo. |
| `/misc` | Специальные команды для China delivery и Terra Motors. |
| `/webhook` | Тестовый endpoint, считает Fibonacci. |
| `/admin/` | Django admin, включая расписания `django-celery-beat`. |

Формат успешного ответа обычно такой:

```json
{"result": "..."}
```

При ошибке обработчики возвращают HTTP `400` и текст ошибки в `result`.

## `/google`

Обязательное поле: `method`.

Частые поля:

| Поле | Что это |
| --- | --- |
| `id` | ID Google Spreadsheet. |
| `name` | Название worksheet. |
| `range_name` | Диапазон, например `A1:C10`. |

Методы:

| `method` | Что делает |
| --- | --- |
| `get_list` | Читает значения. |
| `append_row` | Добавляет одну строку. |
| `append_rows` | Добавляет несколько строк. |
| `find` | Ищет первую ячейку. |
| `find_all` | Ищет все ячейки. |
| `get_unique` | Возвращает уникальные значения из строки или колонки. |
| `update_cells` | Обновляет список ячеек. |
| `multi_method` | Выполняет несколько методов подряд. |

Пример:

```bash
curl -sS -X POST http://127.0.0.1:8010/google \
  -H 'Content-Type: application/json' \
  -d '{"method":"get_list","id":"spreadsheet_id","name":"Sheet1","range_name":"A1:C10"}'
```

## `/telegram`

Методы:

| `method` | Что делает |
| --- | --- |
| `send_message` | Отправляет одно сообщение. |
| `batch_send` | Отправляет один текст нескольким chat id. |
| `batch_send_unique` | Отправляет разные тексты разным chat id. |

`batch_send` по умолчанию работает в режиме `fire_and_forget=true`: запускает отправку в потоках и сразу возвращает ответ.

Пример:

```bash
curl -sS -X POST http://127.0.0.1:8010/telegram \
  -H 'Content-Type: application/json' \
  -d '{"method":"send_message","bot_id":"token","chat_id":"123","message":"Hello"}'
```

## `/whatsapp`

Используется Vonage/Nexmo Messages API:

```text
https://api.nexmo.com/v0.1/messages
```

Методы:

| `method` | Что делает |
| --- | --- |
| `send_message` | Отправляет WhatsApp text message. |
| `send_template` | Отправляет WhatsApp template. |
| `batch_send_template` | Отправляет template нескольким номерам. |

`auth` передается как значение для Basic auth без префикса `Basic `.

## `/misc`

Методы:

| `method` | Что делает |
| --- | --- |
| `terra_motors_send` | Берет номера из Google Sheet Terra Motors и отправляет WhatsApp template. |
| `china_get_status` | Собирает текст статуса посылок клиента. |
| `china_check_client` | Проверяет наличие клиента в таблице. |
| `china_add_tracks` | Добавляет tracking numbers клиента. |
| `china_update_table` | Синхронизирует статусы между таблицами. |
| `china_send_notifications` | Отправляет Telegram-уведомления по статусам и обновляет Google Sheet. |

Эта логика зависит от конкретной структуры Google Sheets: порядок колонок важен.

## Celery

Задачи лежат в `app/notification/tasks.py`.

| Задача | Что делает |
| --- | --- |
| `send_dentist_remainders` | Напоминает клиентам Telegram-сообщением о записи на завтра. |
| `update_schedule` | Пересобирает таблицу броней на 7 дней. |
| `send_delivery_remainders` | Отправляет delivery-напоминания и отмечает строки как `SENT` или `ERROR`. |

Расписание хранится в таблицах `django-celery-beat`, управляется через Django admin.

Текущие записи в базе:

| Название | Задача | Расписание | Включено |
| --- | --- | --- | --- |
| `celery.backend_cleanup` | `celery.backend_cleanup` | Каждый день в `04:00` | Да |
| `notification.tasks.send_dentist_remainders()` | `send_dentist_remainders` | Каждый час на `15` минуте | Да |
| `Update Schedule` | `update_schedule` | 1 числа каждого месяца в `03:24` | Да |
| `Delivery Remainders` | `send_delivery_remainders` | Каждый день в `12:05` и `17:05` | Нет |

Таймзона: `Asia/Almaty`.

## Запуск

```bash
docker compose up -d
```
