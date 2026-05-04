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

## Структура проекта

```text
.
├── dockerfiles/          # Dockerfile'ы backend и frontend
├── docs/                 # материалы спринтов, отчеты, UAT и проектная документация
├── frontend/             # Next.js frontend
│   ├── src/app/          # страницы приложения
│   ├── src/components/   # UI-компоненты Generate, Anonymize, Similar и общие блоки
│   ├── src/hooks/        # frontend hooks
│   └── src/lib/          # API-клиент, типы ответов и download helpers
├── scripts/              # вспомогательные скрипты для локальных проверок
├── src/sda/              # backend Python-пакет
│   ├── core/             # доменная логика: генерация, анонимизация, Similar/SDV
│   ├── io/               # чтение и запись CSV
│   ├── resources/        # JSON-шаблоны генерации
│   ├── use_cases/        # application use cases для API
│   └── web/              # FastAPI app, routers, schemas и stores
├── tests/                # backend unit/integration tests
├── compose.yaml          # Docker Compose запуск всего приложения
└── requirements.txt      # backend Python dependencies
```

## API

- `GET /api/v1/health`
- `GET /api/v1/generate/templates`
- `GET /api/v1/generate/templates/{template_id}`
- `POST /api/v1/generate/run`
- `POST /api/v1/anonymize/upload`
- `POST /api/v1/anonymize/run`
- `POST /api/v1/similar/analyze`
- `POST /api/v1/similar/run`
