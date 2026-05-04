import type {
  AnonymizeRunResponse,
  AnonymizeUploadResponse,
  GenerateDomainSummary,
  GenerateRunRequest,
  GenerateRunResponse,
  GenerateTemplateDetail,
  GenerateTemplateId,
  GenerateTemplateSummary,
  SimilarAnalyzeResponse,
  SimilarMultiAnalyzeResponse,
  SimilarMultiRunResponse,
  SimilarRunResponse,
} from "@/lib/api-types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

type ApiErrorPayload = {
  message?: string;
  error_code?: string;
};

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function parseJsonResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const errorPayload = payload as ApiErrorPayload | null;
    throw new ApiError(
      errorPayload?.message ?? "Request failed.",
      response.status,
      errorPayload?.error_code,
    );
  }

  return payload as T;
}

async function postJson<TResponse>(path: string, body: unknown): Promise<TResponse> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  return parseJsonResponse<TResponse>(response);
}

function buildCsvFormData(file: File, options?: { previewRowsLimit?: number }) {
  const formData = new FormData();
  formData.append("file", file);

  if (options?.previewRowsLimit) {
    formData.append("preview_rows_limit", String(options.previewRowsLimit));
  }

  return formData;
}

function buildMultiCsvFormData(files: File[], options?: { previewRowsLimit?: number }) {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });

  if (options?.previewRowsLimit) {
    formData.append("preview_rows_limit", String(options.previewRowsLimit));
  }
  formData.append("has_header", "true");

  return formData;
}

export async function fetchGenerateDomains(): Promise<{ items: GenerateDomainSummary[] }> {
  const response = await fetch(`${API_BASE_URL}/generate/domains`);
  return parseJsonResponse(response);
}

export async function fetchGenerateTemplates(): Promise<{ items: GenerateTemplateSummary[] }> {
  const response = await fetch(`${API_BASE_URL}/generate/templates`);
  return parseJsonResponse(response);
}

export async function fetchGenerateTemplateDetail(templateId: GenerateTemplateId): Promise<GenerateTemplateDetail> {
  const response = await fetch(`${API_BASE_URL}/generate/templates/${templateId}`);
  return parseJsonResponse(response);
}

export async function runGenerate(request: GenerateRunRequest): Promise<GenerateRunResponse> {
  return postJson("/generate/run", request);
}

export async function uploadAnonymizeFile(file: File): Promise<AnonymizeUploadResponse> {
  const response = await fetch(`${API_BASE_URL}/anonymize/upload`, {
    method: "POST",
    body: buildCsvFormData(file),
  });

  return parseJsonResponse(response);
}

export async function runAnonymize(request: { upload_id: string; rules: unknown[] }): Promise<AnonymizeRunResponse> {
  return postJson("/anonymize/run", request);
}

export async function analyzeSimilarFile(
  file: File,
  options?: { previewRowsLimit?: number },
): Promise<SimilarAnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}/similar/analyze`, {
    method: "POST",
    body: buildCsvFormData(file, options),
  });

  return parseJsonResponse(response);
}

export async function runSimilar(request: { analysis_id: string; target_rows: number }): Promise<SimilarRunResponse> {
  return postJson("/similar/run", request);
}

export async function analyzeMultiTableSimilarFiles(
  files: File[],
  options?: { previewRowsLimit?: number },
): Promise<SimilarMultiAnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}/similar/multi/analyze`, {
    method: "POST",
    body: buildMultiCsvFormData(files, options),
  });

  return parseJsonResponse(response);
}

export async function runMultiTableSimilar(request: {
  analysis_id: string;
  scale: number;
}): Promise<SimilarMultiRunResponse> {
  return postJson("/similar/multi/run", request);
}
