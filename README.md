# Investing Demo

## Setup (Windows PowerShell)

Create a virtual environment with Python 3.14 and install the pinned dependencies:

```powershell
C:\Users\Александр\AppData\Local\Python\bin\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `TINKOFF_TOKEN` and a private `DJANGO_SECRET_KEY` in `.env`. Do not commit `.env`; it is ignored by Git. The sample Compose configuration publishes PostgreSQL on port 5433 and Redis on port 6380 to avoid common local port conflicts. Override `POSTGRES_PORT` or `REDIS_PORT` in `.env` if needed.

Start the database and Redis, then apply migrations:

```powershell
docker compose up -d db redis
.\.venv\Scripts\python.exe manage.py migrate
```

Load shares from Tinkoff Invest API (requires `TINKOFF_TOKEN`):

```powershell
.\.venv\Scripts\python.exe manage.py add_shares
```

Start Django:

```powershell
.\.venv\Scripts\python.exe manage.py runserver
```

The REST API is available at `/api/v1/shares/`.

## Celery

Run Beat and the worker in separate terminals. On Windows, use the `solo` worker pool:

```powershell
.\.venv\Scripts\celery.exe -A config beat
.\.venv\Scripts\celery.exe -A config worker -l info -P solo
```
