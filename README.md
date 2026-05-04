# SDA

SDA — веб-сервис для работы с синтетическими и анонимизированными CSV-данными.

Сервис позволяет:

- генерировать синтетические CSV-файлы по готовым шаблонам;
- анонимизировать загруженные CSV-файлы по выбранным правилам;
- создавать похожие синтетические датасеты на основе загруженного CSV.

## Запуск через Docker Compose

```bash
docker compose up --build
```

После запуска:

- frontend: `http://127.0.0.1:3000`
- backend API: `http://127.0.0.1:8000/docs`
- healthcheck: `http://127.0.0.1:8000/api/v1/health`

Остановить сервис:

```bash
docker compose down
```

## Локальный запуск

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn --app-dir src sda.web.app:app --reload
```

Frontend:

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api/v1 npm run dev
```

Адреса по умолчанию:

- frontend: `http://127.0.0.1:3000`
- backend: `http://127.0.0.1:8000`

## API

- `GET /api/v1/health`
- `GET /api/v1/generate/templates`
- `GET /api/v1/generate/templates/{template_id}`
- `POST /api/v1/generate/run`
- `POST /api/v1/anonymize/upload`
- `POST /api/v1/anonymize/run`
- `POST /api/v1/similar/analyze`
- `POST /api/v1/similar/run`
