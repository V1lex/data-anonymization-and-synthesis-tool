const apiBase = window.SDA_API_BASE || "/api/v1";
const templateDependencies = {
  users: [],
  orders: ["users"],
  payments: ["users", "orders"],
  products: [],
  support_tickets: ["users"],
};
const templateLabels = {
  users: "Пользователи",
  orders: "Заказы",
  payments: "Платежи",
  products: "Товары",
  support_tickets: "Тикеты поддержки",
};
const methodLabels = {
  keep: "Оставить",
  mask: "Маскировать",
  redact: "Скрыть",
  pseudonymize: "Псевдонимизировать",
  generalize_year: "Оставить год",
};
const inferredTypeLabels = {
  string: "строка",
  number: "число",
  date: "дата",
  boolean: "логический",
};

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
    const message = payload && typeof payload.message === "string" ? payload.message : "Не удалось выполнить запрос.";
    throw new Error(message);
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
  link.click();
  URL.revokeObjectURL(url);
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
    if (visited.has(templateId)) {
      return;
    }
    if (visiting.has(templateId)) {
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
    .map((item) => templateLabels[item.dependencyId] || item.dependencyId);

  return `Для генерации "${templateLabels[firstMissing.templateId] || firstMissing.templateId}" также выберите: ${requiredTemplateIds.join(", ")}.`;
}

function renderShell({ title, subtitle, accent, backHref = null }) {
  return `
    <div class="page">
      <header class="topbar">
        <a class="brand" href="/">
          <span class="brand-mark">S</span>
          <span>Генератор и анонимизатор данных</span>
        </a>
      </header>
      <section class="hero">
        ${backHref ? `<a class="back-link" href="${backHref}">← Назад</a>` : ""}
        <h1>${escapeHtml(title)}</h1>
        <p>${escapeHtml(subtitle)}</p>
      </section>
      <section id="page-content" class="${accent ? `accent-${accent}` : ""}"></section>
    </div>
  `;
}

function renderHome(root) {
  root.innerHTML = renderShell({
    title: "Генерация, анонимизация и похожие данные",
    subtitle: "Выберите сценарий, настройте параметры и скачайте результат прямо из интерфейса.",
    accent: "violet",
  });

  const content = document.getElementById("page-content");
  const cards = [
    {
      number: "01",
      accent: "violet",
      title: "Генерация",
      description: "Сгенерируйте синтетические CSV-файлы по встроенным шаблонам и скачайте один CSV или ZIP-архив.",
      href: "/generate",
      icon: "▦",
    },
    {
      number: "02",
      accent: "emerald",
      title: "Анонимизация",
      description: "Загрузите CSV, проверьте колонки, выберите правило для каждой и скачайте анонимизированный файл.",
      href: "/anonymize",
      icon: "◌",
    },
    {
      number: "03",
      accent: "orange",
      title: "Похожие данные",
      description: "Перейдите в ветку похожих данных с главной страницы.",
      href: "/similar",
      icon: "≈",
    },
  ];

  content.innerHTML = `
    <div class="cards">
      ${cards
        .map(
          (card) => `
            <a class="action-card card accent-${card.accent}" href="${card.href}">
              <span class="badge">${card.number}</span>
              <span class="action-icon">${card.icon}</span>
              <h2>${card.title}</h2>
              <p>${card.description}</p>
              <span class="action-link">Открыть →</span>
            </a>
          `,
        )
        .join("")}
    </div>
  `;
}

