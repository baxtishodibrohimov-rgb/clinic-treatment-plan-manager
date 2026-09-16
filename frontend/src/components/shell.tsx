"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { getScopeClinicId, setScopeClinicId } from "@/lib/clinic-scope";
import type { ClinicOut } from "@/lib/types";

// Full-bleed screens (patient detail, wizard, presentation) draw their own
// compact header and hide the top nav — see the design handoff.
const HIDE_NAV_PATTERN = /^\/cases\/[^/]+/;

function ClinicSwitcher() {
  const [clinics, setClinics] = useState<ClinicOut[]>([]);
  const [value, setValue] = useState("");

  useEffect(() => {
    setValue(getScopeClinicId() ?? "");
    api
      .get<ClinicOut[]>("/api/clinics")
      .then(setClinics)
      .catch(() => {});
  }, []);

  return (
    <select
      value={value}
      onChange={(e) => {
        setValue(e.target.value);
        setScopeClinicId(e.target.value || null);
        window.location.reload();
      }}
      className="w-[200px] shrink-0 rounded-md border border-divider bg-surface px-2 py-1.5 text-xs text-body"
    >
      <option value="">Barcha filiallar</option>
      {clinics.map((c) => (
        <option key={c.id} value={c.id}>
          {c.name}
        </option>
      ))}
    </select>
  );
}

function GearIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 256 256" fill="currentColor">
      <path d="M128,80a48,48,0,1,0,48,48A48.05,48.05,0,0,0,128,80Zm0,80a32,32,0,1,1,32-32A32,32,0,0,1,128,160Zm88-29.84q.06-2.16,0-4.32l14.92-18.64a8,8,0,0,0,1.48-7.06,107.21,107.21,0,0,0-10.88-26.25,8,8,0,0,0-6-3.93l-23.72-2.64q-1.48-1.56-3-3L186,40.54a8,8,0,0,0-3.94-6,107.71,107.71,0,0,0-26.25-10.87,8,8,0,0,0-7.06,1.48L130.16,40q-2.16-.06-4.32,0L107.2,25.11a8,8,0,0,0-7.06-1.48A107.6,107.6,0,0,0,73.89,34.51a8,8,0,0,0-3.93,6L67.32,64.2q-1.56,1.49-3,3L40.54,70a8,8,0,0,0-6,3.94,107.71,107.71,0,0,0-10.87,26.25,8,8,0,0,0,1.48,7.06L40,125.84q-.06,2.16,0,4.32L25.11,148.8a8,8,0,0,0-1.48,7.06,107.21,107.21,0,0,0,10.88,26.25,8,8,0,0,0,6,3.93l23.72,2.64q1.49,1.56,3,3L70,215.46a8,8,0,0,0,3.94,6,107.71,107.71,0,0,0,26.25,10.87,8,8,0,0,0,7.06-1.48L125.84,216q2.16.06,4.32,0l18.64,14.92a8,8,0,0,0,7.06,1.48,107.21,107.21,0,0,0,26.25-10.88,8,8,0,0,0,3.93-6l2.64-23.72q1.56-1.48,3-3L215.46,186a8,8,0,0,0,6-3.94,107.71,107.71,0,0,0,10.87-26.25,8,8,0,0,0-1.48-7.06Z" />
    </svg>
  );
}

function TopNav() {
  const { user, isSuperAdmin, logout } = useAuth();
  const pathname = usePathname();
  const isDashboard = pathname === "/dashboard";
  const isSettings = pathname?.startsWith("/admin") ?? false;

  return (
    <header className="flex items-center gap-6 border-b border-divider bg-surface px-6 py-3">
      <div className="whitespace-nowrap font-heading text-base font-medium text-accent">Treatment Plan Manager</div>

      {isSuperAdmin && <ClinicSwitcher />}

      <nav className="flex items-center gap-1">
        <Link
          href="/dashboard"
          className={`whitespace-nowrap rounded-md px-3.5 py-2 text-sm ${
            isDashboard ? "bg-tag-accent-bg font-medium text-tag-accent-text" : "text-body hover:bg-tag-neutral-bg"
          }`}
        >
          Dashboard
        </Link>
        <Link
          href="/admin/settings-hub"
          className={`flex items-center gap-1.5 whitespace-nowrap rounded-md px-3.5 py-2 text-sm ${
            isSettings ? "bg-tag-accent-bg font-medium text-tag-accent-text" : "text-body hover:bg-tag-neutral-bg"
          }`}
        >
          <GearIcon />
          Sozlamalar
        </Link>
      </nav>

      <div className="flex-1" />

      <div className="flex shrink-0 items-center gap-3 text-xs text-muted">
        <span className="max-w-[160px] truncate">{user?.email}</span>
        <button onClick={logout} className="whitespace-nowrap text-accent hover:underline">
          Chiqish
        </button>
      </div>
    </header>
  );
}

export function Shell({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const hideNav = HIDE_NAV_PATTERN.test(pathname ?? "");

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return <div className="flex min-h-screen items-center justify-center text-muted">Yuklanmoqda...</div>;
  }

  return (
    <div className="min-h-screen bg-surface">
      {!hideNav && <TopNav />}
      <main className="min-w-0 overflow-x-hidden p-6">{children}</main>
    </div>
  );
}
