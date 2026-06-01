# Blum Backend

Django backend for small automation endpoints around Google Sheets, Telegram, WhatsApp/Vonage, and scheduled notification jobs.

The current runtime is Docker Compose. Nginx proxies public traffic to the local web container.

## Runtime Overview

```text
client
  -> nginx
  -> http://127.0.0.1:8010
  -> blum-web / Django / Gunicorn
       -> Google Sheets API
       -> Telegram Bot API
       -> Vonage/Nexmo WhatsApp Messages API
       -> Redis / Celery / Celery Beat
```

Docker Compose services:

| Service | Container | Purpose |
| --- | --- | --- |
| `web` | `blum-web` | Runs migrations, collects static files, then starts Gunicorn on port `8000` inside the container. Exposed on host `127.0.0.1:8010`. |
| `redis` | `blum-redis` | Redis broker and result backend for Celery. |
| `celery-worker` | `blum-celery-worker` | Executes Celery tasks discovered from Django apps. |
| `celery-beat` | `blum-celery-beat` | Runs scheduled tasks using `django_celery_beat.schedulers:DatabaseScheduler`. |

## Project Layout

```text
/root/Blum
|-- app/                         # Django source code copied into the Docker image
|   |-- django_app/              # Django project, URL routes, Celery app
|   |-- google_helper/           # Google Sheets endpoint and helper functions
|   |-- telegram_helper/         # Telegram Bot API endpoint and helper functions
|   |-- whatsapp_helper/         # WhatsApp/Vonage endpoint and helper functions
|   |-- notification/            # Celery scheduled notification tasks
|   |-- misc/                    # Business-specific helpers: China delivery, Terra Motors
|   `-- webhook/                 # Simple test webhook for Fibonacci
|-- config/settings.py           # Runtime settings mounted into containers as /config/settings.py
|-- data/                        # Persistent SQLite DB, media, cache, Celery Beat data
|-- logs/                        # Django log files
|-- secrets/service.key          # Google service account key mounted read-only
|-- static/                      # Collected static files
|-- Dockerfile
|-- docker-compose.yml
`-- blum.md                      # Migration notes from the old systemd setup
```

## Configuration

Base Django settings live in `app/django_app/settings.py`. Docker runtime settings override them from `config/settings.py` because containers set:

```text
PYTHONPATH=/config:/app
DJANGO_SETTINGS_MODULE=settings
```

Important runtime settings:

| Setting | Value / behavior |
| --- | --- |
| `DEBUG` | `False` in Docker runtime. |
| `DJANGO_SECRET_KEY` | Django secret key. Required for stable production sessions and security-sensitive signing. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts. Default: `127.0.0.1,localhost,142.93.128.96`. |
| Database | SQLite at `/data/django_app.db`, mounted from `./data/django_app.db`. |
| Static files | `/static`, mounted from `./static`. |
| Media files | `/data/media`, mounted from `./data/media`. |
| Cache | File-based cache at `/data/cache`. |
| Logs | Console plus `/logs/django_app.log`, rotated daily. |
| Google credentials | `/etc/opt/django_app/service.key`, mounted from `./secrets/service.key`. |
| Celery broker/result backend | `redis://redis:6379`. |
| Time zone | `Asia/Almaty`. |

Create a local `.env` file from `.env.example` before starting production containers:

```bash
cd /root/Blum
cp .env.example .env
```

Then fill in the real values:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Stable Django signing key. |
| `DJANGO_ALLOWED_HOSTS` | Hosts accepted by Django. |
| `DENTIST_TELEGRAM_BOT_ID` | Telegram bot token for dentist reminders. |
| `DENTIST_SHEET_ID` | Spreadsheet ID for dentist clients and bookings. |
| `DELIVERY_TELEGRAM_BOT_ID` | Telegram bot token for delivery reminders. |
| `DELIVERY_SHEET_ID` | Spreadsheet ID for delivery tracking reminders. |
| `TERRA_MOTORS_SHEET_ID` | Spreadsheet ID used by Terra Motors WhatsApp sending. |

## URL Routes

Routes are defined in `app/django_app/urls.py`.

| Path | Method | Handler | Purpose |
| --- | --- | --- | --- |
| `/admin/` | Django admin | Django | Admin UI for built-in Django and `django-celery-beat` tables. |
| `/google` | `POST` | `google_helper.views.google_hook` | JSON API for Google Sheets operations. |
| `/telegram` | `POST` | `telegram_helper.views.telegram_hook` | JSON API for Telegram sends. |
| `/whatsapp` | `POST` | `whatsapp_helper.views.whatsapp_hook` | JSON API for WhatsApp/Vonage sends. |
| `/misc` | `POST` | `misc.views.misc_handler` | Business-specific commands. |
| `/webhook` | `POST` | `webhook.views.webhook` | Test endpoint that returns a Fibonacci number. |

