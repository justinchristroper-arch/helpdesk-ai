export type Source = {
  id: string;
  document_id: string;
  title: string;
  section: string | null;
  page_number: number | null;
  excerpt: string;
  relevance_score: number;
  citation_number: number;
};
export type Message = {
  id: string;
  role: string;
  content: string;
  outcome?: string;
  synthesis_status?: "used" | "limited" | "disabled" | "unavailable" | null;
  sources: Source[];
  intent_id?: string;
  feedback_rating?: -1 | 1 | null;
  clarification?: { intent_id: string; topic: string; question: string }[];
};
export type Conversation = { id: string; title: string };
export type Document = {
  id: string;
  title: string;
  filename: string;
  created_at: string;
  status: string;
};
export type Session = { token: string; role: string; email: string };
export async function api<T>(
  path: string,
  token?: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(
      `${import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "http://localhost:8000" : "/api")}${path}`,
      { ...options, headers, signal: options.signal ?? AbortSignal.timeout(120_000) },
    );
  } catch {
    throw new Error("The demo server is waking up or unavailable. Please wait a moment and try again. Your question has not been retried automatically.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : `Request failed (${response.status}). Please try again.`,
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
