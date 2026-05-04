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
    title: "Загружайте произвольный CSV и получайте похожий синтетический датасет.",
    description: "",
    analyze: "Загрузить и проанализировать CSV",
    analyzeMulti: "Загрузить связный датасет",
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
    relationships: "связей",
    result: "Результат",
    targetRows: "Размер результата",
    scale: "Масштаб результата",
    unique: "уникальных",
    analysisFailed: "Не удалось выполнить анализ.",
    synthesisFailed: "Не удалось сгенерировать результат.",
    multiFileCount: "Загрузите минимум два и максимум пять CSV файлов.",
  },
  en: {
    eyebrow: "Similar",
    title: "Upload any CSV and produce a similar synthetic dataset.",
    description: "",
    analyze: "Upload and analyze CSV",
    analyzeMulti: "Upload related dataset",
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
    targetRows: "Result size",
    scale: "Result scale",
    unique: "unique",
    analysisFailed: "Analysis failed.",
    synthesisFailed: "Synthesis failed.",
    multiFileCount: "Upload at least two and at most five CSV files.",
  },
} as const;

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

export function SimilarFlow() {
  const { language } = useLanguage();
  const t = copy[language];
  const [analysis, setAnalysis] = useState<SimilarAnalyzeResponse | null>(null);
  const [result, setResult] = useState<SimilarRunResponse | null>(null);
  const [multiAnalysis, setMultiAnalysis] = useState<SimilarMultiAnalyzeResponse | null>(null);
  const [multiResult, setMultiResult] = useState<SimilarMultiRunResponse | null>(null);
  const [targetRows, setTargetRows] = useState(500);
  const [scale, setScale] = useState(1);
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
    return analysis.summary.map((item) => localizeSummaryItem(item, language));
  }, [analysis, language]);

  const multiSummaryItems = useMemo(() => {
    if (!multiAnalysis) {
      return [];
    }
    return multiAnalysis.summary.map((item) => localizeSummaryItem(item, language));
  }, [multiAnalysis, language]);

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
      setScale(1);
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

    setIsMultiRunning(true);
    setMultiError(null);

    try {
      const response = await runMultiTableSimilar({
        analysis_id: multiAnalysis.analysis_id,
        scale,
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

      <section className="page-container similar-mode-grid">
        <div className="tool-surface similar-mode-card">
          {!analysis ? (
            <label className="upload-dropzone">
              <input type="file" accept=".csv,text/csv" onChange={(event) => void handleAnalyze(event.target.files?.[0] ?? null)} />
              <span>{t.analyze}</span>
              <small className="upload-dropzone__hint">{t.uploadLimit}</small>
            </label>
          ) : (
            <div className="surface-topbar">
              <div className="surface-meta surface-meta--compact">
                <span>{analysis.file_name}</span>
              </div>
              <label className="surface-topbar__action">
                <input type="file" accept=".csv,text/csv" onChange={(event) => void handleAnalyze(event.target.files?.[0] ?? null)} />
                <span>{language === "ru" ? "Загрузить другой файл" : "Upload another file"}</span>
              </label>
            </div>
          )}

          {error ? <p className="surface-error">{error}</p> : null}

          {analysis ? (
            <>
              <div className={`preview-panel${isPreviewOpen ? " is-open" : ""}`}>
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

              <div className="summary-list summary-list--stack">
                {summaryItems.map((item) => (
                  <div key={item} className="summary-list__item">
                    {item}
                  </div>
                ))}
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
            <article className="sidebar-card sidebar-card--result">
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

        <div className="tool-surface similar-mode-card">
          {!multiAnalysis ? (
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
            </div>
          )}

          {multiError ? <p className="surface-error">{multiError}</p> : null}

          {multiAnalysis ? (
            <>
              <div className="summary-list summary-list--stack">
                {multiSummaryItems.map((item) => (
                  <div key={item} className="summary-list__item">
                    {item}
                  </div>
                ))}
              </div>

              <div className="multi-table-list">
                {multiAnalysis.tables.map((table) => {
                  const isOpen = openTableName === table.table_name;
                  return (
                    <div key={table.table_name} className={`preview-panel${isOpen ? " is-open" : ""}`}>
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

              {multiAnalysis.relationships.length > 0 ? (
                <div className="relationship-list">
                  {multiAnalysis.relationships.map((relationship) => (
                    <div
                      key={`${relationship.parent_table_name}-${relationship.child_table_name}-${relationship.child_foreign_key}`}
                      className="summary-list__item"
                    >
                      {relationship.parent_table_name}.{relationship.parent_primary_key} → {relationship.child_table_name}.{relationship.child_foreign_key}
                    </div>
                  ))}
                </div>
              ) : null}

              <label className="input-block input-block--inline input-block--wide">
                <span className="field-label">{t.scale}</span>
                <input
                  type="number"
                  min={0.1}
                  max={5}
                  step={0.1}
                  value={scale}
                  onChange={(event) => {
                    setMultiResult(null);
                    setScale(Math.min(5, Math.max(0.1, Number(event.target.value) || 1)));
                  }}
                />
              </label>

              <button type="button" className="button button--primary tool-submit" onClick={handleMultiRun} disabled={isMultiRunning}>
                {t.runMulti}
              </button>
            </>
          ) : null}

          {multiResult ? (
            <article className="sidebar-card sidebar-card--result">
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
    </main>
  );
}
