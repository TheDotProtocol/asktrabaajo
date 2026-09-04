/**
 * Organization selection storage.
 *
 * The selected org id is a UX default passed as a path/query parameter.
 * The backend still checks membership on every org-scoped request.
 */
export const ORG_STORAGE_KEY = "asktrabaajo_org_id";

export function getStoredOrganizationId(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(ORG_STORAGE_KEY) ?? "";
}

export function setStoredOrganizationId(organizationId: string): void {
  if (typeof window === "undefined") return;
  if (organizationId) {
    window.localStorage.setItem(ORG_STORAGE_KEY, organizationId);
  } else {
    window.localStorage.removeItem(ORG_STORAGE_KEY);
  }
}
