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
  sources: Source[];
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
  const response = await fetch(
    `${import.meta.env.VITE_API_URL || "http://localhost:8000"}${path}`,
    { ...options, headers },
  );
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
