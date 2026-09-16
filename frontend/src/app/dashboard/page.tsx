"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Shell } from "@/components/shell";
import { AuthenticatedImage } from "@/components/authenticated-image";
import { api, ApiError } from "@/lib/api";
import { onScopeClinicChange, withClinicScope } from "@/lib/clinic-scope";
import { useAuth } from "@/lib/auth-context";
import type { CaseListItem, CaseStatus, ClinicOut, DoctorOut, ImageTypeOut } from "@/lib/types";

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

const UZ_MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"];

function formatUzDate(d: Date): string {
  return `${d.getDate()}-${UZ_MONTHS[d.getMonth()]}, ${d.getFullYear()}`;
}

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

const STATUS_LABELS: Record<CaseStatus, string> = {
  NEW: "Yangi",
  WAITING_ASSIGNMENT: "Biriktirish kutilmoqda",
  ASSIGNED: "Biriktirilgan",
  IMAGES_READY: "Rasmlar tayyor",
  ANALYSIS_IN_PROGRESS: "Tahlil qilinmoqda",
  PLAN_IN_PROGRESS: "Plan tayyorlanmoqda",
  REVIEW_REQUIRED: "Review kutilmoqda",
  READY: "Tayyor",
  OVERDUE: "Kechikkan",
  CONSULTATION_COMPLETED: "Yakunlangan",
};

// Status-color triad per the design handoff: ready/completed = green, brand
// new = grey, everything still in flight = red (a visual "needs attention").
function statusColor(status: CaseStatus): string {
  if (status === "READY" || status === "CONSULTATION_COMPLETED") return "#15803D";
  if (status === "NEW") return "#6B7280";
  return "#B91C1C";
}
function statusBg(status: CaseStatus): string {
  if (status === "READY" || status === "CONSULTATION_COMPLETED") return "#E6F7EA";
  if (status === "NEW") return "#F1F2F0";
  return "#FDECEC";
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
      <form onSubmit={submit} className="w-full max-w-md space-y-3 rounded-lg bg-surface p-5 shadow-lg">
        <div className="flex items-center justify-between">
          <h2 className="font-heading text-lg font-medium">Yangi bemor / case</h2>
          <button type="button" onClick={onClose} className="text-muted hover:text-ink">
            ✕
          </button>
        </div>

        {error && <div className="rounded-md bg-status-other-bg px-3 py-2 text-sm text-status-other">{error}</div>}

        <div className="space-y-1">
          <label className="text-xs font-medium text-muted">F.I.Sh *</label>
          <input
            required
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            className="w-full rounded-md border border-divider px-3 py-2 text-sm"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted">Tug&apos;ilgan sana</label>
            <input
              type="date"
              value={form.birth_date}
              onChange={(e) => setForm({ ...form, birth_date: e.target.value })}
              className="w-full rounded-md border border-divider px-3 py-2 text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted">Telefon</label>
            <input
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              placeholder="+998..."
              className="w-full rounded-md border border-divider px-3 py-2 text-sm"
            />
          </div>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-medium text-muted">Shifokor</label>
          <select
            value={form.doctor_name}
            onChange={(e) => setForm({ ...form, doctor_name: e.target.value })}
            className="w-full rounded-md border border-divider px-3 py-2 text-sm"
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
            <label className="text-xs font-medium text-muted">2-konsultatsiya vaqti *</label>
            <input
              required
              type="datetime-local"
              value={form.consultation_datetime}
              onChange={(e) => setForm({ ...form, consultation_datetime: e.target.value })}
              className="w-full rounded-md border border-divider px-3 py-2 text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted">Muhimlik</label>
            <select
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
              className="w-full rounded-md border border-divider px-3 py-2 text-sm"
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
            <label className="text-xs font-medium text-muted">Filial *</label>
            <select
              required
              value={form.clinic_id}
              onChange={(e) => setForm({ ...form, clinic_id: e.target.value })}
              className="w-full rounded-md border border-divider px-3 py-2 text-sm"
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
          className="w-full rounded-md bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50"
        >
          {saving ? "..." : "Yaratish"}
        </button>
      </form>
    </div>
  );
}

