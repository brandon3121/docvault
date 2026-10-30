export interface User {
  id: number;
  username: string;
  full_name: string;
  role: "admin" | "user";
}

export interface Destination {
  id: number;
  name: string;
  parent_id: number | null;
  depth: number;
  path: string;
}

export interface DocumentType {
  id: number;
  name: string;
}

export interface Owner {
  id: number;
  full_name: string;
  department: string | null;
}

export interface DocumentRecord {
  id: number;
  title: string;
  document_type_id: number;
  document_type_name: string;
  destination_id: number;
  destination_path: string;
  owner_id: number | null;
  owner_name: string | null;
  owner_name_extracted: string | null;
  owner_name_edited: boolean;
  document_date: string | null;
  document_date_extracted: string | null;
  document_date_edited: boolean;
  original_filename: string;
  sha256: string;
  uploaded_by: number;
  uploaded_by_name: string;
  uploaded_at: string;
}

export interface DocumentPage {
  items: DocumentRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface DocumentFilters {
  q?: string;
  owner?: string;
  destination_id?: string;
  document_type_id?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export interface DocumentUpdate {
  title?: string;
  destination_id?: number;
  document_type_id?: number;
  owner_id?: number | null;
  owner_name?: string | null;
  document_date?: string | null;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown = null,
  ) {
    super(`Request failed with status ${status}`);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (typeof init.body === "string") {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...init, credentials: "include", headers });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body?.detail ?? null);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

function json(method: string, body: unknown): RequestInit {
  return { method, body: JSON.stringify(body) };
}

export function login(username: string, password: string): Promise<User> {
  return request<User>("/api/auth/login", json("POST", { username, password }));
}

export function logout(): Promise<void> {
  return request<void>("/api/auth/logout", { method: "POST" });
}

export function getMe(): Promise<User> {
  return request<User>("/api/auth/me");
}

export function listDestinations(): Promise<Destination[]> {
  return request<Destination[]>("/api/destinations");
}

export function createDestination(name: string, parentId: number | null): Promise<Destination> {
  return request<Destination>("/api/destinations", json("POST", { name, parent_id: parentId }));
}

export function updateDestination(id: number, name: string, parentId: number | null): Promise<Destination> {
  return request<Destination>(`/api/destinations/${id}`, json("PUT", { name, parent_id: parentId }));
}

export function deleteDestination(id: number): Promise<void> {
  return request<void>(`/api/destinations/${id}`, { method: "DELETE" });
}

export function listDocumentTypes(): Promise<DocumentType[]> {
  return request<DocumentType[]>("/api/document-types");
}

export function createDocumentType(name: string): Promise<DocumentType> {
  return request<DocumentType>("/api/document-types", json("POST", { name }));
}

export function updateDocumentType(id: number, name: string): Promise<DocumentType> {
  return request<DocumentType>(`/api/document-types/${id}`, json("PUT", { name }));
}

export function deleteDocumentType(id: number): Promise<void> {
  return request<void>(`/api/document-types/${id}`, { method: "DELETE" });
}

export function searchOwners(query: string, signal?: AbortSignal): Promise<Owner[]> {
  const params = new URLSearchParams();
  if (query.trim()) {
    params.set("q", query.trim());
  }
  return request<Owner[]>(`/api/owners?${params}`, { signal });
}

export function createOwner(fullName: string, department: string | null): Promise<Owner> {
  return request<Owner>("/api/owners", json("POST", { full_name: fullName, department }));
}

export function updateOwner(id: number, fullName: string, department: string | null): Promise<Owner> {
  return request<Owner>(`/api/owners/${id}`, json("PUT", { full_name: fullName, department }));
}

export function deleteOwner(id: number): Promise<void> {
  return request<void>(`/api/owners/${id}`, { method: "DELETE" });
}

export function listDocuments(filters: DocumentFilters): Promise<DocumentPage> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") {
      params.set(key, String(value));
    }
  }
  return request<DocumentPage>(`/api/documents?${params}`);
}

export function getDocument(id: number): Promise<DocumentRecord> {
  return request<DocumentRecord>(`/api/documents/${id}`);
}

export function uploadDocument(form: FormData): Promise<DocumentRecord> {
  return request<DocumentRecord>("/api/documents", { method: "POST", body: form });
}

export function updateDocument(id: number, changes: DocumentUpdate): Promise<DocumentRecord> {
  return request<DocumentRecord>(`/api/documents/${id}`, json("PATCH", changes));
}

export function documentFileUrl(id: number): string {
  return `/api/documents/${id}/file`;
}

export function duplicateDocumentId(error: unknown): number | null {
  if (error instanceof ApiError && error.status === 409) {
    const detail = error.detail as { document_id?: unknown } | null;
    if (detail && typeof detail.document_id === "number") {
      return detail.document_id;
    }
  }
  return null;
}
