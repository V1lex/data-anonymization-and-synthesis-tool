# Архитектура репозитория

## Цель
Зафиксировать структуру проекта и правила размещения логики.

## Слои и ответственность
1. `src/sda/core/generation/` - доменная логика генерации данных.
2. `src/sda/core/anonymization/` - доменная логика анонимизации.
3. `src/sda/core/ml/` - эвристики и синтез похожих данных.
4. `src/sda/io/` - чтение и запись CSV.
5. `src/sda/use_cases/` - прикладные сценарии и оркестрация слоев.
6. `src/sda/web/routers/` - HTTP-эндпоинты.
7. `src/sda/web/schemas/` - Pydantic-схемы API.
8. `src/sda/resources/templates/` - шаблоны генерации.
9. `tests/` - модульные и API-тесты.

## Правила зависимостей
1. `core` не зависит от FastAPI и HTTP-типа данных.
2. `web` делегирует бизнес-логику в `use_cases`.
3. `use_cases` связывает `core`, `io` и `web`.
4. `io` занимается только преобразованием CSV.
5. `schemas` описывают API-контракты и не подменяют доменные модели.

## Куда добавлять новую логику
1. `suggest_pii`: `core/ml` -> `use_cases/suggest_pii.py` -> `web/routers/suggest.py`.
2. `similar`: `core/ml/synthesizer.py` -> `use_cases/synthesize_csv.py` -> `web/routers/similar.py`.

## Антипаттерны
1. Дублирование бизнес-логики одновременно в роутерах и use case.
2. Чтение/запись CSV напрямую в роутерах.
3. Использование HTTP-статусов внутри `core`.
4. Хардкод схем шаблонов внутри endpoint-кода.
