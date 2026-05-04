"use client";

import { useEffect, useMemo, useState } from "react";

import { DotGridBackground } from "@/components/dot-grid-background";
import { FullscreenLoaderOverlay } from "@/components/fullscreen-loader-overlay";
import { useLanguage } from "@/components/language-provider";
import {
  ApiError,
  fetchGenerateDomains,
  fetchGenerateTemplateDetail,
  fetchGenerateTemplates,
  runGenerate,
} from "@/lib/api";
import type {
  GenerateDomainId,
  GenerateDomainSummary,
  GenerateRunResponse,
  GenerateTemplateDetail,
  GenerateTemplateSummary,
} from "@/lib/api-types";
import { downloadBase64File } from "@/lib/download";

const copy = {
  ru: {
    eyebrow: "Generate",
    title: "Создавайте связанные синтетические датасеты без ручной рутины.",
    description:
      "Выберите один или несколько шаблонов, настройте объём и язык, затем скачайте CSV или ZIP с согласованными таблицами.",
    locale: "Язык / регион датасета",
    localeRu: "Русский",
    localeEn: "English",
    domain: "Сценарий применения",
    loadError: "Не удалось загрузить шаблоны.",
    generate: "Сгенерировать",
    generating: "Генерация...",
    selected: "Выбрано шаблонов",
    rows: "Строк",
    columns: "Колонки",
    result: "Результат",
    totalRows: "Всего строк",
    download: "Скачать",
    noSelection: "Выберите хотя бы один шаблон.",
    requestFailed: "Не удалось выполнить запрос.",
    loadingTemplates: "Загрузка шаблонов...",
  },
  en: {
    eyebrow: "Generate",
    title: "Build connected synthetic datasets without manual busywork.",
    description:
      "Pick one or more templates, tune row volume and language, then download a CSV or ZIP with coherent tables.",
    locale: "Dataset language / region",
    localeRu: "Russian",
    localeEn: "English",
    domain: "Use case",
    loadError: "Failed to load templates.",
    generate: "Generate",
    generating: "Generating...",
    selected: "Selected templates",
    rows: "Rows",
    columns: "Columns",
    result: "Result",
    totalRows: "Total rows",
    download: "Download",
    noSelection: "Select at least one template.",
    requestFailed: "Request failed.",
    loadingTemplates: "Loading templates...",
  },
} as const;

const domainCopy: Record<GenerateDomainId, Record<"ru" | "en", { name: string; description: string }>> = {
  ecommerce: {
    ru: {
      name: "Электронная коммерция",
      description: "Каталоги товаров, заказы и платежи для интернет-магазинов.",
    },
    en: {
      name: "E-commerce",
      description: "Product catalogs, orders, and payments for online stores.",
    },
  },
  fintech: {
    ru: {
      name: "Финтех",
      description: "Финансовые продукты, операции и клиентские сценарии.",
    },
    en: {
      name: "Fintech",
      description: "Financial products, operations, and customer scenarios.",
    },
  },
  shops: {
    ru: {
      name: "Продуктовые магазины",
      description: "Продукты, напитки и товары повседневного спроса для розницы.",
    },
    en: {
      name: "Grocery stores",
      description: "Food, drinks, and everyday retail goods.",
    },
  },
  logistics: {
    ru: {
      name: "Логистика",
      description: "Доставки, маршруты, склады и грузовые услуги.",
    },
    en: {
      name: "Logistics",
      description: "Deliveries, routes, warehouses, and cargo services.",
    },
  },
  education: {
    ru: {
      name: "Образование",
      description: "Курсы, учебные модули и активности студентов.",
    },
    en: {
      name: "Education",
      description: "Courses, learning modules, and student activities.",
    },
  },
  crm: {
    ru: {
      name: "CRM",
      description: "Продажи, лиды, лицензии и клиентские коммуникации.",
    },
    en: {
      name: "CRM",
      description: "Sales, leads, licenses, and customer communication.",
    },
  },
};

const templateCopy = {
  users: {
    ru: {
      name: "Пользователи",
      description: "Синтетические профили пользователей.",
    },
    en: {
      name: "Users",
      description: "Synthetic user profiles.",
    },
  },
  orders: {
    ru: {
      name: "Заказы",
      description: "Синтетическая история заказов, связанная с пользователями и товарами.",
    },
    en: {
      name: "Orders",
      description: "Synthetic order history linked to users and products.",
    },
  },
  payments: {
    ru: {
      name: "Платежи",
      description: "Синтетические платёжные операции, связанные с заказами.",
    },
    en: {
      name: "Payments",
      description: "Synthetic payment operations linked to orders.",
    },
  },
  products: {
    ru: {
      name: "Товары",
      description: "Синтетический каталог товаров.",
    },
    en: {
      name: "Products",
      description: "Synthetic product catalog.",
    },
  },
  support_tickets: {
    ru: {
      name: "Тикеты поддержки",
      description: "Синтетические обращения в поддержку и история их обработки.",
    },
    en: {
      name: "Support tickets",
      description: "Synthetic support requests and processing history.",
    },
  },
} as const;

