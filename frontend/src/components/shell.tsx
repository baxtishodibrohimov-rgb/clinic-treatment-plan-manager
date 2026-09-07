"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode, useEffect } from "react";
import { useAuth } from "@/lib/auth-context";

const ADMIN_NAV = [
  { href: "/admin/staff", label: "Planner/Doctor rollari" },
  { href: "/admin/image-types", label: "Rasm turlari" },
  { href: "/admin/reminders", label: "Eslatmalar" },
  { href: "/admin/settings", label: "Sozlamalar" },
];

export function Shell({ children }: { children: ReactNode }) {
  const { user, loading, isAdmin, logout } = useAuth();
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
        <div className="px-4 py-4 font-semibold text-lg border-b border-gray-200">Treatment Plan Manager</div>
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
              {ADMIN_NAV.map((item) => (
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
