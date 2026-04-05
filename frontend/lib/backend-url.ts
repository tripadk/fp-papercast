const API_PREFIX = "/api";

function normalizePath(path: string): string {
  if (!path.startsWith("/")) {
    return `/${path}`;
  }
  return path;
}

export function backendApiUrl(path: string): string {
  return normalizePath(path);
}

export function backendAssetUrl(path: string): string {
  const normalizedPath = normalizePath(path);
  return normalizedPath.startsWith(API_PREFIX) ? normalizedPath : `${API_PREFIX}${normalizedPath}`;
}
