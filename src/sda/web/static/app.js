const apiBase = window.SDA_API_BASE || "/api/v1";
const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;
const DEFAULT_UI_LANGUAGE = "ru";
const UI_LANGUAGE_STORAGE_KEY = "sda_ui_language";
const TYPEWRITER_PHRASES = ["Generate easily.", "Anonymize easily.", "Download easily."];

const templateDependencies = {
  users: [],
  orders: ["users", "products"],
  payments: ["users", "orders"],
  products: [],
  support_tickets: ["users"],
};

const fakerLocaleOptions = [
  {
    value: "ru_RU",
    label: {
      ru: "Русский",
      en: "Russian",
    },
    hint: {
      ru: "Русские имена, города и адреса",
      en: "Russian names, cities, and addresses",
    },
  },
  {
    value: "en_US",
    label: {
      ru: "Английский",
      en: "English",
    },
    hint: {
      ru: "Английские имена и адреса США",
      en: "English names and US-style addresses",
    },
  },
];

const uiMessages = {
  ru: {
    common: {
      requestFailed: "Не удалось выполнить запрос.",
      back: "Назад",
      downloadDone: "Скачано",
      loading: "загрузка",
      megabytes: "МБ",
    },
    templates: {
      users: {
        label: "Пользователи",
        description: "Таблица пользователей с ФИО, email, телефон",
      },
      orders: {
        label: "Заказы",
        description: "Таблица заказов с пользователем, товаром и количеством",
      },
      payments: {
        label: "Платежи",
        description: "Таблица платежей с картами и транзакциями",
      },
      products: {
        label: "Товары",
        description: "Каталог товаров с ценами",
      },
      support_tickets: {
        label: "Тикеты поддержки",
        description: "Обращения в поддержку",
      },
    },
    methods: {
      keep: "Оставить",
      mask: "Маскировать",
      redact: "Скрыть",
      pseudonymize: "Псевдоним",
      generalize_year: "Обобщение до года",
    },
    home: {
      generateTitle: "Генерация данных",
      generateDescription: "Создайте синтетические таблицы по шаблону. Выберите типы таблиц и количество записей.",
      generateAction: "Начать генерацию",
      anonymizeTitle: "Анонимизация",
      anonymizeDescription: "Защитите персональные данные. Загрузите CSV и выберите методы анонимизации для каждого поля.",
      anonymizeAction: "Анонимизировать",
      similarTitle: "Похожие данные",
      similarDescription: "Раздел пока что не доступен.",
      similarAction: "Открыть раздел",
    },
    generate: {
      title: "Генерация синтетических данных",
      subtitle: "Выберите таблицы и количество записей для генерации",
      selectedTables: "Выбрано таблиц",
      totalRows: "Всего записей",
      format: "Формат",
      loadingTemplates: "Загрузка шаблонов...",
      emptySelection: "Выберите хотя бы одну таблицу для генерации",
      running: "Генерация...",
      run: "Сгенерировать и скачать",
      rowCountAriaLabel: "количество строк",
      localeTitle: "Язык и регион данных",
      localeSubtitle: "Выберите язык и регион для имён, городов, телефонов и адресов.",
      dependencyError: "Для генерации \"{template}\" также выберите: {dependencies}.",
    },
    anonymize: {
      title: "Анонимизация данных",
      subtitle: "Загрузите CSV файл и настройте методы анонимизации",
      uploadTitle: "Загрузите CSV файл",
      uploadHint: "Перетащите файл сюда или нажмите для выбора",
      uploadBadge: "Можно загрузить CSV до {size}",
      fileTooLarge: "Файл слишком большой. Максимальный размер: {size}.",
      infoMeta: "{columnCount} колонок | {rowCount} записей",
      hidePreview: "Скрыть превью",
      showPreview: "Показать превью",
      previewNote: "Показано {shown} из {total} записей",
      sectionTitle: "Настройка анонимизации",
      uploadAnother: "Загрузить другой файл",
      running: "Анонимизация...",
      run: "Анонимизировать и скачать",
    },
    similar: {
      title: "Генерация похожих данных",
      subtitle: "Маршрут сохранён в дизайне проекта, но логика этого режима в текущей версии недоступна",
      unavailableTitle: "Раздел пока недоступен",
      unavailableHint: "Сейчас в проекте активны сценарии генерации и анонимизации. Этот экран оставлен только как визуальный маршрут.",
      soon: "Скоро здесь будет отдельный сценарий",
    },
    errors: {
      invalid_file_type: "Поддерживаются только CSV-файлы.",
      empty_file: "Загруженный файл пуст.",
      csv_parse_error: "Не удалось разобрать CSV-файл.",
      file_too_large: "Файл слишком большой.",
      validation_error: "Проверьте корректность введённых данных.",
      generation_failed: "Не удалось сгенерировать данные.",
      upload_not_found: "Загруженный файл не найден или уже истёк.",
      invalid_rule: "Выбранное правило анонимизации недопустимо.",
      unknown_column: "Правило ссылается на отсутствующую колонку.",
      template_not_found: "Шаблон не найден.",
      anonymization_failed: "Не удалось анонимизировать данные.",
    },
  },
  en: {
    common: {
      requestFailed: "Request failed.",
      back: "Back",
      downloadDone: "Downloaded",
      loading: "loading",
      megabytes: "MB",
    },
    templates: {
      users: {
        label: "Users",
        description: "User table with full name, email, and phone",
      },
      orders: {
        label: "Orders",
        description: "Orders linked to users, products, and quantity",
      },
      payments: {
        label: "Payments",
        description: "Payment table with cards and transactions",
      },
      products: {
        label: "Products",
        description: "Product catalog with prices",
      },
      support_tickets: {
        label: "Support tickets",
        description: "Support requests",
      },
    },
    methods: {
      keep: "Keep",
      mask: "Mask",
      redact: "Redact",
      pseudonymize: "Pseudonymize",
      generalize_year: "Generalize to year",
    },
    home: {
      generateTitle: "Data generation",
      generateDescription: "Create synthetic tables from templates. Choose datasets and record counts.",
      generateAction: "Start generation",
      anonymizeTitle: "Anonymization",
      anonymizeDescription: "Protect personal data. Upload a CSV file and choose anonymization methods for each field.",
      anonymizeAction: "Anonymize data",
      similarTitle: "Similar data",
      similarDescription: "Section is currently unavailable.",
      similarAction: "Open section",
    },
    generate: {
      title: "Synthetic data generation",
      subtitle: "Choose datasets and record counts for generation",
      selectedTables: "Selected datasets",
      totalRows: "Total rows",
      format: "Format",
      loadingTemplates: "Loading templates...",
      emptySelection: "Select at least one dataset to generate",
      running: "Generating...",
      run: "Generate and download",
      rowCountAriaLabel: "row count",
      localeTitle: "Data language and region",
      localeSubtitle: "Choose the language and region used for names, cities, phone numbers, and addresses.",
      dependencyError: "To generate \"{template}\", also select: {dependencies}.",
    },
    anonymize: {
      title: "Data anonymization",
      subtitle: "Upload a CSV file and choose anonymization methods",
      uploadTitle: "Upload CSV file",
      uploadHint: "Drag a file here or click to choose",
      uploadBadge: "Upload CSV up to {size}",
      fileTooLarge: "File is too large. Max size: {size}.",
      infoMeta: "{columnCount} columns | {rowCount} rows",
      hidePreview: "Hide preview",
      showPreview: "Show preview",
      previewNote: "Showing {shown} of {total} rows",
      sectionTitle: "Anonymization settings",
      uploadAnother: "Upload another file",
      running: "Anonymizing...",
      run: "Anonymize and download",
    },
    similar: {
      title: "Similar data generation",
      subtitle: "This route remains in the design, but the logic is unavailable in the current version",
      unavailableTitle: "Section is unavailable",
      unavailableHint: "The current project only includes generation and anonymization flows. This screen is kept as a visual route.",
      soon: "A separate flow will appear here later",
    },
    errors: {
      invalid_file_type: "Only CSV files are supported.",
      empty_file: "The uploaded file is empty.",
      csv_parse_error: "Could not parse the CSV file.",
      file_too_large: "The file is too large.",
      validation_error: "Please check the request data.",
      generation_failed: "Could not generate data.",
      upload_not_found: "The uploaded file was not found or has expired.",
      invalid_rule: "The selected anonymization rule is invalid.",
      unknown_column: "A rule points to a missing column.",
      template_not_found: "Template not found.",
      anonymization_failed: "Could not anonymize data.",
    },
  },
};