All custom endpoints are CSRF-exempt and expect JSON request bodies. Unsupported methods return HTTP `400`.

## Google Sheets API

Endpoint:

```http
POST /google
Content-Type: application/json
```

The request must include `method`. Most methods require:

| Field | Meaning |
| --- | --- |
| `id` | Google Spreadsheet ID. |
| `name` | Worksheet name. |

Supported methods:

| Method | Code path | Description |
| --- | --- | --- |
| `get_list` | `google_helper.sheets.get_list` | Reads sheet values. Supports `range_name` and `cols=true` for column-major output. |
| `append_row` | `google_helper.sheets.append_row` | Appends one row and returns the created row number. |
| `append_rows` | `google_helper.sheets.append_rows` | Appends multiple rows and returns the number of updated rows. |
| `find` | `google_helper.sheets.find` | Finds one matching cell and returns `[row, col]`, or `null`. |
| `find_all` | `google_helper.sheets.find_all` | Finds all matching cells. Can return full rows or values from a return column. |
| `get_unique` | `google_helper.sheets.get_unique` | Returns unique values from a row or column. |
| `update_cells` | `google_helper.sheets.update_cells` | Updates a list of cells with a list of values. |
| `multi_method` | `google_helper.views.google_hook` | Executes several Google methods in order from `methods`. |

Example:

```bash
curl -sS -X POST http://127.0.0.1:8010/google \
  -H 'Content-Type: application/json' \
  -d '{
    "method": "get_list",
    "id": "spreadsheet_id",
    "name": "Sheet1",
    "range_name": "A1:C10"
  }'
```

Response shape:

```json
{
  "result": []
}
```

On exceptions, the endpoint returns HTTP `400` with:

```json
{
  "result": "Request caused exception ..."
}
```

## Telegram API

Endpoint:

```http
POST /telegram
Content-Type: application/json
```

Supported methods:

| Method | Required fields | Description |
| --- | --- | --- |
| `send_message` | `bot_id`, `chat_id`, `message` | Sends one Telegram text message. Returns `1` on Telegram API success, otherwise `0`. |
| `batch_send` | `bot_id`, `chat_ids`, `message` | Sends the same message to many chats. With default `fire_and_forget=true`, starts background threads and returns `null`. |
| `batch_send_unique` | `bot_id`, `chat_ids`, `messages` | Sends a different message to each chat and returns a list of booleans/integers. |

Example:

```bash
curl -sS -X POST http://127.0.0.1:8010/telegram \
  -H 'Content-Type: application/json' \
  -d '{
    "method": "send_message",
    "bot_id": "telegram_bot_token",
    "chat_id": "123456",
    "message": "Hello"
  }'
```

## WhatsApp/Vonage API

Endpoint:

```http
POST /whatsapp
Content-Type: application/json
```

The implementation uses Vonage/Nexmo Messages API:

```text
https://api.nexmo.com/v0.1/messages
```

Supported methods:

| Method | Required fields | Description |
| --- | --- | --- |
| `send_message` | `bot_phone`, `client_phone`, `auth`, `text` | Sends a WhatsApp text message. Returns `1` when Vonage returns HTTP `202 Accepted`, otherwise `0`. |
| `send_template` | `bot_phone`, `client_phone`, `template`, `auth` | Sends a WhatsApp template message. Optional `locale`, default `ru`. |
| `batch_send_template` | `bot_phone`, `client_phones`, `template`, `auth` | Sends one template to many phone numbers. With default `fire_and_forget=true`, starts background threads and returns `null`. |

`auth` is sent as a Basic authorization value, without the `Basic ` prefix in the request payload.

## Misc API

Endpoint:

```http
POST /misc
Content-Type: application/json
```

Supported methods:

| Method | Code path | Description |
| --- | --- | --- |
| `terra_motors_send` | `misc.terra_motors.get_and_send` | Reads phone numbers/statuses from a fixed Google Sheet and sends WhatsApp templates. |
| `china_get_status` | `misc.china_delivery.get_status` | Builds shipment status text for a client from Google Sheets. Can also send it to Telegram. |
| `china_check_client` | `misc.china_delivery.check_client` | Checks whether a client exists in the clients sheet. |
| `china_add_tracks` | `misc.china_delivery.add_tracks` | Adds valid tracking numbers for a client into the tracked sheet. |
| `china_update_table` | `misc.china_delivery.update_table` | Synchronizes status and client info between working sheets. |
| `china_send_notifications` | `misc.china_delivery.send_notifications` | Sends Telegram notifications for tracking status changes and updates Google Sheets. |

