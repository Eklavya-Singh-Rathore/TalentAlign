import { AnalysisPayload } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  embedding_backend: string;
  llm_backend: string;
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/health`, {
    method: "GET",
    headers: {
      "Accept": "application/json",
    },
  });

  if (!res.ok) {
    throw new Error(`Health check failed with status: ${res.status}`);
  }

  return res.json();
}

export async function analyzeResumeJD(
  resumeFile: File,
  jdText: string,
  includeDebug: boolean = false
): Promise<AnalysisPayload> {
  const formData = new FormData();
  formData.append("resume", resumeFile);
  formData.append("jd_text", jdText);
  formData.append("include_debug", includeDebug ? "true" : "false");

  const res = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    headers: {
      "Accept": "application/json",
    },
    body: formData,
  });

  if (!res.ok) {
    let errorMessage = "Analysis request failed.";
    try {
      const errDetail = await res.json();
      if (errDetail && errDetail.detail) {
        errorMessage = errDetail.detail;
      }
    } catch {
      // ignore
    }
    throw new Error(errorMessage);
  }

  return res.json();
}
