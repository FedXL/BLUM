# Blum Docker Compose Migration

Дата переноса: 2026-06-01

## Что было сделано

Старое Django-приложение `django_app`, которое обслуживает endpoint `/google`, перенесено из systemd-сервисов в Docker Compose проект:

```bash
/root/Blum
```

Созданы основные файлы:

```bash
/root/Blum/docker-compose.yml
/root/Blum/Dockerfile
/root/Blum/config/settings.py
/root/Blum/requirements.txt
/root/Blum/.dockerignore
```

Код приложения перенесен сюда:

```bash
/root/Blum/app
```

`/root/Blum/app` теперь является рабочей кодовой базой Django-приложения для Docker Compose. Старый каталог `/opt/django_app` больше не используется runtime-схемой после переключения nginx на контейнеры.

В `/root/Blum/app` перенесены исходники приложения. Старые служебные каталоги `/opt/django_app/venv`, `/opt/django_app/.git` и `__pycache__` не переносились как часть Docker runtime:

- зависимости устанавливаются в Docker image из `requirements.txt`
- Python cache создается заново при запуске
- Git history старого каталога не нужен для запуска контейнеров

При сравнении `/opt/django_app` и `/root/Blum/app` без `.git`, `venv` и `__pycache__` исходники совпадают. Единственное ожидаемое отличие - `requirements.txt`: в старом каталоге файл был в битой UTF-16/нулевой кодировке, а в `/root/Blum` лежит нормальная читаемая версия для Docker build.

Данные приложения перенесены сюда:

```bash
/root/Blum/data/django_app.db
/root/Blum/data/celerybeat_schedule.db
/root/Blum/data/media
/root/Blum/secrets/service.key
/root/Blum/static
/root/Blum/logs
```

Важно: старая media-директория `/var/opt/django_app/media` была пустая. В базе `django_app.db` ссылок на `.jpg`, `.jpeg`, `.png` или `/media/` не найдено. На сервере есть фотографии в Docker volumes других проектов (`med`, `kino`, `battery`, `water`), но они не относятся к этому `django_app`/`/google` endpoint.

## Текущая схема

Сейчас запрос идет так:

```text
http://142.93.128.96/google
  -> nginx
  -> http://127.0.0.1:8010/google
  -> Docker container blum-web
```

Docker Compose сервисы:

```bash
blum-web
blum-redis
blum-celery-worker
blum-celery-beat
```

Проверка:

```bash
cd /root/Blum
docker compose ps
curl -i http://142.93.128.96/google
```

Ожидаемый ответ на GET:

```text
HTTP/1.1 400 Bad Request
Use POST request
```

Это нормально, потому что `/google` ожидает POST.

## Что изменено в nginx

Файл:

```bash
/etc/nginx/sites-available/default
```

В default server для IP `142.93.128.96` изменено:

```nginx
location / {
    proxy_pass http://localhost:8010/;
}

location /static/ {
    alias /root/Blum/static/;
}

location /media/ {
    alias /root/Blum/data/media/;
}
```

Backup старого nginx-конфига сохранен:

```bash
/etc/nginx/sites-available/default.before-blum-docker
```

## Какие старые systemd-сервисы отключены

Остановлены и отключены:

```bash
django_app.service
celery-worker-django_app.service
celery-beat-django_app.service
redis-for-django_app.service
```

Проверка:

```bash
systemctl show django_app.service celery-worker-django_app.service celery-beat-django_app.service redis-for-django_app.service -p Id -p ActiveState -p SubState -p UnitFileState
```

## Управление Docker Compose

Статус:

```bash
cd /root/Blum
docker compose ps
```

Логи:

```bash
cd /root/Blum
docker compose logs -f web
docker compose logs -f celery-worker
docker compose logs -f celery-beat
docker compose logs -f redis
```

Перезапуск:

```bash
cd /root/Blum
docker compose restart
```

Остановить:

```bash
cd /root/Blum
docker compose stop
```

Запустить:

```bash
cd /root/Blum
docker compose up -d
```

Пересобрать после изменений в коде или зависимостях:

```bash
cd /root/Blum
docker compose up -d --build
```

Проверка Django:

```bash
cd /root/Blum
docker compose exec -T web python manage.py check
docker compose exec -T web python manage.py showmigrations --plan
```

## Как вернуть обратно на старую systemd-схему

Rollback нужен, если Docker Compose версия перестала работать и нужно вернуть старое приложение на `127.0.0.1:8000`.

### 1. Остановить Docker Compose

```bash
cd /root/Blum
docker compose stop
```

### 2. Вернуть nginx-конфиг

Самый простой вариант - восстановить backup:

```bash
cp -a /etc/nginx/sites-available/default.before-blum-docker /etc/nginx/sites-available/default
nginx -t
systemctl reload nginx
```

Если нужно править вручную, вернуть в `/etc/nginx/sites-available/default`:

```nginx
location / {
    proxy_pass http://localhost:8000/;
}

location /static/ {
    alias /var/cache/django_app/static/;
}

location /media/ {
    alias /var/opt/django_app/media/;
}
```

Потом:

```bash
nginx -t
systemctl reload nginx
```

### 3. Вернуть данные из Docker Compose обратно в старые пути

Если Docker-версия уже принимала реальные POST-запросы и могла изменить базу, перед rollback скопировать актуальную SQLite-базу обратно:

```bash
cp -a /root/Blum/data/django_app.db /var/opt/django_app/django_app.db
cp -a /root/Blum/data/celerybeat_schedule.db /var/opt/django_app/celerybeat_schedule.db
cp -a /root/Blum/data/media/. /var/opt/django_app/media/
chown django_app:django /var/opt/django_app/django_app.db /var/opt/django_app/celerybeat_schedule.db
chown -R django_app:root /var/opt/django_app/media
```

### 4. Включить старые systemd-сервисы

```bash
systemctl enable --now redis-for-django_app.service
systemctl enable --now django_app.service
systemctl enable --now celery-worker-django_app.service
systemctl enable --now celery-beat-django_app.service
```

Проверить:

```bash
systemctl status django_app.service --no-pager
systemctl status celery-worker-django_app.service --no-pager
systemctl status celery-beat-django_app.service --no-pager
systemctl status redis-for-django_app.service --no-pager
ss -ltnp | grep ':8000'
```

### 5. Проверить endpoint

```bash
curl -i http://127.0.0.1:8000/google
curl -i http://142.93.128.96/google
```

Ожидаемый ответ на GET:

```text
HTTP/1.1 400 Bad Request
Use POST request
```

## Что еще стоит сделать

1. Проверить реальный POST payload к `/google`, потому что во время переноса был проверен только GET, который ожидаемо возвращает `400 Use POST request`.
2. Добавить бэкап `/root/Blum/data/django_app.db`.
3. Решить, нужно ли переносить фотографии из других проектов. Для текущего Blum/`django_app` media пустая, но на сервере есть фото в Docker volumes других проектов.
4. При желании настроить Redis warning:

```bash
sysctl vm.overcommit_memory=1
```

И закрепить настройку в `/etc/sysctl.conf`, если Redis warning критичен.
