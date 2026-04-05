const BACKEND_BASE_URL = (process.env.NEXT_PUBLIC_BACKEND_URL ?? "").replace(/\/+$/, "");

function normalizePath(path: string): string {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  if (!path.startsWith("/")) {
    return `/${path}`;
  }
  return path;
}

export function backendApiUrl(path: string): string {
  const normalizedPath = normalizePath(path);
  return normalizedPath.startsWith("http") ? normalizedPath : `${BACKEND_BASE_URL}${normalizedPath}`;
}

export function backendAssetUrl(path: string): string {
  return backendApiUrl(path);
}
