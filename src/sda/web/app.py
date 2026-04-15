from pathlib import Path

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from sda.core.domain.errors import SdaError
from sda.web.routers.anonymize import router as anonymize_router
from sda.web.routers.generate import router as generate_router
from sda.web.routers.health import router as health_router
from sda.web.routers.similar import router as similar_router
from sda.web.schemas.generate import ErrorResponse

API_PREFIX = "/api/v1"
STATIC_DIR = Path(__file__).resolve().parent / "static"


def _static_asset_url(file_name: str) -> str:
    asset_path = STATIC_DIR / file_name
    version = asset_path.stat().st_mtime_ns
    return f"/static/{file_name}?v={version}"


def _render_shell(page: str, title: str) -> HTMLResponse:
    css_url = _static_asset_url("app.css")
    js_url = _static_asset_url("app.js")
    html = f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title}</title>
    <script>
      (() => {{
        const page = "{page}";
        const defaultTitle = "{title}";
        const titles = {{
          ru: {{
            home: "SDA",
            generate: "SDA - Генерация",
            anonymize: "SDA - Анонимизация",
            similar: "SDA - Похожие данные",
          }},
          en: {{
            home: "SDA",
            generate: "SDA - Generate",
            anonymize: "SDA - Anonymize",
            similar: "SDA - Similar Data",
          }},
        }};

        let language = "ru";
        try {{
          const stored = window.localStorage.getItem("sda_ui_language");
          if (stored && Object.prototype.hasOwnProperty.call(titles, stored)) {{
            language = stored;
          }}
        }} catch (error) {{
          language = "ru";
        }}

        document.documentElement.lang = language;
        document.title = titles[language]?.[page] || defaultTitle;
      }})();
    </script>
    <link rel="stylesheet" href="{css_url}" />
  </head>
  <body data-page="{page}">
    <main id="app"></main>
    <script>
      window.SDA_API_BASE = "{API_PREFIX}";
    </script>
    <script src="{js_url}" defer></script>
  </body>
</html>"""
    return HTMLResponse(html)


def create_app() -> FastAPI:
    app = FastAPI(title="Генератор и анонимизатор данных")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    app.include_router(health_router, prefix=API_PREFIX)
    app.include_router(generate_router, prefix=API_PREFIX)
    app.include_router(anonymize_router, prefix=API_PREFIX)
    app.include_router(similar_router, prefix=API_PREFIX)

    @app.exception_handler(SdaError)
    async def handle_sda_error(_, exc: SdaError) -> JSONResponse:
        payload = ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            request_id=None,
        ).model_dump()
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_, exc: RequestValidationError) -> JSONResponse:
        payload = ErrorResponse(
            error_code="validation_error",
            message="Невалидный запрос.",
            details={"errors": jsonable_encoder(exc.errors())},
            request_id=None,
        ).model_dump()
        return JSONResponse(status_code=422, content=payload)

    @app.get("/", response_class=HTMLResponse)
    async def home_page() -> HTMLResponse:
        return _render_shell("home", "SDA")

    @app.get("/generate", response_class=HTMLResponse)
    async def generate_page() -> HTMLResponse:
        return _render_shell("generate", "SDA - Генерация")

    @app.get("/anonymize", response_class=HTMLResponse)
    async def anonymize_page() -> HTMLResponse:
        return _render_shell("anonymize", "SDA - Анонимизация")

    @app.get("/similar", response_class=HTMLResponse)
    async def similar_page() -> HTMLResponse:
        return _render_shell("similar", "SDA - Похожие данные")

    return app


app = create_app()
