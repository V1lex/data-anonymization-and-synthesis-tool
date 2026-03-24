# SDA (Synthetic Data Anonymizer)

Простой учебный проект для кейса: генерация синтетических CSV и анонимизация CSV без использования реальных персональных данных.

## Что сейчас готово

- `GET /`, `GET /generate`, `GET /anonymize` - рабочие web-экраны.
- `GET /similar` - пока заглушка без реального backend-сценария.
- `GET /api/v1/health` - healthcheck.
- `GET /api/v1/generate/templates`
- `GET /api/v1/generate/templates/{template_id}`
- `POST /api/v1/generate/run`
- `POST /api/v1/anonymize/upload`
- `POST /api/v1/anonymize/run`

## Как запустить

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn --app-dir src sda.web.app:app --reload
```

Для разработки и тестов:

```bash
python -m pip install -r requirements-dev.txt
```

После старта открой:

- `http://127.0.0.1:8000/` - главная
- `http://127.0.0.1:8000/generate` - UI генерации
- `http://127.0.0.1:8000/anonymize` - UI анонимизации
- `http://127.0.0.1:8000/docs` - Swagger UI

## Как проверить

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Ручная проверка:

- В шапке переключи язык `RU/EN` и проверь, что тексты интерфейса меняются без перезагрузки.
- В `Generate` выбери Faker locale (`ru_RU` или `en_US`), затем выбери один шаблон и скачай один CSV.
- Выбери несколько зависимых шаблонов, например `users + orders`, и скачай ZIP.
- В `Anonymize` загрузи CSV, проверь preview, выбери правила вручную и скачай `*_anonymized.csv`.
- Для CSV с `;` в качестве разделителя не указывай delimiter вручную: backend теперь корректно определяет его автоматически.

## Docker Compose (MVP one-command run)

Run from the project root:

```bash
docker compose up --build
```

Services:
- `frontend` at `http://localhost:8080`
- `backend` API at `http://localhost:8000`
- backend healthcheck endpoint: `http://localhost:8000/api/v1/health`

Compose starts 2 containers:
- `sda-frontend` (Nginx + static UI)
- `sda-backend` (FastAPI API)

Stop:

```bash
docker compose down
```