function readInitialLanguage() {
  try {
    const storedLanguage = window.localStorage.getItem(UI_LANGUAGE_STORAGE_KEY);
    if (storedLanguage && Object.hasOwn(uiMessages, storedLanguage)) {
      return storedLanguage;
    }
  } catch (error) {
    // Ignore storage access issues and keep the default language.
  }
  return DEFAULT_UI_LANGUAGE;
}

function getLanguage() {
  if (!window.__sdaUiLanguage) {
    window.__sdaUiLanguage = readInitialLanguage();
  }
  return window.__sdaUiLanguage;
}

function syncDocumentLanguage() {
  document.documentElement.lang = getLanguage();
}

function getPageTitle(pageName) {
  const pageTitles = {
    home: "SDA",
    generate: getLanguage() === "en" ? "SDA - Generate" : "SDA - Генерация",
    anonymize: getLanguage() === "en" ? "SDA - Anonymize" : "SDA - Анонимизация",
    similar: getLanguage() === "en" ? "SDA - Similar Data" : "SDA - Похожие данные",
  };
  return pageTitles[pageName] || "SDA";
}

function syncDocumentMetadata() {
  syncDocumentLanguage();
  document.title = getPageTitle(document.body?.dataset.page || "home");
}

function setLanguage(nextLanguage) {
  if (!Object.hasOwn(uiMessages, nextLanguage)) {
    return;
  }

  window.__sdaUiLanguage = nextLanguage;
  syncDocumentMetadata();

  try {
    window.localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, nextLanguage);
  } catch (error) {
    // Ignore storage write issues and keep the in-memory selection.
  }
}

