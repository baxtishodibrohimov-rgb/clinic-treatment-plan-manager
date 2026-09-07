"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { getScopeClinicId, setScopeClinicId } from "@/lib/clinic-scope";
import type { ClinicOut } from "@/lib/types";

const ADMIN_NAV = [
  { href: "/admin/staff", label: "Planner/Doctor rollari" },
  { href: "/admin/image-types", label: "Rasm turlari" },
  { href: "/admin/reminders", label: "Eslatmalar" },
  { href: "/admin/settings", label: "Sozlamalar" },
];

const SUPER_ADMIN_NAV = [{ href: "/admin/clinics", label: "Filiallar" }];

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
      className="w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-xs"
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

export function Shell({ children }: { children: ReactNode }) {
  const { user, loading, isAdmin, isSuperAdmin, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return <div className="flex min-h-screen items-center justify-center text-gray-500">Yuklanmoqda...</div>;
  }

  return (
    <div className="flex min-h-screen">
      <aside className="w-64 shrink-0 border-r border-gray-200 bg-white flex flex-col">
        <div className="px-4 py-4 border-b border-gray-200">
          <div className="font-semibold text-lg">Treatment Plan Manager</div>
          {isSuperAdmin ? (
            <div className="mt-2">
              <ClinicSwitcher />
            </div>
          ) : (
            <div className="mt-1 text-xs font-medium text-blue-700">{user.clinic?.name ?? "Filial belgilanmagan"}</div>
          )}
        </div>
        <nav className="flex-1 px-2 py-3 space-y-1">
          <Link
            href="/dashboard"
            className={`block rounded-md px-3 py-2 text-sm ${pathname === "/dashboard" ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-700 hover:bg-gray-100"}`}
          >
            Dashboard
          </Link>
          {isAdmin && (
            <>
              <div className="pt-3 pb-1 px-3 text-xs font-semibold uppercase text-gray-400">Sozlamalar</div>
              {[...(isSuperAdmin ? SUPER_ADMIN_NAV : []), ...ADMIN_NAV].map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`block rounded-md px-3 py-2 text-sm ${pathname === item.href ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-700 hover:bg-gray-100"}`}
                >
                  {item.label}
                </Link>
              ))}
            </>
          )}
        </nav>
        <div className="px-4 py-3 border-t border-gray-200 text-xs text-gray-500 flex items-center justify-between">
          <span className="truncate">{user.email}</span>
          <button onClick={logout} className="text-red-600 hover:underline shrink-0 ml-2">
            Chiqish
          </button>
        </div>
      </aside>
      <main className="flex-1 p-6 overflow-x-hidden">{children}</main>
    </div>
  );
}
