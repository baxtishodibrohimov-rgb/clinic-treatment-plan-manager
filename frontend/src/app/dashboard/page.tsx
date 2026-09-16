"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Shell } from "@/components/shell";
import { api, ApiError } from "@/lib/api";
import { onScopeClinicChange, withClinicScope } from "@/lib/clinic-scope";
import { useAuth } from "@/lib/auth-context";
import type { CaseListItem, CaseStatus, ClinicOut, DailyConsultationCount, DashboardStats, DoctorOut } from "@/lib/types";

function toLocalDateValue(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function toLocalDatetimeInputValue(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${toLocalDateValue(d)}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function addDays(date: Date, days: number): Date {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
}

function NewPatientModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const { isSuperAdmin } = useAuth();
  const [doctors, setDoctors] = useState<DoctorOut[]>([]);
  const [clinics, setClinics] = useState<ClinicOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    full_name: "",
    birth_date: "",
    phone: "",
    doctor_name: "",
    consultation_datetime: toLocalDatetimeInputValue(new Date()),
    priority: "normal",
    clinic_id: "",
  });

  useEffect(() => {
    api
      .get<DoctorOut[]>("/api/cases/doctors")
      .then(setDoctors)
      .catch(() => {});
    if (isSuperAdmin) {
      api
        .get<ClinicOut[]>("/api/clinics")
        .then(setClinics)
        .catch(() => {});
    }
  }, [isSuperAdmin]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await api.post("/api/cases/manual", {
        full_name: form.full_name,
        birth_date: form.birth_date || null,
        phone: form.phone || null,
        doctor_name: form.doctor_name || null,
        consultation_datetime: new Date(form.consultation_datetime).toISOString(),
        priority: form.priority,
        clinic_id: form.clinic_id || null,
      });
      onCreated();
      onClose();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Xatolik");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <form onSubmit={submit} className="w-full max-w-md space-y-3 rounded-lg bg-white p-5 shadow-lg">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Yangi bemor / case</h2>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>

        {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">F.I.Sh *</label>
          <input
            required
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-600">Tug&apos;ilgan sana</label>
            <input
              type="date"
              value={form.birth_date}
              onChange={(e) => setForm({ ...form, birth_date: e.target.value })}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-600">Telefon</label>
            <input
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              placeholder="+998..."
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-600">Shifokor</label>
          <select
            value={form.doctor_name}
            onChange={(e) => setForm({ ...form, doctor_name: e.target.value })}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            <option value="">— tanlanmagan —</option>
            {doctors.map((d) => (
              <option key={d.id} value={d.full_name}>
                {d.full_name}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-600">2-konsultatsiya vaqti *</label>
            <input
              required
              type="datetime-local"
              value={form.consultation_datetime}
              onChange={(e) => setForm({ ...form, consultation_datetime: e.target.value })}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-600">Muhimlik</label>
            <select
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="low">Past</option>
              <option value="normal">Oddiy</option>
              <option value="high">Yuqori</option>
              <option value="urgent">Shoshilinch</option>
            </select>
          </div>
        </div>

        {isSuperAdmin && (
          <div className="space-y-1">
            <label className="text-xs font-medium text-gray-600">Filial *</label>
            <select
              required
              value={form.clinic_id}
              onChange={(e) => setForm({ ...form, clinic_id: e.target.value })}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="">Filialni tanlang</option>
              {clinics.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <button
          type="submit"
          disabled={saving}
          className="w-full rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? "..." : "Yaratish"}
        </button>
      </form>
    </div>
  );
}

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
  const [dailyCounts, setDailyCounts] = useState<DailyConsultationCount[]>([]);
  const [selectedDate, setSelectedDate] = useState(() => toLocalDateValue(new Date()));
  const [loading, setLoading] = useState(true);
  const [showNewPatient, setShowNewPatient] = useState(false);

  const load = async () => {
    const rangeStart = toLocalDateValue(new Date());
    const rangeEnd = toLocalDateValue(addDays(new Date(), 60));
    const [s, c, daily] = await Promise.all([
      api.get<DashboardStats>(withClinicScope("/api/cases/dashboard-stats")),
      api.get<CaseListItem[]>(withClinicScope("/api/cases")),
      api.get<DailyConsultationCount[]>(withClinicScope(`/api/cases/second-consultations/daily?from=${rangeStart}&to=${rangeEnd}`)),
    ]);
    setStats(s);
    setCases(c);
    setDailyCounts(daily);
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

  const selectedCases = cases.filter(
    (item) => item.consultation_datetime && toLocalDateValue(new Date(item.consultation_datetime)) === selectedDate,
  );
  const selectedDayCount = selectedCases.length;
  const busyDays = dailyCounts.filter((item) => item.count > 0);

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
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Treatment Planning Dashboard</h1>
            <p className="text-sm text-gray-500">2-konsultatsiyaga tayyorgarlik holati</p>
          </div>
          <button
            onClick={() => setShowNewPatient(true)}
            className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            + Yangi bemor
          </button>
        </div>

        {showNewPatient && <NewPatientModal onClose={() => setShowNewPatient(false)} onCreated={load} />}

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {statCards.map((c) => (
            <div key={c.label} className="rounded-lg border border-gray-200 bg-white p-4">
              <div className="text-2xl font-bold">{loading ? "…" : c.value}</div>
              <div className="text-xs text-gray-500">{c.label}</div>
            </div>
          ))}
        </div>

        <section className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-base font-semibold">2-konsultatsiyalar kalendari</h2>
              <p className="text-xs text-gray-500">Sanani tanlang — shu kundagi konsultatsiyalar soni ko‘rinadi</p>
            </div>
            <div className="flex items-end gap-3">
              <label className="space-y-1">
                <span className="block text-xs font-medium text-gray-600">Sana</span>
                <input
                  type="date"
                  min={toLocalDateValue(new Date())}
                  max={toLocalDateValue(addDays(new Date(), 60))}
                  value={selectedDate}
                  onChange={(event) => setSelectedDate(event.target.value)}
                  className="rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </label>
              <div className="min-w-28 rounded-md bg-blue-50 px-4 py-2 text-center">
                <div className="text-2xl font-bold text-blue-700">{loading ? "…" : selectedDayCount}</div>
                <div className="text-[11px] text-blue-700">2-konsultatsiya</div>
              </div>
            </div>
          </div>

          <div className="mt-4 flex gap-2 overflow-x-auto pb-1">
            {busyDays.map((item) => (
              <button
                key={item.date}
                type="button"
                onClick={() => setSelectedDate(item.date)}
                className={`shrink-0 rounded-md border px-3 py-2 text-left text-xs ${
                  item.date === selectedDate ? "border-blue-500 bg-blue-50 text-blue-700" : "border-gray-200 hover:border-blue-300"
                }`}
              >
                <span className="block font-medium">{new Date(`${item.date}T00:00:00`).toLocaleDateString("uz-UZ", { day: "2-digit", month: "short" })}</span>
                <span>{item.count} ta</span>
              </button>
            ))}
            {!loading && busyDays.length === 0 && <p className="text-xs text-gray-400">Keyingi 60 kunda konsultatsiya topilmadi</p>}
          </div>

          <div className="mt-4 border-t border-gray-100 pt-4">
            <h3 className="mb-2 text-sm font-semibold">Tanlangan sanadagi konsultatsiyalar</h3>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {selectedCases.map((item) => (
                <Link
                  key={item.id}
                  href={`/cases/${item.id}`}
                  className="rounded-md border border-gray-200 p-3 transition-colors hover:border-blue-400 hover:bg-blue-50/40"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="text-sm font-medium">{item.patient_name}</div>
                    <div className="text-xs font-semibold text-blue-700">
                      {item.consultation_datetime
                        ? new Date(item.consultation_datetime).toLocaleTimeString("uz-UZ", { hour: "2-digit", minute: "2-digit" })
                        : "—"}
                    </div>
                  </div>
                  <div className="mt-1 text-xs text-gray-500">
                    {STATUS_COLUMNS.find((column) => column.status === item.status)?.label ?? item.status}
                  </div>
                  <div className="text-xs text-gray-500">Doktor: {item.doctor_name ?? "—"}</div>
                  <div className="text-xs text-gray-500">Planner: {item.planner_name ?? "biriktirilmagan"}</div>
                </Link>
              ))}
              {!loading && selectedCases.length === 0 && (
                <div className="rounded-md border border-dashed border-gray-200 p-4 text-sm text-gray-400 sm:col-span-2 lg:col-span-3">
                  Bu sanada 2-konsultatsiya yo‘q.
                </div>
              )}
            </div>
          </div>
        </section>

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
