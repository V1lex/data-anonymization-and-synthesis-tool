"use client";

import { useMemo, useState } from "react";

import { DotGridBackground } from "@/components/dot-grid-background";
import { FullscreenLoaderOverlay } from "@/components/fullscreen-loader-overlay";
import { useLanguage } from "@/components/language-provider";
import {
  analyzeMultiTableSimilarFiles,
  analyzeSimilarFile,
  ApiError,
  runMultiTableSimilar,
  runSimilar,
} from "@/lib/api";
import type {
  SimilarAnalyzeResponse,
  SimilarMultiAnalyzeResponse,
  SimilarMultiRunResponse,
  SimilarRunResponse,
} from "@/lib/api-types";
import { downloadBase64File } from "@/lib/download";

const copy = {
  ru: {
    eyebrow: "Similar",
    title: "Создайте похожие синтетические данные из CSV",
    description: "",
    singleModeTitle: "Одиночная таблица",
    singleModeDescription: "Один CSV без связей с другими таблицами. Подходит для быстрых похожих выборок.",
    multiModeTitle: "Набор связанных таблиц",
    multiModeDescription: "От 2 до 5 CSV. Система попробует определить ключи и сохранить связи между таблицами.",
    choose: "Выбрать",
    back: "Назад",
    analyze: "Загрузить таблицу",
    analyzeMulti: "Загрузить набор таблиц",
    uploadLimit: "Максимальный размер файла: 5 МБ",
    multiUploadLimit: "От 2 до 5 CSV, каждый до 5 МБ",
    run: "Сгенерировать похожий CSV",
    runMulti: "Сгенерировать ZIP",
    running: "Генерация...",
    download: "Скачать CSV",
    downloadZip: "Скачать ZIP",
    analyzing: "Анализ...",
    rows: "строк",
    columns: "колонок",
    tables: "таблиц",
    relationships: "Связи",
    result: "Результат",
    totalRows: "Всего строк",
    totalColumns: "Всего колонок",
    sourceTables: "Таблицы",
    detectedTypes: "Типы колонок",
    primaryKey: "Первичный ключ",
    noRelationships: "Связи не найдены",
    targetRows: "Строк в результате",
    scale: "Размер датасета",
    scaleHint: "Можно от 0.1 до 5. 1 — как исходные CSV, 2 — в два раза больше.",
    unique: "уникальных",
    analysisFailed: "Не удалось выполнить анализ.",
    synthesisFailed: "Не удалось сгенерировать результат.",
    multiFileCount: "Загрузите минимум два и максимум пять CSV файлов.",
  },
  en: {
    eyebrow: "Similar",
    title: "Create similar synthetic data from CSV",
    description: "",
    singleModeTitle: "Standalone table",
    singleModeDescription: "One CSV without relationships to other tables. Best for quick similar samples.",
    multiModeTitle: "Related table set",
    multiModeDescription: "From 2 to 5 CSV files. The system tries to detect keys and preserve relationships.",
    choose: "Choose",
    back: "Back",
    analyze: "Upload table",
    analyzeMulti: "Upload table set",
    uploadLimit: "Maximum file size: 5 MB",
    multiUploadLimit: "From 2 to 5 CSV files, 5 MB each",
    run: "Generate similar CSV",
    runMulti: "Generate ZIP",
    running: "Generating...",
    download: "Download CSV",
    downloadZip: "Download ZIP",
    analyzing: "Analyzing...",
    rows: "rows",
    columns: "columns",
    tables: "tables",
    relationships: "relationships",
    result: "Result",
    totalRows: "Total rows",
    totalColumns: "Total columns",
    sourceTables: "Tables",
    detectedTypes: "Column types",
    primaryKey: "Primary key",
    noRelationships: "No relationships detected",
    targetRows: "Rows in result",
    scale: "Dataset size",
    scaleHint: "Allowed range: 0.1 to 5. 1 keeps the original size, 2 doubles it.",
    unique: "unique",
    analysisFailed: "Analysis failed.",
    synthesisFailed: "Synthesis failed.",
    multiFileCount: "Upload at least two and at most five CSV files.",
  },
} as const;

type SimilarMode = "single" | "multi";

const MIN_MULTI_SCALE = 0.1;
const MAX_MULTI_SCALE = 5;

function normalizeMultiScale(value: string) {
  const normalizedValue = value.trim().replace(",", ".");
  if (normalizedValue === "") {
    return 1;
  }

  const parsed = Number(normalizedValue);
  if (!Number.isFinite(parsed)) {
    return 1;
  }

  return Math.min(MAX_MULTI_SCALE, Math.max(MIN_MULTI_SCALE, parsed));
}

