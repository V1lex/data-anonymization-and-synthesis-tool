# Low-Fi UI Flow Sprint 1

Документ фиксирует экранный путь пользователя до начала верстки и привязан к макетам из `Data Generation Tool Design`.

## 1. Главная страница

### Блоки

- Header: логотип/анимация названия, language switcher
- Hero title
- 3 action cards:
  - `Generate`
  - `Anonymize`
  - `Similar`

### Действия пользователя

1. Открывает приложение.
2. Видит три плашки с кратким описанием сценариев.
3. Переходит в нужную ветку по клику на карточку.

### Состояния

- `empty`: только 3 карточки и описания
- `loading`: не нужен как отдельный экран, переход мгновенный
- `error`: глобальный banner только если не удалось загрузить shell приложения
- `success`: пользователь успешно перешел в нужный раздел

## 2. Generate

### Экран и блоки

- Header с кнопкой Back
- Заголовок и subtitle страницы
- Summary cards:
  - selected tables
  - total rows
  - output format
- Список template cards:
  - checkbox/select table
  - label + description
  - preview columns/tags
  - counter `- / input / +`
- Primary CTA: `Generate and download`

### Пользовательский путь

1. Пользователь открывает `Generate`.
2. Видит список доступных template’ов: `users`, `orders`, `payments`, `products`, `support_tickets`.
3. Включает одну или несколько таблиц.
4. Для каждой выбранной таблицы задает `row_count`.
5. Видит, как summary cards пересчитывают количество таблиц и total rows.
6. Нажимает `Generate and download`.
7. Frontend отправляет `POST /generate/run`.
8. Получает `GenerateRunResponse`.
9. Если `result_format=csv_base64`, сразу скачивает один CSV.
10. Если `result_format=zip_base64`, скачивает архив.

### Состояния

- `empty`: ни одна таблица не выбрана, CTA disabled или заменен подсказкой `Select at least one`
- `loading`: overlay spinner на время генерации
- `error`: inline alert над CTA, например `Template generation failed`
- `success`: файл скачан, CTA кратко показывает completed state

## 3. Anonymize

### Экран 1: Upload

Блоки:

- Header с Back
- Title + subtitle
- Большая dropzone / upload card
- Текст про допустимый формат `CSV only`

Шаги:

1. Пользователь открывает `Anonymize`.
2. Загружает CSV.
3. Frontend вызывает `POST /anonymize/upload`.
4. Backend возвращает `upload_id`, columns, preview rows и suggestions.

Состояния:

- `empty`: только upload area
- `loading`: spinner во время upload/parsing
- `error`: ошибка загрузки/парсинга под dropzone
- `success`: переход ко второму экрану без отдельного route

### Экран 2: Column review and rules

Блоки:

- File summary card:
  - file name
  - columns count
  - records count
  - toggle preview show/hide
- Preview table на 3-5 строк
- Список column cards:
  - column name
  - delete/restore column
  - набор action chips для методов:
    - keep
    - mask
    - remove
    - pseudonymize
    - generalize year
    - generalize date
- Actions:
  - upload another
  - anonymize and download

Шаги:

1. Пользователь просматривает summary и первые строки файла.
2. Для каждой колонки либо оставляет suggested/default method, либо меняет вручную.
3. Может удалить колонку целиком через `remove`.
4. Нажимает `Anonymize and download`.
5. Frontend отправляет `POST /anonymize/run` с `upload_id` и полным набором `rules`.
6. Получает `AnonymizeRunResponse`.
7. Скачивает готовый CSV.

Состояния:

- `empty`: после upload это состояние не используется
- `loading`: spinner на время применения правил
- `error`: inline alert у action buttons, например `Unknown column in rules`
- `success`: файл скачан; опционально сохраняется экран с выбранными rules

## 4. Similar

### Экран 1: Upload and explanation

Блоки:

- Header с Back
- Title + subtitle
- Upload card
- Secondary info card `How it works`

Шаги:

1. Пользователь открывает `Similar`.
2. Загружает CSV.
3. Frontend отправляет `POST /similar/analyze`.
4. Backend возвращает `analysis_id`, profiles колонок, preview и summary.

Состояния:

- `empty`: upload area + explanatory block
- `loading`: spinner во время анализа
- `error`: ошибка upload/analysis под upload area
- `success`: показ второго состояния страницы

### Экран 2: Structure preview and generation

Блоки:

- Source file summary card:
  - file name
  - column count
  - record count
- Column chips / structure preview
- Analyze summary list
- Generation params card:
  - target row count input
  - quick presets
- Stats cards:
  - source records
  - will generate
  - increase percentage
- Actions:
  - upload another
  - generate and download similar

Шаги:

1. Пользователь смотрит структуру и summary анализа.
2. Задает `target_rows`.
3. Нажимает `Generate and download similar`.
4. Frontend отправляет `POST /similar/run` с `analysis_id`.
5. Получает `SimilarRunResponse`.
6. Скачивает CSV.

Состояния:

- `empty`: до upload
- `loading`: spinner во время синтеза
- `error`: ошибка анализа или генерации рядом с actions
- `success`: файл скачан

## 5. Общие UI-правила состояний

- Любой async шаг должен блокировать повторный submit до завершения.
- Ошибки API показываются рядом с текущим действием, не только в console.
- Успех не должен уводить пользователя со страницы: после скачивания экран остается доступным для повтора.
- Для всех трех веток нужен единый визуальный паттерн состояний: `empty -> loading -> error/success`.
