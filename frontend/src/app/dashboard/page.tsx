"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Shell } from "@/components/shell";
import { api } from "@/lib/api";
import { onScopeClinicChange, withClinicScope } from "@/lib/clinic-scope";
import { useAuth } from "@/lib/auth-context";
import type { CaseListItem, CaseStatus, DashboardStats } from "@/lib/types";

const STATUS_COLUMNS: { status: CaseStatus; label: string }[] = [
  { status: "NEW", label: "Yangi" },
  { status: "WAITING_ASSIGNMENT", label: "Biriktirish kutilmoqda" },
  { status: "ASSIGNED", label: "Biriktirilgan" },
  { status: "IMAGES_READY", label: "Rasmlar tayyor" },
  { status: "ANALYSIS_IN_PROGRESS", label: "Tahlil qilinmoqda" },
  { status: "PLAN_IN_PROGRESS", label: "Plan tayyorlanmoqda" },
  { status: "REVIEW_REQUIRED", label: "Review kutilmoqda" },
  { status: "READY", label: "Tayyor" },
  { status: "OVERDUE", label: "Kechikkan" },
  { status: "CONSULTATION_COMPLETED", label: "Yakunlangan" },
];

function timeLeftLabel(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const diffMs = d.getTime() - Date.now();
  const past = diffMs < 0;
  const abs = Math.abs(diffMs);
  const hours = Math.floor(abs / (1000 * 60 * 60));
  const days = Math.floor(hours / 24);
  const label = days > 0 ? `${days} kun` : `${hours} soat`;
  return past ? `${label} oldin` : `${label} qoldi`;
}

export default function DashboardPage() {
  const { isSuperAdmin } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    const [s, c] = await Promise.all([
      api.get<DashboardStats>(withClinicScope("/api/cases/dashboard-stats")),
      api.get<CaseListItem[]>(withClinicScope("/api/cases")),
    ]);
    setStats(s);
    setCases(c);
  };

  useEffect(() => {
    load()
      .catch(() => {})
      .finally(() => setLoading(false));
    const interval = setInterval(() => load().catch(() => {}), 30_000);
    const unsubscribe = onScopeClinicChange(() => load().catch(() => {}));
    return () => {
      clearInterval(interval);
      unsubscribe();
    };
  }, []);

  const statCards = stats
    ? [
        { label: "Bugungi 2-konsultatsiyalar", value: stats.today_consultations },
        { label: "Yangi case'lar", value: stats.new_cases },
        { label: "Ishlanayotgan", value: stats.in_progress },
        { label: "Review kutayotgan", value: stats.review_pending },
        { label: "Tayyor", value: stats.ready },
        { label: "Kechikkan", value: stats.overdue },
      ]
    : [];

  return (
    <Shell>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Treatment Planning Dashboard</h1>
          <p className="text-sm text-gray-500">2-konsultatsiyaga tayyorgarlik holati</p>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {statCards.map((c) => (
            <div key={c.label} className="rounded-lg border border-gray-200 bg-white p-4">
              <div className="text-2xl font-bold">{loading ? "…" : c.value}</div>
              <div className="text-xs text-gray-500">{c.label}</div>
            </div>
          ))}
        </div>

        <div className="flex gap-4 overflow-x-auto pb-2">
          {STATUS_COLUMNS.map((col) => {
            const items = cases.filter((c) => c.status === col.status);
            return (
              <div key={col.status} className="w-60 shrink-0 space-y-2">
                <div className="flex items-center justify-between px-1">
                  <h3 className="text-sm font-semibold">{col.label}</h3>
                  <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{items.length}</span>
                </div>
                <div className="space-y-2">
                  {items.map((c) => (
                    <Link
                      key={c.id}
                      href={`/cases/${c.id}`}
                      className="block rounded-md border border-gray-200 bg-white p-3 hover:border-blue-400 transition-colors"
                    >
                      <div className="text-sm font-medium">{c.patient_name}</div>
                      {isSuperAdmin && c.clinic_name && (
                        <div className="text-[10px] font-medium uppercase text-blue-600">{c.clinic_name}</div>
                      )}
                      <div className="text-xs text-gray-500">{timeLeftLabel(c.consultation_datetime)}</div>
                      <div className="text-xs text-gray-500">Dr: {c.doctor_name ?? "—"}</div>
                      <div className="text-xs text-gray-500">Planner: {c.planner_name ?? "—"}</div>
                      <div className="mt-1.5 h-1.5 w-full rounded-full bg-gray-100">
                        <div
                          className="h-1.5 rounded-full bg-blue-500"
                          style={{ width: `${c.images_progress_percent}%` }}
                        />
                      </div>
                    </Link>
                  ))}
                  {items.length === 0 && <p className="px-1 text-xs text-gray-400">Bo&apos;sh</p>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Shell>
  );
}
