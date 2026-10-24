# Investing Demo

Django-приложение со справочником акций, ценами из T-Invest API (Т-Банк), REST API и фоновым обновлением цен через Celery.

Требования: Python 3.14 (проверено на 3.14.3), Docker.

## Запуск

```bash
# 1. Настройки: скопировать шаблон и заполнить DJANGO_SECRET_KEY и TINKOFF_TOKEN
cp .env.example .env

# 2. PostgreSQL и Redis
docker compose up -d

# 3. Зависимости
python -m venv .venv
.venv/Scripts/activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pip install --no-deps -r requirements-sdk.txt   # SDK Т-Банка (см. комментарий в файле)

# 4. База и первичная загрузка акций (нужен TINKOFF_TOKEN)
python manage.py migrate
python manage.py add_shares

# 5. Веб-сервер
python manage.py runserver

# 6. Фоновое обновление цен (в отдельных терминалах)
celery -A config worker -l info -P solo   # на Windows нужен -P solo
celery -A config beat -l info
```

Без токена и доступа к T-Invest API приложение можно посмотреть на демо-данных (цены выдуманы):

```bash
python manage.py loaddata demo_shares
python manage.py generate_demo_prices   # синтетическая история цен только для демо-акций
```

Ограничения подключения к API описаны в `ANALYSIS.md`, раздел 18.

## Возможности

* справочник акций, карточка с графиком, REST API `/api/v1/shares/`;
* история цен с выбором периода, изменениями и графиком — `/history/<id>/`;
* списки наблюдения с ценовыми уровнями и уведомлениями — `/watchlists/`, `/notifications/`;
* виртуальные портфели с покупками/продажами и прибылью/убытком — `/portfolios/`;
* симулятор стратегий с журналом сделок и бэктестом — `/strategies/`.

Уведомления и сделки стратегий формируются автоматически после каждого обновления цен (Celery).

## Тесты

```bash
python manage.py test
```

## API

`/api/v1/shares/` — работа с акциями (список, поиск `?search=`, фильтры `?name=`/`?ticker=`, сортировка `?ordering=`, пагинация `?limit=&offset=`).