function resolveMessage(path) {
  return path.split(".").reduce((value, key) => (value == null ? undefined : value[key]), uiMessages[getLanguage()]);
}

function interpolateMessage(template, params = {}) {
  return String(template).replace(/\{(\w+)\}/g, (_, key) => String(params[key] ?? ""));
}

function t(path, params = {}) {
  const value = resolveMessage(path);
  if (typeof value !== "string") {
    return "";
  }
  return interpolateMessage(value, params);
}

function getTypewriterPhrases() {
  return TYPEWRITER_PHRASES;
}

function getTemplateUi(templateId) {
  return uiMessages[getLanguage()].templates[templateId] || {
    label: templateId,
    description: templateId,
  };
}

function getMethodLabel(methodKey) {
  return uiMessages[getLanguage()].methods[methodKey] || methodKey;
}

function getDefaultFakerLocale() {
  return getLanguage() === "en" ? "en_US" : "ru_RU";
}

function getFakerLocaleLabel(locale) {
  const option = fakerLocaleOptions.find((item) => item.value === locale);
  if (!option) {
    return locale;
  }
  return option.label[getLanguage()] || locale;
}

function getApiErrorMessage(payload) {
  if (payload && typeof payload.message === "string" && payload.message.trim()) {
    return payload.message;
  }
  if (payload && typeof payload.error_code === "string") {
    const localizedError = resolveMessage(`errors.${payload.error_code}`);
    if (typeof localizedError === "string") {
      return localizedError;
    }
  }
  return t("common.requestFailed");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function parseApiResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(getApiErrorMessage(payload));
  }
  return payload;
}

