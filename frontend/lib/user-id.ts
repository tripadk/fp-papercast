export function toUserId(input: string): string {
  const normalized = input.trim().toLowerCase();
  if (!normalized) {
    return "anonymous";
  }

  const localPart = normalized.includes("@") ? normalized.split("@")[0] : normalized;
  const safeUserId = localPart.replace(/[^a-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "");
  return safeUserId || "anonymous";
}