function formatMultiScale(value: number) {
  return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(2)));
}

function localizeSummaryItem(item: string, language: "ru" | "en") {
  if (language === "ru") {
    return item;
  }

  const detectedColumnsMatch = item.match(/^Найдено колонок:\s*(.+)$/);
  if (detectedColumnsMatch) {
    return `Detected columns: ${detectedColumnsMatch[1]}`;
  }

  const inputRowsMatch = item.match(/^Строк во входном CSV:\s*(.+)$/);
  if (inputRowsMatch) {
    return `Rows in input CSV: ${inputRowsMatch[1]}`;
  }

  const primaryKeyMatch = item.match(/^Первичный ключ SDV:\s*(.+)$/);
  if (primaryKeyMatch) {
    return `Primary key: ${primaryKeyMatch[1]}`;
  }

  return item;
}

function extractPrimaryKey(summary: string[], language: "ru" | "en") {
  const source = summary
    .map((item) => localizeSummaryItem(item, language))
    .find((item) => item.startsWith(language === "ru" ? "Первичный ключ SDV:" : "Primary key:"));
  return source?.split(":").slice(1).join(":").trim() ?? null;
}

function extractTypeSummaries(summary: string[], language: "ru" | "en") {
  return summary
    .map((item) => localizeSummaryItem(item, language))
    .filter((item) => {
      const lower = item.toLowerCase();
      return (
        item.includes(":") &&
        !lower.startsWith(language === "ru" ? "найдено колонок:" : "detected columns:") &&
        !lower.startsWith(language === "ru" ? "строк во входном csv:" : "rows in input csv:") &&
        !lower.startsWith(language === "ru" ? "первичный ключ sdv:" : "primary key:")
      );
    });
}