function downloadBase64File(base64, fileName, contentType) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  const blob = new Blob([bytes], { type: contentType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function formatMegabytes(bytes) {
  return `${(bytes / (1024 * 1024)).toFixed(0)} ${t("common.megabytes")}`;
}

function formatCount(value) {
  return Number(value || 0).toLocaleString(getLanguage() === "en" ? "en-US" : "ru-RU");
}

function findMissingTemplateDependencies(templateIds) {
  const selected = new Set(templateIds);
  return templateIds.flatMap((templateId) =>
    (templateDependencies[templateId] || [])
      .filter((dependencyId) => !selected.has(dependencyId))
      .map((dependencyId) => ({ templateId, dependencyId })),
  );
}

function sortGenerateItemsByDependencies(items) {
  const itemsByTemplateId = new Map(items.map((item) => [item.template_id, item]));
  const orderedItems = [];
  const visited = new Set();
  const visiting = new Set();

  const visit = (templateId) => {
    if (visited.has(templateId) || visiting.has(templateId)) {
      return;
    }

    visiting.add(templateId);
    (templateDependencies[templateId] || []).forEach((dependencyId) => {
      if (itemsByTemplateId.has(dependencyId)) {
        visit(dependencyId);
      }
    });
    visiting.delete(templateId);
    visited.add(templateId);
    orderedItems.push(itemsByTemplateId.get(templateId));
  };

  items.forEach((item) => visit(item.template_id));
  return orderedItems;
}

function formatGenerateDependencyError(missingDependencies) {
  const [firstMissing] = missingDependencies;
  if (!firstMissing) {
    return "";
  }

  const requiredTemplateIds = missingDependencies
    .filter((item) => item.templateId === firstMissing.templateId)
    .map((item) => getTemplateUi(item.dependencyId).label || item.dependencyId);

  return t("generate.dependencyError", {
    template: getTemplateUi(firstMissing.templateId).label || firstMissing.templateId,
    dependencies: requiredTemplateIds.join(", "),
  });
}

function icon(name) {
  const icons = {
    "arrow-left": `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M19 12H5" />
        <path d="m12 19-7-7 7-7" />
      </svg>
    `,
    "arrow-right": `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M5 12h14" />
        <path d="m12 5 7 7-7 7" />
      </svg>
    `,
    download: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 19V5" />
        <path d="m8 15 4 4 4-4" />
      </svg>
    `,
    check: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m5 12 4.5 4.5L19 7" />
      </svg>
    `,
    database: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <ellipse cx="12" cy="5" rx="7" ry="3" />
        <path d="M5 5v6c0 1.7 3.1 3 7 3s7-1.3 7-3V5" />
        <path d="M5 11v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" />
      </svg>
    `,
    shield: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m12 3 7 3v6c0 4.4-3 8.4-7 9-4-0.6-7-4.6-7-9V6l7-3Z" />
        <path d="m9.5 12 1.8 1.8L15 10.2" />
      </svg>
    `,
    copy: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="9" y="9" width="10" height="10" rx="2" />
        <path d="M7 15H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v1" />
      </svg>
    `,
    upload: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 16V6" />
        <path d="m7 11 5-5 5 5" />
        <path d="M5 19h14" />
      </svg>
    `,
    eye: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M2 12s3.6-6 10-6 10 6 10 6-3.6 6-10 6-10-6-10-6Z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    `,
    "eye-off": `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m3 3 18 18" />
        <path d="M10.6 10.6A2 2 0 0 0 12 14a2 2 0 0 0 1.4-.6" />
        <path d="M9.9 5.2A11.3 11.3 0 0 1 12 5c6.4 0 10 7 10 7a18.7 18.7 0 0 1-3.2 4.2" />
        <path d="M6.2 6.2C3.8 8 2 12 2 12s3.6 7 10 7c1.6 0 3-.4 4.2-.9" />
      </svg>
    `,
    globe: `
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path fill="currentColor" stroke="none" d="M12.87 15.07l-2.54-2.51.03-.03A17.52 17.52 0 0014.07 6H17V4h-7V2H8v2H1v1.99h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z" />
      </svg>
    `,
  };

  return icons[name] || "";
}

function renderHeader() {
  const currentLanguage = getLanguage();
  return `
    <div class="app-header">
      <div class="typewriter">
        <span class="js-typewriter"></span>
        <span class="typewriter-caret"></span>
      </div>
      <div class="language-switcher">
        <span class="language-icon">${icon("globe")}</span>
        <button
          type="button"
          class="language-option ${currentLanguage === "en" ? "active" : ""}"
          data-action="set-language"
          data-language="en"
          aria-pressed="${currentLanguage === "en" ? "true" : "false"}"
        >
          EN
        </button>
        <button
          type="button"
          class="language-option ${currentLanguage === "ru" ? "active" : ""}"
          data-action="set-language"
          data-language="ru"
          aria-pressed="${currentLanguage === "ru" ? "true" : "false"}"
        >
          RU
        </button>
      </div>
    </div>
  `;
}

function renderLayout(content) {
  return `
    <div class="page-shell">
      <div class="screen-container">
        ${renderHeader()}
        ${content}
      </div>
    </div>
  `;
}

function attachCommonControls(onLanguageChange) {
  document.querySelectorAll("[data-action='set-language']").forEach((element) => {
    element.addEventListener("click", () => {
      const nextLanguage = element.dataset.language;
      if (!nextLanguage || nextLanguage === getLanguage()) {
        return;
      }

      setLanguage(nextLanguage);
      onLanguageChange();
    });
  });
}

function buildPageIntro({ accent, title, subtitle, backHref = "/" }) {
  return `
    <section class="page-intro">
      <a class="back-link text-${accent}" href="${backHref}">
        ${icon("arrow-left")}
        ${escapeHtml(t("common.back"))}
      </a>
      <h1 class="page-title">${escapeHtml(title)}</h1>
      <p class="page-subtitle">${escapeHtml(subtitle)}</p>
    </section>
  `;
}

function buildStatsCards(items) {
  return `
    <div class="stats-grid">
      ${items
        .map(
          (item) => `
            <article class="stat-card accent-${item.accent}">
              <span class="stat-orb"></span>
              <div class="stat-label">${escapeHtml(item.label)}</div>
              <div class="stat-value">${escapeHtml(item.value)}</div>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function buildNotice(kind, message) {
  if (!message) {
    return "";
  }

  return `<div class="inline-message ${kind}">${escapeHtml(message)}</div>`;
}

function buildLoadingOverlay(visible, accent = "violet") {
  if (!visible) {
    return "";
  }

  const loadingText = t("common.loading");
  const loadingTextClass = /[А-Яа-яЁё]/.test(loadingText) ? " is-cyrillic" : "";

  return `
    <div class="loading-overlay accent-${accent}" aria-live="polite">
      <div class="loader">
        <span class="loader-text${loadingTextClass}">${escapeHtml(loadingText)}</span>
        <span class="load"></span>
      </div>
    </div>
  `;
}

function buildDownloadButton({ id, label, accent, disabled = false, done = false }) {
  return `
    <button type="button" id="${id}" class="download-button accent-${accent} ${done ? "done" : ""}" ${disabled ? "disabled" : ""}>
      <span class="download-circle">
        ${done ? icon("check") : icon("download")}
      </span>
      <span class="download-text">${escapeHtml(done ? t("common.downloadDone") : label)}</span>
    </button>
  `;
}

function buildHomeCard(card) {
  return `
    <a class="feature-card accent-${card.accent}" href="${card.href}">
      <span class="feature-circle">
        <span class="feature-number">${card.number}</span>
      </span>
      <span class="feature-icon">${icon(card.icon)}</span>
      <h2 class="feature-title">${escapeHtml(card.title)}</h2>
      <p class="feature-description">${escapeHtml(card.description)}</p>
      <span class="feature-action">
        ${escapeHtml(card.action)}
        ${icon("arrow-right")}
      </span>
    </a>
  `;
}

function renderHome(root) {
  const homeMessages = uiMessages[getLanguage()].home;
  const cards = [
    {
      number: "01",
      accent: "violet",
      title: homeMessages.generateTitle,
      description: homeMessages.generateDescription,
      action: homeMessages.generateAction,
      href: "/generate",
      icon: "database",
    },
    {
      number: "02",
      accent: "emerald",
      title: homeMessages.anonymizeTitle,
      description: homeMessages.anonymizeDescription,
      action: homeMessages.anonymizeAction,
      href: "/anonymize",
      icon: "shield",
    },
    {
      number: "03",
      accent: "orange",
      title: homeMessages.similarTitle,
      description: homeMessages.similarDescription,
      action: homeMessages.similarAction,
      href: "/similar",
      icon: "copy",
    },
  ];

  root.innerHTML = renderLayout(`
    <section class="home-hero">
      <h1 class="home-title">Synthetic Data Generator & Anonymizer</h1>
    </section>
    <section class="home-cards">
      ${cards.map(buildHomeCard).join("")}
    </section>
  `);
  attachCommonControls(() => renderHome(root));
}

function renderGenerate(root) {
  const state = {
    templates: [],
    selections: {},
    locale: getDefaultFakerLocale(),
    localeDirty: false,
    loading: true,
    running: false,
    error: "",
    success: "",
  };

  const render = () => {
    const generateMessages = uiMessages[getLanguage()].generate;
    const selectedItems = state.templates.filter((item) => state.selections[item.template_id]?.enabled);
    const totalRows = selectedItems.reduce((sum, item) => sum + state.selections[item.template_id].row_count, 0);
    const formatLabel = selectedItems.length > 1 ? "ZIP" : "CSV";

    root.innerHTML = renderLayout(`
      ${buildPageIntro({
        accent: "violet",
        title: generateMessages.title,
        subtitle: generateMessages.subtitle,
      })}
      ${buildStatsCards([
        { accent: "violet", label: generateMessages.selectedTables, value: String(selectedItems.length) },
        { accent: "violet", label: generateMessages.totalRows, value: formatCount(totalRows) },
        { accent: "violet", label: generateMessages.format, value: formatLabel },
      ])}
      ${
        state.loading
          ? `<div class="empty-area">${escapeHtml(generateMessages.loadingTemplates)}</div>`
          : `
            <section class="locale-panel accent-violet">
              <div class="locale-panel-copy">
                <h2 class="section-title">${escapeHtml(generateMessages.localeTitle)}</h2>
                <p class="locale-description">${escapeHtml(generateMessages.localeSubtitle)}</p>
              </div>
              <div class="locale-grid">
                ${fakerLocaleOptions
                  .map(
                    (option) => `
                      <button
                        type="button"
                        class="locale-option ${state.locale === option.value ? "active" : ""}"
                        data-action="set-faker-locale"
                        data-locale="${option.value}"
                        aria-pressed="${state.locale === option.value ? "true" : "false"}"
                      >
                        <span class="locale-option-label">${escapeHtml(getFakerLocaleLabel(option.value))}</span>
                      </button>
                    `,
                  )
                  .join("")}
              </div>
            </section>
            <section class="template-list">
              ${state.templates
                .map((template) => {
                  const selection = state.selections[template.template_id];
                  const ui = getTemplateUi(template.template_id);
                  const chips = template.preview_columns || [];

                  return `
                    <article class="template-card ${selection.enabled ? "active" : ""}">
                      <div class="template-row">
                        <div class="template-main">
                          <div class="template-title-row">
                            <button
                              type="button"
                              class="template-toggle"
                              data-action="toggle-template"
                              data-template-id="${template.template_id}"
                              aria-pressed="${selection.enabled ? "true" : "false"}"
                            >
                              ${selection.enabled ? icon("check") : ""}
                            </button>
                            <h3 class="template-title">${escapeHtml(ui.label || template.name)}</h3>
                          </div>
                          <p class="template-description">${escapeHtml(ui.description || template.description || "")}</p>
                          <div class="chip-list">
                            ${chips.map((column) => `<span class="field-chip">${escapeHtml(column)}</span>`).join("")}
                          </div>
                        </div>
                        ${
                          selection.enabled
                            ? `
                              <div class="count-stepper">
                                <button type="button" data-action="decrease-row-count" data-template-id="${template.template_id}">-</button>
                                <input
                                  type="number"
                                  min="1"
                                  max="10000"
                                  value="${selection.row_count}"
                                  data-action="set-row-count"
                                  data-template-id="${template.template_id}"
                                  aria-label="${escapeHtml(generateMessages.rowCountAriaLabel)}"
                                />
                                <button type="button" data-action="increase-row-count" data-template-id="${template.template_id}">+</button>
                              </div>
                            `
                            : ""
                        }
                      </div>
                    </article>
                  `;
                })
                .join("")}
            </section>
            <div class="center-actions">
              ${
                selectedItems.length > 0
                  ? buildDownloadButton({
                      id: "generate-run",
                      label: state.running ? generateMessages.running : generateMessages.run,
                      accent: "violet",
                      disabled: state.running,
                      done: Boolean(state.success) && !state.running,
                    })
                  : `<div class="empty-area empty-action">${escapeHtml(generateMessages.emptySelection)}</div>`
              }
            </div>
          `
      }
      ${buildNotice("error", state.error)}
      ${buildLoadingOverlay(state.loading || state.running, "violet")}
    `);

    attachCommonControls(() => {
      if (!state.localeDirty) {
        state.locale = getDefaultFakerLocale();
      }
      render();
    });

    if (state.loading) {
      return;
    }

    document.querySelectorAll("[data-action='set-faker-locale']").forEach((element) => {
      element.addEventListener("click", () => {
        state.locale = element.dataset.locale || getDefaultFakerLocale();
        state.localeDirty = true;
        state.success = "";
        render();
      });
    });

    document.querySelectorAll("[data-action='toggle-template']").forEach((element) => {
      element.addEventListener("click", () => {
        const templateId = element.dataset.templateId;
        state.selections[templateId].enabled = !state.selections[templateId].enabled;
        state.error = "";
        state.success = "";
        render();
      });
    });

    document.querySelectorAll("[data-action='decrease-row-count']").forEach((element) => {
      element.addEventListener("click", () => {
        const templateId = element.dataset.templateId;
        state.selections[templateId].row_count = Math.max(1, state.selections[templateId].row_count - 10);
        state.success = "";
        render();
      });
    });

    document.querySelectorAll("[data-action='increase-row-count']").forEach((element) => {
      element.addEventListener("click", () => {
        const templateId = element.dataset.templateId;
        state.selections[templateId].row_count = Math.min(10000, state.selections[templateId].row_count + 10);
        state.success = "";
        render();
      });
    });

    document.querySelectorAll("[data-action='set-row-count']").forEach((element) => {
      element.addEventListener("input", () => {
        const templateId = element.dataset.templateId;
        const nextValue = Number.parseInt(element.value, 10);
        state.selections[templateId].row_count = Number.isFinite(nextValue)
          ? Math.min(10000, Math.max(1, nextValue))
          : 1;
        state.success = "";
      });
      element.addEventListener("change", render);
    });

    const runButton = document.getElementById("generate-run");
    if (runButton) {
      runButton.addEventListener("click", async () => {
        const items = state.templates
          .filter((item) => state.selections[item.template_id]?.enabled)
          .map((item) => ({
            template_id: item.template_id,
            row_count: state.selections[item.template_id].row_count,
          }));

        const missingDependencies = findMissingTemplateDependencies(items.map((item) => item.template_id));
        if (missingDependencies.length > 0) {
          state.error = formatGenerateDependencyError(missingDependencies);
          state.success = "";
          render();
          return;
        }

        const orderedItems = sortGenerateItemsByDependencies(items);

        state.running = true;
        state.error = "";
        state.success = "";
        render();
        try {
          const response = await fetch(`${apiBase}/generate/run`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ items: orderedItems, locale: state.locale }),
          });
          const payload = await parseApiResponse(response);
          if (payload.result_format === "zip_base64") {
            downloadBase64File(payload.archive_base64, payload.file_name, "application/zip");
          } else {
            downloadBase64File(payload.content_base64, payload.file_name, "text/csv;charset=utf-8");
          }
          state.success = "done";
        } catch (error) {
          state.error = error.message;
        } finally {
          state.running = false;
          render();
        }
      });
    }
  };

  fetch(`${apiBase}/generate/templates`)
    .then(parseApiResponse)
    .then((payload) => {
      state.templates = payload.items || [];
      state.selections = Object.fromEntries(
        state.templates.map((item) => [
          item.template_id,
          {
            enabled: false,
            row_count: 100,
          },
        ]),
      );
    })
    .catch((error) => {
      state.error = error.message;
    })
    .finally(() => {
      state.loading = false;
      render();
    });

  render();
}

function renderAnonymize(root) {
  const methodKeys = ["keep", "mask", "redact", "pseudonymize", "generalize_year"];

  const state = {
    uploading: false,
    running: false,
    showPreview: false,
    error: "",
    success: "",
    upload: null,
    rules: {},
  };
  let dragDepth = 0;

  const uploadCsvFile = async (file) => {
    if (!file) {
      return;
    }

    if (file.size > MAX_UPLOAD_BYTES) {
      state.error = t("anonymize.fileTooLarge", { size: formatMegabytes(MAX_UPLOAD_BYTES) });
      render();
      return;
    }

    state.uploading = true;
    state.error = "";
    state.success = "";
    render();
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("has_header", "true");
      const response = await fetch(`${apiBase}/anonymize/upload`, {
        method: "POST",
        body: formData,
      });
      const payload = await parseApiResponse(response);
      state.upload = payload;
      state.rules = Object.fromEntries(
        payload.columns.map((column) => [column.name, "keep"]),
      );
    } catch (error) {
      state.error = error.message;
    } finally {
      state.uploading = false;
      render();
    }
  };

  const resetUpload = () => {
    state.upload = null;
    state.rules = {};
    state.error = "";
    state.success = "";
    state.uploading = false;
    state.running = false;
    state.showPreview = false;
    dragDepth = 0;
  };

  const render = () => {
    const anonymizeMessages = uiMessages[getLanguage()].anonymize;
    root.innerHTML = renderLayout(`
      ${buildPageIntro({
        accent: "emerald",
        title: anonymizeMessages.title,
        subtitle: anonymizeMessages.subtitle,
      })}
      ${
        !state.upload
          ? `
            <div class="upload-wrapper">
              <label class="upload-dropzone accent-emerald" id="upload-dropzone">
                <div class="upload-panel">
                  <span class="upload-circle">${icon("upload")}</span>
                  <h3 class="upload-title">${escapeHtml(anonymizeMessages.uploadTitle)}</h3>
                  <p class="upload-hint">${escapeHtml(anonymizeMessages.uploadHint)}</p>
                  <div class="upload-badge-text">${escapeHtml(t("anonymize.uploadBadge", { size: formatMegabytes(MAX_UPLOAD_BYTES) }))}</div>
                </div>
                <input type="file" id="csv-upload" accept=".csv,text/csv" />
              </label>
            </div>
          `
          : `
            <article class="info-card accent-emerald">
              <span class="info-orb"></span>
              <div class="info-card-row">
                <div>
                  <h3 class="info-title">${escapeHtml(state.upload.file_name)}</h3>
                  <p class="info-meta">${escapeHtml(t("anonymize.infoMeta", {
                    columnCount: formatCount(state.upload.column_count),
                    rowCount: formatCount(state.upload.row_count),
                  }))}</p>
                </div>
                <button type="button" class="preview-button accent-emerald" id="toggle-preview">
                  <span class="preview-button-icon">${state.showPreview ? icon("eye-off") : icon("eye")}</span>
                  <span class="preview-button-label">${escapeHtml(state.showPreview ? anonymizeMessages.hidePreview : anonymizeMessages.showPreview)}</span>
                </button>
              </div>
              <div class="preview-panel ${state.showPreview ? "is-open" : ""}" id="preview-panel" aria-hidden="${state.showPreview ? "false" : "true"}">
                <div class="preview-panel-inner">
                      <table>
                        <thead>
                          <tr>${state.upload.columns.map((column) => `<th>${escapeHtml(column.name)}</th>`).join("")}</tr>
                        </thead>
                        <tbody>
                          ${(state.upload.preview_rows || [])
                            .map(
                              (row) => `
                                <tr>
                                  ${state.upload.columns
                                    .map((column) => `<td>${escapeHtml(row[column.name] == null ? "" : row[column.name])}</td>`)
                                    .join("")}
                                </tr>
                              `,
                            )
                            .join("")}
                        </tbody>
                      </table>
                      ${
                        (state.upload.preview_rows || []).length > 0
                          ? `<p class="preview-note">${escapeHtml(t("anonymize.previewNote", {
                            shown: formatCount(state.upload.preview_rows.length),
                            total: formatCount(state.upload.row_count),
                          }))}</p>`
                          : ""
                      }
                </div>
              </div>
            </article>
            <section class="rules-section">
              <h2 class="section-title">${escapeHtml(anonymizeMessages.sectionTitle)}</h2>
              ${state.upload.columns
                .map((column) => `
                    <article class="rule-card">
                      <div class="rule-card-body">
                        <h3 class="rule-title">${escapeHtml(column.name)}</h3>
                        <div class="method-list">
                          ${methodKeys
                            .map((methodKey) => {
                              const compatibilityMessage = column?.unsupported_methods?.[methodKey] || "";
                              return `
                                <button
                                  type="button"
                                  class="method-chip ${state.rules[column.name] === methodKey ? `active ${methodKey}` : ""} ${compatibilityMessage ? "unsupported" : ""}"
                                  data-action="set-rule"
                                  data-column-name="${escapeHtml(column.name)}"
                                  data-method="${methodKey}"
                                  data-method-error="${escapeHtml(compatibilityMessage)}"
                                  title="${escapeHtml(compatibilityMessage)}"
                                >
                                  ${escapeHtml(getMethodLabel(methodKey))}
                                </button>
                              `;
                            })
                            .join("")}
                        </div>
                      </div>
                    </article>
                  `)
                .join("")}
            </section>
            <div class="center-actions spaced">
              <button type="button" class="secondary-action" id="upload-another">${escapeHtml(anonymizeMessages.uploadAnother)}</button>
              ${buildDownloadButton({
                id: "run-anonymize",
                label: state.running ? anonymizeMessages.running : anonymizeMessages.run,
                accent: "emerald",
                disabled: state.running,
                done: Boolean(state.success) && !state.running,
              })}
            </div>
          `
      }
      ${buildNotice("error", state.error)}
      ${buildLoadingOverlay(state.uploading || state.running, "emerald")}
    `);

    attachCommonControls(render);

    if (!state.upload) {
      const uploadDropzone = document.getElementById("upload-dropzone");
      const uploadInput = document.getElementById("csv-upload");
      if (uploadDropzone) {
        const setDragState = (active) => {
          uploadDropzone.classList.toggle("is-dragover", active);
        };

        uploadDropzone.addEventListener("dragenter", (event) => {
          event.preventDefault();
          dragDepth += 1;
          setDragState(true);
        });

        uploadDropzone.addEventListener("dragover", (event) => {
          event.preventDefault();
          if (event.dataTransfer) {
            event.dataTransfer.dropEffect = "copy";
          }
          setDragState(true);
        });

        uploadDropzone.addEventListener("dragleave", (event) => {
          event.preventDefault();
          dragDepth = Math.max(0, dragDepth - 1);
          if (dragDepth === 0) {
            setDragState(false);
          }
        });

        uploadDropzone.addEventListener("drop", async (event) => {
          event.preventDefault();
          dragDepth = 0;
          setDragState(false);
          const file = event.dataTransfer?.files && event.dataTransfer.files[0];
          await uploadCsvFile(file);
        });
      }

      if (uploadInput) {
        uploadInput.addEventListener("change", async (event) => {
          const file = event.target.files && event.target.files[0];
          await uploadCsvFile(file);
        });
      }
      return;
    }

    const togglePreviewButton = document.getElementById("toggle-preview");
    if (togglePreviewButton) {
      const previewPanel = document.getElementById("preview-panel");
      const previewButtonIcon = togglePreviewButton.querySelector(".preview-button-icon");
      const previewButtonLabel = togglePreviewButton.querySelector(".preview-button-label");
      togglePreviewButton.addEventListener("click", () => {
        state.showPreview = !state.showPreview;
        if (previewPanel) {
          previewPanel.classList.toggle("is-open", state.showPreview);
          previewPanel.setAttribute("aria-hidden", state.showPreview ? "false" : "true");
        }
        if (previewButtonIcon) {
          previewButtonIcon.innerHTML = state.showPreview ? icon("eye-off") : icon("eye");
        }
        if (previewButtonLabel) {
          previewButtonLabel.textContent = state.showPreview ? t("anonymize.hidePreview") : t("anonymize.showPreview");
        }
      });
    }

    document.querySelectorAll("[data-action='set-rule']").forEach((element) => {
      element.addEventListener("click", () => {
        const methodError = element.dataset.methodError || "";
        if (methodError) {
          state.error = methodError;
          state.success = "";
          render();
          return;
        }
        state.rules[element.dataset.columnName] = element.dataset.method;
        state.success = "";
        state.error = "";
        render();
      });
    });

    const uploadAnotherButton = document.getElementById("upload-another");
    if (uploadAnotherButton) {
      uploadAnotherButton.addEventListener("click", () => {
        resetUpload();
        render();
      });
    }

    const runButton = document.getElementById("run-anonymize");
    if (runButton) {
      runButton.addEventListener("click", async () => {
        state.running = true;
        state.error = "";
        state.success = "";
        render();
        try {
          const response = await fetch(`${apiBase}/anonymize/run`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              upload_id: state.upload.upload_id,
              rules: state.upload.columns.map((column) => ({
                column_name: column.name,
                method: state.rules[column.name] || "keep",
                params: {},
              })),
            }),
          });
          const payload = await parseApiResponse(response);
          downloadBase64File(payload.content_base64, payload.file_name, "text/csv;charset=utf-8");
          state.success = "done";
        } catch (error) {
          state.error = error.message;
        } finally {
          state.running = false;
          render();
        }
      });
    }
  };

  render();
}

function renderSimilar(root) {
  const similarMessages = uiMessages[getLanguage()].similar;
  root.innerHTML = renderLayout(`
    ${buildPageIntro({
      accent: "orange",
      title: similarMessages.title,
      subtitle: similarMessages.subtitle,
    })}
    <div class="upload-wrapper">
      <article class="upload-panel static accent-orange">
        <span class="upload-circle">${icon("copy")}</span>
        <h3 class="upload-title">${escapeHtml(similarMessages.unavailableTitle)}</h3>
        <p class="upload-hint">${escapeHtml(similarMessages.unavailableHint)}</p>
        <div class="upload-badge-text orange">${escapeHtml(similarMessages.soon)}</div>
      </article>
    </div>
  `);
  attachCommonControls(() => renderSimilar(root));
}

function startTypewriterLoop() {
  if (window.__sdaTypewriterStarted) {
    return;
  }

  window.__sdaTypewriterStarted = true;
  const state = {
    phraseIndex: 0,
    charIndex: 0,
    deleting: false,
    pauseUntil: 0,
  };

  window.setInterval(() => {
    const node = document.querySelector(".js-typewriter");
    if (!node) {
      return;
    }

    const phrases = getTypewriterPhrases();
    if (state.phraseIndex >= phrases.length) {
      state.phraseIndex = 0;
      state.charIndex = 0;
      state.deleting = false;
    }
    const phrase = phrases[state.phraseIndex];
    const now = Date.now();

    if (now >= state.pauseUntil) {
      if (!state.deleting && state.charIndex < phrase.length) {
        state.charIndex += 1;
      } else if (!state.deleting && state.charIndex === phrase.length) {
        state.pauseUntil = now + 1500;
        state.deleting = true;
      } else if (state.deleting && state.charIndex > 0) {
        state.charIndex -= 1;
      } else if (state.deleting && state.charIndex === 0) {
        state.deleting = false;
        state.phraseIndex = (state.phraseIndex + 1) % phrases.length;
      }
    }

    node.textContent = phrase.slice(0, state.charIndex);
  }, 80);
}

syncDocumentMetadata();
startTypewriterLoop();

const root = document.getElementById("app");
const page = document.body.dataset.page;

if (page === "generate") {
  renderGenerate(root);
} else if (page === "anonymize") {
  renderAnonymize(root);
} else if (page === "similar") {
  renderSimilar(root);
} else {
  renderHome(root);
}