type SelectionState = Record<string, number>;

export function GenerateFlow() {
  const { language } = useLanguage();
  const t = copy[language];
  const [templates, setTemplates] = useState<GenerateTemplateSummary[]>([]);
  const [domains, setDomains] = useState<GenerateDomainSummary[]>([]);
  const [details, setDetails] = useState<Record<string, GenerateTemplateDetail>>({});
  const [selection, setSelection] = useState<SelectionState>({});
  const [locale, setLocale] = useState<"ru_RU" | "en_US">(language === "en" ? "en_US" : "ru_RU");
  const [domain, setDomain] = useState<GenerateDomainId>("ecommerce");
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<GenerateRunResponse | null>(null);
  const loaderWord = isLoading ? "Loading" : isRunning ? "Generating" : null;

  useEffect(() => {
    void (async () => {
      try {
        const [templatesResponse, domainsResponse] = await Promise.all([
          fetchGenerateTemplates(),
          fetchGenerateDomains(),
        ]);
        setTemplates(templatesResponse.items);
        setDomains(domainsResponse.items);
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.message : t.loadError);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [t.loadError]);

  const selectedTemplates = useMemo(
    () => templates.filter((item) => selection[item.template_id] && selection[item.template_id] > 0),
    [selection, templates],
  );

  const getTemplateName = (templateId: GenerateTemplateSummary["template_id"], fallback?: string | null) =>
    templateCopy[templateId][language].name ?? fallback ?? templateId;

  const getTemplateDescription = (templateId: GenerateTemplateSummary["template_id"], fallback?: string | null) =>
    templateCopy[templateId][language].description ?? fallback ?? "";

  const getDomainName = (domainId: GenerateDomainId, fallback?: string | null) =>
    domainCopy[domainId][language].name ?? fallback ?? domainId;

  const getDomainDescription = (domainId: GenerateDomainId, fallback?: string | null) =>
    domainCopy[domainId][language].description ?? fallback ?? "";

  const toggleTemplate = async (template: GenerateTemplateSummary) => {
    setError(null);
    setResult(null);

    if (selection[template.template_id]) {
      const next = { ...selection };
      delete next[template.template_id];
      setSelection(next);
      return;
    }

    setSelection((current) => ({ ...current, [template.template_id]: 250 }));

    if (!details[template.template_id]) {
      try {
        const detail = await fetchGenerateTemplateDetail(template.template_id);
        setDetails((current) => ({ ...current, [template.template_id]: detail }));
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.message : t.loadError);
      }
    }
  };

  const updateRowCount = (templateId: string, value: string) => {
    const parsed = Number(value);
    setResult(null);
    setSelection((current) => ({
      ...current,
      [templateId]: Number.isFinite(parsed) && parsed > 0 ? Math.min(10000, parsed) : 1,
    }));
  };

  const adjustRowCount = (templateId: string, delta: number) => {
    setResult(null);
    setSelection((current) => {
      const currentValue = current[templateId] ?? 1;
      return {
        ...current,
        [templateId]: Math.min(10000, Math.max(1, currentValue + delta)),
      };
    });
  };

  const handleRun = async () => {
    if (selectedTemplates.length === 0) {
      setError(t.noSelection);
      return;
    }

    setIsRunning(true);
    setError(null);

    try {
      const response = await runGenerate({
        items: selectedTemplates.map((item) => ({
          template_id: item.template_id,
          row_count: selection[item.template_id],
        })),
        locale,
        domain,
      });
      setResult(response);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t.requestFailed);
    } finally {
      setIsRunning(false);
    }
  };

  const downloadResult = () => {
    if (!result) {
      return;
    }

    if (result.result_format === "zip_base64" && result.archive_base64) {
      downloadBase64File(result.archive_base64, result.file_name, "application/zip");
      return;
    }

    if (result.content_base64) {
      downloadBase64File(result.content_base64, result.file_name, "text/csv;charset=utf-8");
    }
  };

  return (
    <main className="tool-page tool-page--interactive">
      <FullscreenLoaderOverlay visible={Boolean(loaderWord)} word={loaderWord} />
      <div className="tool-page__background" aria-hidden="true">
        <DotGridBackground className="tool-page__dot-grid" />
      </div>
      <div className="tool-page__overlay" aria-hidden="true" />

      <section className="tool-page__hero page-container">
        <p className="eyebrow">{t.eyebrow}</p>
        <h1>{t.title}</h1>
        <p>{t.description}</p>
      </section>

      <section className="page-container tool-layout">
        <div className="tool-surface">
          <div className="tool-toolbar tool-toolbar--stack">
            <div className="tool-toolbar__group tool-toolbar__group--left">
              <span className="field-label">{t.locale}</span>
              <div className="segmented-control">
                <button
                  type="button"
                  className={`segmented-control__button${locale === "ru_RU" ? " is-active" : ""}`}
                  onClick={() => setLocale("ru_RU")}
                >
                  {t.localeRu}
                </button>
                <button
                  type="button"
                  className={`segmented-control__button${locale === "en_US" ? " is-active" : ""}`}
                  onClick={() => setLocale("en_US")}
                >
                  {t.localeEn}
                </button>
              </div>
            </div>
            <div className="tool-toolbar__group tool-toolbar__group--left">
              <span className="field-label">{t.domain}</span>
              <div className="domain-grid">
                {domains.map((item) => {
                  const active = domain === item.domain_id;

                  return (
                    <button
                      key={item.domain_id}
                      type="button"
                      className={`domain-option${active ? " is-active" : ""}`}
                      onClick={() => {
                        setDomain(item.domain_id);
                        setResult(null);
                      }}
                    >
                      <strong>{getDomainName(item.domain_id, item.name)}</strong>
                      <span>{getDomainDescription(item.domain_id, item.description)}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
          <div className="template-grid template-grid--stack">
            {templates.map((template) => {
              const active = Boolean(selection[template.template_id]);
              const detail = details[template.template_id];
              const previewColumns = detail?.columns.map((item) => item.name) ?? template.preview_columns ?? [];

              return (
                <article key={template.template_id} className={`template-card${active ? " is-active" : ""}`}>
                  <button type="button" className="template-card__toggle" onClick={() => void toggleTemplate(template)}>
                    <div>
                      <span className="template-card__tag">{template.template_id}</span>
                      <h2>{getTemplateName(template.template_id, template.name)}</h2>
                      <p>{getTemplateDescription(template.template_id, template.description)}</p>
                    </div>
                    <span className="template-card__state" aria-hidden="true">{active ? "−" : "+"}</span>
                  </button>

                  <div className="template-card__meta">
                    <div className="chip-list">
                      {previewColumns.map((column) => (
                        <span key={column} className="chip">
                          {column}
                        </span>
                      ))}
                    </div>

                    {active ? (
                      <label className="input-block">
                        <span className="field-label">{t.rows}</span>
                        <div className="row-stepper">
                          <button
                            type="button"
                            className="row-stepper__button"
                            onClick={() => adjustRowCount(template.template_id, -10)}
                          >
                            -10
                          </button>
                          <input
                            type="number"
                            min={1}
                            max={10000}
                            value={selection[template.template_id]}
                            onChange={(event) => updateRowCount(template.template_id, event.target.value)}
                            className="row-stepper__input"
                          />
                          <button
                            type="button"
                            className="row-stepper__button"
                            onClick={() => adjustRowCount(template.template_id, 10)}
                          >
                            +10
                          </button>
                        </div>
                      </label>
                    ) : null}
                  </div>
                </article>
              );
            })}
          </div>
        </div>

        <aside className="tool-sidebar">
          <article className="sidebar-card">
            <span className="field-label">{t.selected}</span>
            <strong className="sidebar-card__big">{selectedTemplates.length}</strong>
            <div className="sidebar-list">
              {selectedTemplates.map((template) => (
                <div key={template.template_id} className="sidebar-list__row">
                  <span>{getTemplateName(template.template_id, template.name)}</span>
                  <strong>{selection[template.template_id]}</strong>
                </div>
              ))}
            </div>
            <button
              type="button"
              className="button button--primary button--wide sidebar-card__action"
              onClick={handleRun}
              disabled={isRunning}
            >
              {t.generate}
            </button>
            {error ? <p className="surface-error">{error}</p> : null}
          </article>

          {result ? (
            <article className="sidebar-card sidebar-card--result">
              <span className="field-label">{t.result}</span>
              <strong className="sidebar-card__big">{result.file_name}</strong>
              <div className="sidebar-list">
                <div className="sidebar-list__row">
                  <span>{t.totalRows}</span>
                  <strong>{result.total_rows}</strong>
                </div>
                {result.generated_files.map((item) => (
                  <div key={item.file_name} className="sidebar-list__row">
                    <span>{item.file_name}</span>
                    <strong>{item.row_count}</strong>
                  </div>
                ))}
              </div>
              <button
                type="button"
                className="button button--primary button--wide sidebar-card__download"
                onClick={downloadResult}
              >
                {t.download}
              </button>
            </article>
          ) : null}
        </aside>
      </section>
    </main>
  );
}