export function SimilarFlow() {
  const { language } = useLanguage();
  const t = copy[language];
  const [pendingMode, setPendingMode] = useState<SimilarMode>("single");
  const [selectedMode, setSelectedMode] = useState<SimilarMode | null>(null);
  const [analysis, setAnalysis] = useState<SimilarAnalyzeResponse | null>(null);
  const [result, setResult] = useState<SimilarRunResponse | null>(null);
  const [multiAnalysis, setMultiAnalysis] = useState<SimilarMultiAnalyzeResponse | null>(null);
  const [multiResult, setMultiResult] = useState<SimilarMultiRunResponse | null>(null);
  const [targetRows, setTargetRows] = useState(500);
  const [scaleInput, setScaleInput] = useState("1");
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [openTableName, setOpenTableName] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isMultiAnalyzing, setIsMultiAnalyzing] = useState(false);
  const [isMultiRunning, setIsMultiRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [multiError, setMultiError] = useState<string | null>(null);
  const loaderWord = isAnalyzing || isMultiAnalyzing ? "Analyzing" : isRunning || isMultiRunning ? "Generating" : null;

  const summaryItems = useMemo(() => {
    if (!analysis) {
      return [];
    }
    return extractTypeSummaries(analysis.summary, language);
  }, [analysis, language]);

  const primaryKey = useMemo(() => (analysis ? extractPrimaryKey(analysis.summary, language) : null), [analysis, language]);
  const multiTotalRows = useMemo(
    () => multiAnalysis?.tables.reduce((sum, table) => sum + table.row_count, 0) ?? 0,
    [multiAnalysis],
  );
  const multiTotalColumns = useMemo(
    () => multiAnalysis?.tables.reduce((sum, table) => sum + table.column_count, 0) ?? 0,
    [multiAnalysis],
  );

  const handleAnalyze = async (file: File | null) => {
    if (!file) {
      return;
    }

    setIsAnalyzing(true);
    setError(null);
    setResult(null);

    try {
      const response = await analyzeSimilarFile(file, { previewRowsLimit: 5 });
      setAnalysis(response);
      setIsPreviewOpen(true);
      setTargetRows(response.row_count);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t.analysisFailed);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const resetFlowState = () => {
    setError(null);
    setMultiError(null);
    setAnalysis(null);
    setResult(null);
    setMultiAnalysis(null);
    setMultiResult(null);
    setIsPreviewOpen(false);
    setOpenTableName(null);
  };

  const selectMode = () => {
    setSelectedMode(pendingMode);
    resetFlowState();
  };

  const goBackToModeSelection = () => {
    setSelectedMode(null);
    resetFlowState();
  };

  const handleMultiAnalyze = async (files: FileList | null) => {
    const selectedFiles = Array.from(files ?? []);
    if (selectedFiles.length < 2 || selectedFiles.length > 5) {
      setMultiError(t.multiFileCount);
      return;
    }

    setIsMultiAnalyzing(true);
    setMultiError(null);
    setMultiResult(null);

    try {
      const response = await analyzeMultiTableSimilarFiles(selectedFiles, { previewRowsLimit: 5 });
      setMultiAnalysis(response);
      setOpenTableName(response.tables[0]?.table_name ?? null);
      setScaleInput("1");
    } catch (caught) {
      setMultiError(caught instanceof ApiError ? caught.message : t.analysisFailed);
    } finally {
      setIsMultiAnalyzing(false);
    }
  };

  const handleRun = async () => {
    if (!analysis) {
      return;
    }

    setIsRunning(true);
    setError(null);

    try {
      const response = await runSimilar({
        analysis_id: analysis.analysis_id,
        target_rows: targetRows,
      });
      setResult(response);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : t.synthesisFailed);
    } finally {
      setIsRunning(false);
    }
  };

  const handleMultiRun = async () => {
    if (!multiAnalysis) {
      return;
    }

    const normalizedScale = normalizeMultiScale(scaleInput);
    setScaleInput(formatMultiScale(normalizedScale));
    setIsMultiRunning(true);
    setMultiError(null);

    try {
      const response = await runMultiTableSimilar({
        analysis_id: multiAnalysis.analysis_id,
        scale: normalizedScale,
      });
      setMultiResult(response);
    } catch (caught) {
      setMultiError(caught instanceof ApiError ? caught.message : t.synthesisFailed);
    } finally {
      setIsMultiRunning(false);
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
        {t.description ? <p>{t.description}</p> : null}
      </section>

      {!selectedMode ? (
        <section className="page-container similar-mode-grid">
          <button
            type="button"
            className={`tool-surface similar-mode-card similar-choice-card${pendingMode === "single" ? " is-active" : ""}`}
            onClick={() => setPendingMode("single")}
          >
            <span className="field-label">{t.singleModeTitle}</span>
            <span className="csv-file-visual csv-file-visual--single" aria-hidden="true">
              <span className="csv-file csv-file--blue">
                <span />
                <span />
                <span />
                <strong>CSV</strong>
              </span>
            </span>
            <p>{t.singleModeDescription}</p>
          </button>
          <button
            type="button"
            className={`tool-surface similar-mode-card similar-choice-card${pendingMode === "multi" ? " is-active" : ""}`}
            onClick={() => setPendingMode("multi")}
          >
            <span className="field-label">{t.multiModeTitle}</span>
            <span className="csv-file-visual csv-file-visual--multi" aria-hidden="true">
              <span className="csv-file csv-file--blue">
                <span />
                <span />
                <span />
                <strong>CSV</strong>
              </span>
              <span className="csv-file csv-file--green">
                <span />
                <span />
                <span />
                <strong>CSV</strong>
              </span>
              <span className="csv-file csv-file--pink">
                <span />
                <span />
                <span />
                <strong>CSV</strong>
              </span>
            </span>
            <p>{t.multiModeDescription}</p>
          </button>
          <div className="similar-mode-actions">
            <button type="button" className="button button--primary" onClick={selectMode}>
              {t.choose}
            </button>
          </div>
        </section>
      ) : null}

      {selectedMode === "single" ? (
        <section className="page-container tool-layout">
          <div className="tool-surface">
            {!analysis ? (
              <>
                <div className="surface-topbar">
                  <button type="button" className="surface-topbar__action surface-topbar__button" onClick={goBackToModeSelection}>
                    {t.back}
                  </button>
                </div>
                <label className="upload-dropzone">
                  <input type="file" accept=".csv,text/csv" onChange={(event) => void handleAnalyze(event.target.files?.[0] ?? null)} />
                  <span>{t.analyze}</span>
                  <small className="upload-dropzone__hint">{t.uploadLimit}</small>
                </label>
              </>
            ) : (
              <div className="surface-topbar">
                <div className="surface-meta surface-meta--compact">
                  <span>{analysis.file_name}</span>
                </div>
                <label className="surface-topbar__action">
                  <input type="file" accept=".csv,text/csv" onChange={(event) => void handleAnalyze(event.target.files?.[0] ?? null)} />
                  <span>{language === "ru" ? "Загрузить другой файл" : "Upload another file"}</span>
                </label>
                <button type="button" className="surface-topbar__action surface-topbar__button" onClick={goBackToModeSelection}>
                  {t.back}
                </button>
              </div>
            )}

          {error ? <p className="surface-error">{error}</p> : null}

          {analysis ? (
            <>
              <div className="dataset-overview">
                <div className="dataset-stats-grid">
                  <div className="dataset-stat">
                    <span>{t.totalRows}</span>
                    <strong>{analysis.row_count}</strong>
                  </div>
                  <div className="dataset-stat">
                    <span>{t.totalColumns}</span>
                    <strong>{analysis.column_count}</strong>
                  </div>
                  <div className="dataset-stat">
                    <span>{t.relationships}</span>
                    <strong>0</strong>
                  </div>
                </div>

                {primaryKey || summaryItems.length > 0 ? (
                  <div className="dataset-detail-grid">
                    {primaryKey ? (
                      <div className="dataset-detail">
                        <span>{t.primaryKey}</span>
                        <strong>{primaryKey}</strong>
                      </div>
                    ) : null}
                    {summaryItems.length > 0 ? (
                      <div className="dataset-detail">
                        <span>{t.detectedTypes}</span>
                        <div className="dataset-chip-row">
                          {summaryItems.map((item) => (
                            <em key={item}>{item}</em>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </div>

              <div className={`preview-panel preview-panel--clean${isPreviewOpen ? " is-open" : ""}`}>
                <button
                  type="button"
                  className="preview-panel__toggle"
                  onClick={() => setIsPreviewOpen((current) => !current)}
                >
                  <span>{language === "ru" ? "Превью первых строк" : "Preview first rows"}</span>
                  <span className="preview-panel__icon" aria-hidden="true">{isPreviewOpen ? "−" : "+"}</span>
                </button>
                <div className="preview-panel__body">
                  <div className="preview-table">
                    <table>
                      <thead>
                        <tr>
                          {analysis.columns.map((column) => (
                            <th key={column.name}>{column.name}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {analysis.preview_rows.map((row, index) => (
                          <tr key={index}>
                            {analysis.columns.map((column) => (
                              <td key={column.name}>{row[column.name] ?? ""}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <label className="input-block input-block--inline input-block--wide">
                <span className="field-label">{t.targetRows}</span>
                <input
                  type="number"
                  min={1}
                  max={10000}
                  value={targetRows}
                  onChange={(event) => {
                    setResult(null);
                    setTargetRows(Math.min(10000, Math.max(1, Number(event.target.value) || 1)));
                  }}
                />
              </label>

              <button type="button" className="button button--primary tool-submit" onClick={handleRun} disabled={isRunning}>
                {t.run}
              </button>
            </>
          ) : null}
          {result ? (
            <article className="sidebar-card sidebar-card--result similar-result-card">
              <span className="field-label">{t.result}</span>
              <strong className="sidebar-card__big">{result.file_name}</strong>
              <div className="sidebar-list">
                <div className="sidebar-list__row">
                  <span>{t.rows}</span>
                  <strong>{result.row_count}</strong>
                </div>
                <div className="sidebar-list__row">
                  <span>{t.columns}</span>
                  <strong>{result.column_count}</strong>
                </div>
              </div>
              <button
                type="button"
                className="button button--primary button--wide sidebar-card__download"
                onClick={() => downloadBase64File(result.content_base64, result.file_name, "text/csv;charset=utf-8")}
              >
                {t.download}
              </button>
            </article>
          ) : null}
          </div>
        </section>
      ) : null}

      {selectedMode === "multi" ? (
        <section className="page-container tool-layout">
          <div className="tool-surface">
            {!multiAnalysis ? (
              <>
                <div className="surface-topbar">
                  <button type="button" className="surface-topbar__action surface-topbar__button" onClick={goBackToModeSelection}>
                    {t.back}
                  </button>
                </div>
                <label className="upload-dropzone">
                  <input
                    type="file"
                    accept=".csv,text/csv"
                    multiple
                    onChange={(event) => void handleMultiAnalyze(event.target.files)}
                  />
                  <span>{t.analyzeMulti}</span>
                  <small className="upload-dropzone__hint">{t.multiUploadLimit}</small>
                </label>
              </>
            ) : (
              <div className="surface-topbar">
                <div className="surface-meta surface-meta--compact">
                  <span>{multiAnalysis.table_count} {t.tables}</span>
                  <span>{multiAnalysis.relationships.length} {t.relationships}</span>
                </div>
                <label className="surface-topbar__action">
                  <input
                    type="file"
                    accept=".csv,text/csv"
                    multiple
                    onChange={(event) => void handleMultiAnalyze(event.target.files)}
                  />
                  <span>{language === "ru" ? "Загрузить другой датасет" : "Upload another dataset"}</span>
                </label>
                <button type="button" className="surface-topbar__action surface-topbar__button" onClick={goBackToModeSelection}>
                  {t.back}
                </button>
              </div>
            )}

          {multiError ? <p className="surface-error">{multiError}</p> : null}

          {multiAnalysis ? (
            <>
              <div className="dataset-overview">
                <div className="dataset-stats-grid">
                  <div className="dataset-stat">
                    <span>{t.totalRows}</span>
                    <strong>{multiTotalRows}</strong>
                  </div>
                  <div className="dataset-stat">
                    <span>{t.totalColumns}</span>
                    <strong>{multiTotalColumns}</strong>
                  </div>
                  <div className="dataset-stat">
                    <span>{t.relationships}</span>
                    <strong>{multiAnalysis.relationships.length}</strong>
                  </div>
                </div>

                <div className="dataset-detail-grid">
                  <div className="dataset-detail">
                    <span>{t.sourceTables}</span>
                    <div className="dataset-table-list">
                      {multiAnalysis.tables.map((table) => (
                        <em key={table.table_name}>
                          {table.table_name}: {table.row_count} {t.rows}, {table.column_count} {t.columns}
                        </em>
                      ))}
                    </div>
                  </div>
                  <div className="dataset-detail">
                    <span>{t.relationships}</span>
                    {multiAnalysis.relationships.length > 0 ? (
                      <div className="dataset-table-list">
                        {multiAnalysis.relationships.map((relationship) => (
                          <em key={`${relationship.parent_table_name}-${relationship.child_table_name}-${relationship.child_foreign_key}`}>
                            {relationship.parent_table_name}.{relationship.parent_primary_key} → {relationship.child_table_name}.{relationship.child_foreign_key}
                          </em>
                        ))}
                      </div>
                    ) : (
                      <strong>{t.noRelationships}</strong>
                    )}
                  </div>
                </div>
              </div>

              <div className="multi-table-list">
                {multiAnalysis.tables.map((table) => {
                  const isOpen = openTableName === table.table_name;
                  return (
                    <div key={table.table_name} className={`preview-panel preview-panel--clean${isOpen ? " is-open" : ""}`}>
                      <button
                        type="button"
                        className="preview-panel__toggle"
                        onClick={() => setOpenTableName(isOpen ? null : table.table_name)}
                      >
                        <span>{table.file_name} · {table.row_count} {t.rows}</span>
                        <span className="preview-panel__icon" aria-hidden="true">{isOpen ? "−" : "+"}</span>
                      </button>
                      <div className="preview-panel__body">
                        <div className="preview-table">
                          <table>
                            <thead>
                              <tr>
                                {table.columns.map((column) => (
                                  <th key={column.name}>{column.name}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {table.preview_rows.map((row, index) => (
                                <tr key={index}>
                                  {table.columns.map((column) => (
                                    <td key={column.name}>{row[column.name] ?? ""}</td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              <label className="input-block input-block--inline input-block--wide">
                <span className="field-label">{t.scale}</span>
                <input
                  type="number"
                  min={MIN_MULTI_SCALE}
                  max={MAX_MULTI_SCALE}
                  step="0.1"
                  value={scaleInput}
                  onChange={(event) => {
                    setMultiResult(null);
                    const nextValue = event.target.value;
                    setScaleInput(nextValue);
                  }}
                  onBlur={() => {
                    const normalizedScale = normalizeMultiScale(scaleInput);
                    setScaleInput(formatMultiScale(normalizedScale));
                  }}
                />
                <small className="input-block__hint">{t.scaleHint}</small>
              </label>

              <button type="button" className="button button--primary tool-submit" onClick={handleMultiRun} disabled={isMultiRunning}>
                {t.runMulti}
              </button>
            </>
          ) : null}

          {multiResult ? (
            <article className="sidebar-card sidebar-card--result similar-result-card">
              <span className="field-label">{t.result}</span>
              <strong className="sidebar-card__big">{multiResult.file_name}</strong>
              <div className="sidebar-list">
                <div className="sidebar-list__row">
                  <span>{t.tables}</span>
                  <strong>{multiResult.table_count}</strong>
                </div>
                {multiResult.tables.map((table) => (
                  <div key={table.table_name} className="sidebar-list__row">
                    <span>{table.file_name}</span>
                    <strong>{table.row_count}</strong>
                  </div>
                ))}
              </div>
              <button
                type="button"
                className="button button--primary button--wide sidebar-card__download"
                onClick={() => downloadBase64File(multiResult.archive_base64, multiResult.file_name, "application/zip")}
              >
                {t.downloadZip}
              </button>
            </article>
          ) : null}
          </div>
        </section>
      ) : null}
    </main>
  );
}
