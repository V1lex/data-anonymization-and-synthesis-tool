# SDA (Synthetic Data Generator & Anonymizer)

Инструмент для генерации синтетических CSV и анонимизации CSV без использования реальных персональных данных.

## Что сейчас готово

- `GET /`, `GET /generate`, `GET /anonymize` - рабочие web-экраны.
- `GET /similar` - заглушка без реального backend-сценария.
- `GET /api/v1/health` - healthcheck.
- `GET /api/v1/generate/templates`
- `GET /api/v1/generate/templates/{template_id}`
- `POST /api/v1/generate/run`
- `POST /api/v1/anonymize/upload`
- `POST /api/v1/anonymize/run`

## Запуск через Docker

Сборка образа:

```bash
docker build -t sda .
```

Запуск контейнера:

```bash
docker run --rm -d -p 8000:8000 --name sda-app sda
```

После старта открой:

- `http://127.0.0.1:8000/` - главная
- `http://127.0.0.1:8000/generate` - UI генерации
- `http://127.0.0.1:8000/anonymize` - UI анонимизации
- `http://127.0.0.1:8000/docs` - Swagger UI

Остановить контейнер:

```bash
docker stop sda-app
```

## Локальный запуск без Docker

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn --app-dir src sda.web.app:app --reload
```

## Разработка и тесты

Установка dev-зависимостей:

```bash
python -m pip install -r requirements-dev.txt
```

Запуск тестов:

```bash
python -m pytest -q
```
