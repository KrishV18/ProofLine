import type { Finding } from "@/types/finding";
import { mockFindings } from "@/lib/mock/findings";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK !== "false";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export async function getFindings(
  draftId: string,
  version: number
): Promise<Finding[]> {
  if (USE_MOCK) {
    return mockFindings;
  }
  return apiFetch<Finding[]>(
    `/drafts/${draftId}/versions/${version}/findings`
  );
}

export async function healthCheck(): Promise<{
  status: string;
  service: string;
}> {
  if (USE_MOCK) {
    return { status: "ok", service: "proofline-api (mock)" };
  }
  return apiFetch("/health");
}

