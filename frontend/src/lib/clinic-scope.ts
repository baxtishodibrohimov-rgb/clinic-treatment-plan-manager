// Which single clinic a SUPER_ADMIN is currently viewing (null = every
// clinic). Non-super-admins never touch this — the backend already locks
// them to their own clinic regardless of this value.
const KEY = "tp_clinic_scope";
const EVENT = "tp-clinic-scope-changed";

export function getScopeClinicId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(KEY);
}

export function setScopeClinicId(id: string | null) {
  if (typeof window === "undefined") return;
  if (id) window.localStorage.setItem(KEY, id);
  else window.localStorage.removeItem(KEY);
  window.dispatchEvent(new Event(EVENT));
}

export function onScopeClinicChange(handler: () => void): () => void {
  window.addEventListener(EVENT, handler);
  return () => window.removeEventListener(EVENT, handler);
}

export function withClinicScope(path: string): string {
  const clinicId = getScopeClinicId();
  if (!clinicId) return path;
  return path + (path.includes("?") ? "&" : "?") + `clinic_id=${clinicId}`;
}