function buildSummaryCards(summaryItems) {
  return `
    <div class="summary-grid">
      ${summaryItems
        .map(
          (item) => `
            <article class="summary-card accent-${item.accent}">
              <span class="summary-dot"></span>
              <div class="summary-label">${item.label}</div>
              <div class="summary-value">${item.value}</div>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderGenerate(root) {
  const state = {
    templates: [],
    selections: {},
    loading: true,
    running: false,
    error: "",
    success: "",
  };

  const render = () => {
    root.innerHTML = renderShell({
      title: "Генерация",
      subtitle: "Выберите один или несколько шаблонов, укажите количество строк и скачайте результат генерации.",
      accent: "violet",
      backHref: "/",
    });

    const content = document.getElementById("page-content");
    const selectedItems = state.templates.filter((item) => state.selections[item.template_id]?.enabled);
    const totalRows = selectedItems.reduce((sum, item) => sum + state.selections[item.template_id].row_count, 0);
    const formatLabel = selectedItems.length > 1 ? "ZIP" : "CSV";

    content.innerHTML = `
      ${buildSummaryCards([
        { accent: "violet", label: "Выбрано таблиц", value: String(selectedItems.length) },
        { accent: "emerald", label: "Всего строк", value: totalRows.toLocaleString("ru-RU") },
        { accent: "orange", label: "Формат результата", value: formatLabel },
      ])}
      ${
        state.loading
          ? `<article class="panel"><p class="muted">Загрузка шаблонов...</p></article>`
          : `
            <div class="rules-grid">
              ${state.templates
                .map((template) => {
                  const selection = state.selections[template.template_id];
                  const activeClass = selection.enabled ? "active" : "";
                  const previewChips = (template.preview_columns || [])
                    .map((column) => `<span class="chip violet">${escapeHtml(column)}</span>`)
                    .join("");
                  return `
                    <article class="panel template-card ${activeClass}">
                      <div class="template-main">
                        <div class="template-top">
                          <button class="toggle" data-action="toggle-template" data-template-id="${template.template_id}">
                            ${selection.enabled ? "✓" : ""}
                          </button>
                          <h2>${escapeHtml(template.name)}</h2>
                        </div>
                        <p class="hint">${escapeHtml(template.description || "")}</p>
                        <div class="chips">${previewChips}</div>
                      </div>
                      <div class="stepper">
                        <button type="button" data-action="decrease-row-count" data-template-id="${template.template_id}" ${
                          !selection.enabled ? "disabled" : ""
                        }>-</button>
                        <input
                          aria-label="количество строк"
                          type="number"
                          min="1"
                          max="10000"
                          value="${selection.row_count}"
                          data-action="set-row-count"
                          data-template-id="${template.template_id}"
                          ${!selection.enabled ? "disabled" : ""}
                        />
                        <button type="button" data-action="increase-row-count" data-template-id="${template.template_id}" ${
                          !selection.enabled ? "disabled" : ""
                        }>+</button>
                      </div>
                    </article>
                  `;
                })
                .join("")}
            </div>
            <div class="button-row">
              <button class="primary-button" id="generate-run" ${selectedItems.length === 0 || state.running ? "disabled" : ""}>
                ${state.running ? "Генерация..." : "Сгенерировать и скачать"}
              </button>
            </div>
            ${state.error ? `<div class="notice error">${escapeHtml(state.error)}</div>` : ""}
            ${state.success ? `<div class="notice success">${escapeHtml(state.success)}</div>` : ""}
            ${selectedItems.length === 0 ? `<p class="empty-state">Выберите хотя бы один шаблон для запуска.</p>` : ""}
          `
      }
    `;

    if (state.loading) {
      return;
    }

    content.querySelectorAll("[data-action='toggle-template']").forEach((element) => {
      element.addEventListener("click", () => {
        const templateId = element.dataset.templateId;
        state.selections[templateId].enabled = !state.selections[templateId].enabled;
        state.error = "";
        state.success = "";
        render();
      });
    });

    content.querySelectorAll("[data-action='decrease-row-count']").forEach((element) => {
      element.addEventListener("click", () => {
        const templateId = element.dataset.templateId;
        const current = state.selections[templateId].row_count;
        state.selections[templateId].row_count = Math.max(1, current - 10);
        render();
      });
    });

    content.querySelectorAll("[data-action='increase-row-count']").forEach((element) => {
      element.addEventListener("click", () => {
        const templateId = element.dataset.templateId;
        const current = state.selections[templateId].row_count;
        state.selections[templateId].row_count = Math.min(10000, current + 10);
        render();
      });
    });

    content.querySelectorAll("[data-action='set-row-count']").forEach((element) => {
      element.addEventListener("input", () => {
        const templateId = element.dataset.templateId;
        const nextValue = Number.parseInt(element.value, 10);
        state.selections[templateId].row_count = Number.isFinite(nextValue)
          ? Math.min(10000, Math.max(1, nextValue))
          : 1;
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
            body: JSON.stringify({ items: orderedItems }),
          });
          const payload = await parseApiResponse(response);
          if (payload.result_format === "zip_base64") {
            downloadBase64File(payload.archive_base64, payload.file_name, "application/zip");
          } else {
            downloadBase64File(payload.content_base64, payload.file_name, "text/csv;charset=utf-8");
          }
          state.success = "Результат успешно скачан.";
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
  const methods = [
    { key: "keep", label: methodLabels.keep },
    { key: "mask", label: methodLabels.mask },
    { key: "redact", label: methodLabels.redact },
    { key: "pseudonymize", label: methodLabels.pseudonymize },
    { key: "generalize_year", label: methodLabels.generalize_year },
  ];

  const state = {
    uploading: false,
    running: false,
    showPreview: false,
    error: "",
    success: "",
    upload: null,
    rules: {},
  };

  const resetUpload = () => {
    state.upload = null;
    state.rules = {};
    state.error = "";
    state.success = "";
    state.uploading = false;
    state.running = false;
    state.showPreview = false;
  };

  const render = () => {
    root.innerHTML = renderShell({
      title: "Анонимизация",
      subtitle: "Загрузите CSV, проверьте колонки и строки предпросмотра, настройте правило для каждой колонки и скачайте результат.",
      accent: "emerald",
      backHref: "/",
    });

    const content = document.getElementById("page-content");
    if (!state.upload) {
      content.innerHTML = `
        <article class="upload-card">
          <label class="upload-zone">
            <span class="upload-round">↑</span>
            <h2>Загрузить CSV</h2>
            <p class="hint">Поддерживается только CSV. Файл сразу разбирается, а предпросмотр показывается на этой же странице.</p>
            <span class="chip orange">.csv</span>
            <input type="file" id="csv-upload" accept=".csv,text/csv" />
          </label>
        </article>
        ${state.error ? `<div class="notice error">${escapeHtml(state.error)}</div>` : ""}
        ${state.uploading ? `<div class="notice success">Загрузка и разбор CSV...</div>` : ""}
      `;

      const uploadInput = document.getElementById("csv-upload");
      if (uploadInput) {
        uploadInput.addEventListener("change", async (event) => {
          const file = event.target.files && event.target.files[0];
          if (!file) {
            return;
          }
          state.uploading = true;
          state.error = "";
          state.success = "";
          render();
          try {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("delimiter", ",");
            formData.append("has_header", "true");
            formData.append("suggest", "true");
            const response = await fetch(`${apiBase}/anonymize/upload`, {
              method: "POST",
              body: formData,
            });
            const payload = await parseApiResponse(response);
            state.upload = payload;
            state.rules = Object.fromEntries(
              payload.columns.map((column) => [column.name, column.suggested_method || "keep"]),
            );
          } catch (error) {
            state.error = error.message;
          } finally {
            state.uploading = false;
            render();
          }
        });
      }
      return;
    }

    const previewHeaders = state.upload.columns.map((column) => column.name);
    const previewRows = state.upload.preview_rows || [];
    content.innerHTML = `
      <article class="panel">
        <div class="file-meta">
          <div>
            <h2>${escapeHtml(state.upload.file_name)}</h2>
            <p class="hint">${state.upload.column_count} колонок · ${state.upload.row_count} строк</p>
          </div>
          <button class="secondary-button" id="toggle-preview">${state.showPreview ? "Скрыть превью" : "Показать превью"}</button>
        </div>
        ${
          state.showPreview
            ? `
              <div class="preview-block">
                <table>
                  <thead>
                    <tr>${previewHeaders.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr>
                  </thead>
                  <tbody>
                    ${previewRows
                      .map(
                        (row) => `
                          <tr>
                            ${previewHeaders
                              .map((column) => `<td>${escapeHtml(row[column] == null ? "" : row[column])}</td>`)
                              .join("")}
                          </tr>
                        `,
                      )
                      .join("")}
                  </tbody>
                </table>
              </div>
            `
            : ""
        }
      </article>
      <section class="rules-grid">
        ${state.upload.columns
          .map(
            (column) => `
              <article class="panel">
                <h2>${escapeHtml(column.name)}</h2>
                <p class="hint">${escapeHtml(inferredTypeLabels[column.inferred_type] || column.inferred_type)} · пример: ${escapeHtml((column.sample_values || []).join(", ") || "нет")}</p>
                <div class="methods">
                  ${methods
                    .map(
                      (method) => `
                        <button
                          class="method-button ${state.rules[column.name] === method.key ? `active ${method.key}` : ""}"
                          data-action="set-rule"
                          data-column-name="${escapeHtml(column.name)}"
                          data-method="${method.key}"
                        >
                          ${method.label}
                        </button>
                      `,
                    )
                    .join("")}
                </div>
              </article>
            `,
          )
          .join("")}
      </section>
      <div class="actions-row">
        <button class="secondary-button" id="upload-another">Загрузить другой файл</button>
        <button class="primary-button" id="run-anonymize" ${state.running ? "disabled" : ""}>
          ${state.running ? "Анонимизация..." : "Анонимизировать и скачать"}
        </button>
      </div>
      ${state.error ? `<div class="notice error">${escapeHtml(state.error)}</div>` : ""}
      ${state.success ? `<div class="notice success">${escapeHtml(state.success)}</div>` : ""}
    `;

    const togglePreviewButton = document.getElementById("toggle-preview");
    if (togglePreviewButton) {
      togglePreviewButton.addEventListener("click", () => {
        state.showPreview = !state.showPreview;
        render();
      });
    }

    document.querySelectorAll("[data-action='set-rule']").forEach((element) => {
      element.addEventListener("click", () => {
        state.rules[element.dataset.columnName] = element.dataset.method;
        state.error = "";
        state.success = "";
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
          state.success = "Анонимизированный CSV успешно скачан.";
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
  root.innerHTML = renderShell({
    title: "Похожие данные",
    subtitle: "Маршрут для ветки похожих данных доступен из главного меню.",
    accent: "orange",
    backHref: "/",
  });
  document.getElementById("page-content").innerHTML = `
    <article class="placeholder-card card">
      <h2 class="section-title">Похожие данные</h2>
      <p class="hint">Этот маршрут доступен из меню на главной странице.</p>
    </article>
  `;
}

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