These methods are tightly coupled to the spreadsheet layout passed in the request or, for Terra Motors, hardcoded in `app/misc/terra_motors.py`.

## Test Webhook

Endpoint:

```http
POST /webhook
Content-Type: application/json
```

Example:

```bash
curl -sS -X POST http://127.0.0.1:8010/webhook \
  -H 'Content-Type: application/json' \
  -d '{"number": 10}'
```

Expected response:

```text
55
```

## Celery Tasks

Celery app is configured in `app/django_app/celery.py`.

Task implementations are in `app/notification/tasks.py`:

| Task | Description |
| --- | --- |
| `notification.tasks.send_dentist_remainders` | Reads a dentist schedule from Google Sheets and sends Telegram reminders for tomorrow's appointment at the current hour. |
| `notification.tasks.update_schedule` | Rebuilds a seven-day dentist schedule table in Google Sheets. |
| `notification.tasks.send_delivery_remainders` | Reads delivery tracking data from Google Sheets, sends Telegram reminders for stale statuses, and marks rows as `SENT` or `ERROR`. |

The active schedules are stored in the SQLite database through `django-celery-beat`, not in source code. Current database entries in `data/django_app.db`:

| Name | Task | Schedule | Enabled |
| --- | --- | --- | --- |
| `celery.backend_cleanup` | `celery.backend_cleanup` | Daily at `04:00`, `Asia/Almaty` | Yes |
| `notification.tasks.send_dentist_remainders()` | `notification.tasks.send_dentist_remainders` | Every hour at minute `15`, `Asia/Almaty` | Yes |
| `Update Schedule` | `notification.tasks.update_schedule` | Day `1` of every month at `03:24`, `Asia/Almaty` | Yes |
| `Delivery Remainders` | `notification.tasks.send_delivery_remainders` | Daily at `12:05` and `17:05`, `Asia/Almaty` | No |

Schedules can be changed from Django admin under the `Periodic tasks` section.

## Running The Project

Start all services:

```bash
cd /root/Blum
docker compose up -d
```

Rebuild after Python code, Dockerfile, or dependency changes:

```bash
cd /root/Blum
docker compose up -d --build
```

Check container status:

```bash
cd /root/Blum
docker compose ps
```

View logs:

```bash
cd /root/Blum
docker compose logs -f web
docker compose logs -f celery-worker
docker compose logs -f celery-beat
docker compose logs -f redis
```

Run Django checks:

```bash
cd /root/Blum
docker compose exec -T web python manage.py check
```

Run migrations manually:

```bash
cd /root/Blum
docker compose exec -T web python manage.py migrate
```

Open a Django shell:

```bash
cd /root/Blum
docker compose exec web python manage.py shell
```

Stop services:

```bash
cd /root/Blum
docker compose stop
```

## Data And Persistence

Persistent paths mounted into containers:

| Host path | Container path | Purpose |
| --- | --- | --- |
| `./data` | `/data` | SQLite DB, media files, file cache. |
| `./static` | `/static` | Collected Django static files. |
| `./logs` | `/logs` | Rotating Django logs. |
| `./secrets/service.key` | `/etc/opt/django_app/service.key` | Google service account credentials. |
| `./config` | `/config` | Runtime Django settings. |

The web container runs `python manage.py migrate` and `python manage.py collectstatic --noinput` before starting Gunicorn.

## Operational Checks

Local health checks:

```bash
curl -i http://127.0.0.1:8010/google
curl -i http://127.0.0.1:8010/telegram
curl -i http://127.0.0.1:8010/whatsapp
curl -i http://127.0.0.1:8010/misc
```

For these GET requests, expected behavior is HTTP `400` with:

```text
Use POST request
```

Public check through nginx:

```bash
curl -i http://142.93.128.96/google
```

## Important Notes

- Several integrations depend on exact Google Sheet IDs, worksheet names, and column positions. Changing spreadsheet layouts can break the business logic.
- Secrets, bot tokens, and private spreadsheet IDs must live in `.env` or mounted secret files. Do not commit real values to this public repository.
- Custom endpoints are unauthenticated and CSRF-exempt. Access control should be handled at the network/proxy level or added in Django before exposing broader access.
- `telegram_helper` and `whatsapp_helper` have views imported by URL routes, but these apps are not listed in `INSTALLED_APPS` in the base settings. This is acceptable because they do not define database models used by migrations.
- Most app `models.py` files are empty. The database mainly stores Django built-in tables and `django-celery-beat` schedules.
- Background batch sends often use Python threads and may return before external API calls finish when `fire_and_forget` is left as `true`.

## Legacy Migration Notes

`blum.md` documents the migration from the old systemd-based deployment to Docker Compose, including nginx changes and rollback commands. Use it when investigating deployment history or when a rollback to the previous systemd setup is required.
