"use client";

import Link from "next/link";
import { Shell } from "@/components/shell";
import { useAuth } from "@/lib/auth-context";

const CARDS = [
  { href: "/admin/staff", title: "Planner/Doctor rollari", desc: "Xodimlarga planner/shifokor rolini biriktirish, ish yukini belgilash." },
  { href: "/admin/image-types", title: "Rasm turlari", desc: "Majburiy/ixtiyoriy rasm turlari va ularning tartibi." },
  { href: "/admin/reminders", title: "Eslatmalar", desc: "Konsultatsiyadan oldin/keyin yuboriladigan eslatma qoidalari." },
  { href: "/admin/settings", title: "Tizim sozlamalari", desc: "Biriktirish algoritmi (auto/manual), Cliniccards sync jurnali." },
];

const SUPER_ADMIN_CARD = { href: "/admin/clinics", title: "Filiallar", desc: "Klinika filiallarini qo'shish/tahrirlash." };

export default function SettingsHubPage() {
  const { isSuperAdmin } = useAuth();
  const cards = isSuperAdmin ? [SUPER_ADMIN_CARD, ...CARDS] : CARDS;

  return (
    <Shell>
      <div className="space-y-4">
        <h1 className="font-heading text-xl font-medium">Sozlamalar</h1>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {cards.map((c) => (
            <Link
              key={c.href}
              href={c.href}
              className="rounded-md border border-divider bg-surface p-4 shadow-[0_0_0_1px_rgba(22,36,28,0.08)] transition-shadow hover:shadow-[0_0_0_1px_rgba(22,36,28,0.08),0_6px_18px_rgba(22,36,28,0.08)]"
            >
              <div className="text-sm font-medium text-ink">{c.title}</div>
              <p className="mt-1 text-xs text-muted">{c.desc}</p>
            </Link>
          ))}
        </div>
      </div>
    </Shell>
  );
}