function PatientCard({ item, faceTypeId, onPhotoUploaded }: { item: CaseListItem; faceTypeId: string | null; onPhotoUploaded: () => void }) {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const uploadPhoto = async (files: FileList | null) => {
    if (!files || files.length === 0 || !faceTypeId) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", files[0]);
      await api.postForm(`/api/cases/${item.id}/images/${faceTypeId}`, form);
      onPhotoUploaded();
    } catch {
      // best-effort — the case detail page's upload UI shows real errors
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div className="overflow-hidden rounded-md" style={{ backgroundColor: statusBg(item.status) }}>
      <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={(e) => uploadPhoto(e.target.files)} />
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        title="Rasmni almashtirish"
        className="flex h-40 w-full items-center justify-center bg-tag-neutral-bg"
      >
        {item.face_photo_url ? (
          <AuthenticatedImage src={item.face_photo_url} alt={item.patient_name} className="h-full w-full object-cover" />
        ) : (
          <span className="text-xs text-muted">{uploading ? "Yuklanmoqda..." : "+ Rasm"}</span>
        )}
      </button>
      <div onClick={() => router.push(`/cases/${item.id}`)} className="cursor-pointer p-3">
        <div className="truncate text-sm font-medium text-ink">{item.patient_name}</div>
        {item.clinic_name && (
          <span className="mt-1.5 inline-block max-w-full truncate rounded bg-tag-accent-bg px-2 py-0.5 text-[10px] text-tag-accent-text">
            {item.clinic_name}
          </span>
        )}
        <div className="mt-1.5 text-xs text-muted">
          Qabul vaqti: {item.consultation_datetime ? new Date(item.consultation_datetime).toLocaleTimeString("uz-UZ", { hour: "2-digit", minute: "2-digit" }) : "—"}
          {" · "}
          {timeLeftLabel(item.consultation_datetime)}
        </div>
        <div className="text-xs text-muted">Dr: {item.doctor_name ?? "—"}</div>
        <span
          className="mt-1.5 inline-block rounded px-2 py-0.5 text-[10px]"
          style={{ color: statusColor(item.status), border: `1px solid ${statusColor(item.status)}` }}
        >
          {STATUS_LABELS[item.status] ?? item.status}
        </span>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [faceTypeId, setFaceTypeId] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState(() => new Date());
  const [loading, setLoading] = useState(true);
  const [showNewPatient, setShowNewPatient] = useState(false);

  const load = async () => {
    const [c, types] = await Promise.all([
      api.get<CaseListItem[]>(withClinicScope("/api/cases")),
      api.get<ImageTypeOut[]>("/api/image-types"),
    ]);
    setCases(c);
    setFaceTypeId(types.find((t) => t.code === "face_frontal")?.id ?? null);
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

  const selectedDateValue = toLocalDateValue(selectedDate);
  const selectedCases = cases.filter(
    (item) => item.consultation_datetime && toLocalDateValue(new Date(item.consultation_datetime)) === selectedDateValue,
  );

  return (
    <Shell>
      <div className="space-y-4">
        {showNewPatient && <NewPatientModal onClose={() => setShowNewPatient(false)} onCreated={load} />}

        <div className="flex justify-end">
          <button
            onClick={() => setShowNewPatient(true)}
            className="rounded-md bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-accent-hover"
          >
            + Yangi bemor
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            title="Oldingi kun"
            onClick={() => setSelectedDate((d) => addDays(d, -1))}
            className="rounded-md px-2.5 py-1 text-accent hover:bg-tag-neutral-bg"
          >
            ←
          </button>
          <span className="font-heading text-base font-medium">{formatUzDate(selectedDate)}</span>
          <button
            type="button"
            title="Keyingi kun"
            onClick={() => setSelectedDate((d) => addDays(d, 1))}
            className="rounded-md px-2.5 py-1 text-accent hover:bg-tag-neutral-bg"
          >
            →
          </button>
          <span className="text-sm text-muted">Jami {loading ? "…" : selectedCases.length} ta 2-konsultatsiya</span>
        </div>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {selectedCases.map((item) => (
            <PatientCard key={item.id} item={item} faceTypeId={faceTypeId} onPhotoUploaded={load} />
          ))}
        </div>
        {!loading && selectedCases.length === 0 && (
          <div className="rounded-md border border-dashed border-divider p-6 text-center text-sm text-muted">
            Bu sanada 2-konsultatsiya yo&apos;q.
          </div>
        )}
      </div>
    </Shell>
  );
}
