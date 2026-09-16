"use client";

import { useEffect, useState, use as useUnwrap } from "react";
import Link from "next/link";
import { Shell } from "@/components/shell";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { CaseDetail, UserOut } from "@/lib/types";

const CATEGORY_LABELS: Record<string, string> = {
  extraoral: "Extraoral",
  intraoral: "Intraoral",
  radiology: "Radiology",
};

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("uz-UZ", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function CaseDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = useUnwrap(params);
  const { isAdmin } = useAuth();
  const [data, setData] = useState<CaseDetail | null>(null);
  const [planners, setPlanners] = useState<UserOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [assigning, setAssigning] = useState(false);

  const load = async () => {
    const detail = await api.get<CaseDetail>(`/api/cases/${id}`);
    setData(detail);
    if (isAdmin) {
      const roster = await api.get<UserOut[]>("/api/users/planners");
      setPlanners(roster);
    }
  };

  useEffect(() => {
    load().catch((e) => setError(e instanceof ApiError ? e.message : "Xatolik"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, isAdmin]);

  const onAssign = async (plannerId: string) => {
    if (!plannerId) return;
    setAssigning(true);
    try {
      await api.post(`/api/cases/${id}/assign`, { planner_user_id: plannerId });
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Xatolik");
    } finally {
      setAssigning(false);
    }
  };

  if (error) {
    return (
      <Shell>
        <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
      </Shell>
    );
  }

  if (!data) {
    return (
      <Shell>
        <p className="text-gray-500">Yuklanmoqda...</p>
      </Shell>
    );
  }

  const imagesByType = new Map(data.images.map((img) => [img.image_type_id, img]));
  const categories = ["extraoral", "intraoral", "radiology"];

  return (
    <Shell>
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Link href="/dashboard" className="text-gray-500 hover:text-gray-700">
            ← Orqaga
          </Link>
          <div className="flex-1">
            <h1 className="text-2xl font-bold">{data.patient?.full_name ?? "Noma'lum bemor"}</h1>
            <p className="text-sm text-gray-500">2-konsultatsiya: {fmt(data.consultation_datetime)}</p>
          </div>
          <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium">{data.status}</span>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-2 text-sm">
            <h2 className="font-semibold mb-2">Case ma&apos;lumotlari</h2>
            <div><span className="text-gray-500">Doktor:</span> {data.doctor_name ?? "—"}</div>
            <div><span className="text-gray-500">Telefon:</span> {data.patient?.phone ?? "—"}</div>
            <div><span className="text-gray-500">Tug&apos;ilgan sana:</span> {data.patient?.birth_date ?? "—"}</div>
            <div><span className="text-gray-500">Deadline:</span> {fmt(data.deadline)}</div>
            <div><span className="text-gray-500">Priority:</span> {data.priority}</div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
            <h2 className="font-semibold">Mas&apos;ul planner</h2>
            <div className="text-sm">{data.planner_name ?? <span className="text-gray-400">Biriktirilmagan</span>}</div>
            {isAdmin && (
              <select
                defaultValue=""
                disabled={assigning}
                onChange={(e) => onAssign(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
              >
                <option value="" disabled>
                  Planner tanlash / o&apos;zgartirish
                </option>
                {planners.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.full_name}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
            <h2 className="font-semibold">Diagnostika progress</h2>
            <div className="h-2 w-full rounded-full bg-gray-100">
              <div className="h-2 rounded-full bg-blue-500" style={{ width: `${data.images_progress_percent}%` }} />
            </div>
            <div className="text-sm text-gray-500">{data.images_progress_percent}% majburiy rasmlar tayyor</div>
            <Link
              href={`/cases/${id}/analysis`}
              className="block w-full rounded-md bg-blue-600 px-3 py-2 text-center text-sm font-medium text-white hover:bg-blue-700"
            >
              TAHLILNI BOSHLASH
            </Link>
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-4">
          <h2 className="font-semibold">Diagnostik rasmlar</h2>
          {categories.map((cat) => {
            const typesInCat = data.image_types.filter((t) => t.category === cat);
            if (typesInCat.length === 0) return null;
            return (
              <div key={cat} className="space-y-2">
                <h3 className="text-sm font-semibold">{CATEGORY_LABELS[cat] ?? cat}</h3>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
                  {typesInCat.map((t) => {
                    const img = imagesByType.get(t.id);
                    return (
                      <div key={t.id} className="rounded-md border border-gray-200 p-2 space-y-1">
                        <div className="flex aspect-square items-center justify-center rounded bg-gray-100 overflow-hidden">
                          {img ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={img.external_url ?? undefined}
                              alt={t.label}
                              className="h-full w-full object-cover"
                              onError={(e) => {
                                (e.currentTarget as HTMLImageElement).style.display = "none";
                              }}
                            />
                          ) : (
                            <span className="text-xs text-gray-400">Yo&apos;q</span>
                          )}
                        </div>
                        <div className="truncate text-xs font-medium">{t.label}</div>
                        {t.is_required && !img && (
                          <span className="inline-block rounded bg-red-100 px-1.5 py-0.5 text-[10px] text-red-700">
                            Majburiy — yo&apos;q
                          </span>
                        )}
                        {img && <span className="inline-block rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600">Bor</span>}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="font-semibold mb-2">Master Problem List</h2>
          {data.findings.length === 0 ? (
            <p className="text-sm text-gray-500">
              Hali muammolar aniqlanmagan — Clinical Analysis Wizard (Phase 5-7) orqali to&apos;ldiriladi.
            </p>
          ) : (
            <ul className="space-y-2 text-sm">
              {data.findings.map((f) => (
                <li key={f.id} className="border-b border-gray-100 pb-2 last:border-0">
                  <span className="font-medium">{f.category}:</span> {f.description}
                  {!f.is_confirmed && (
                    <span className="ml-2 inline-block rounded border border-gray-300 px-1.5 py-0.5 text-[10px] text-gray-500">
                      Tasdiqlanmagan
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="font-semibold mb-2">Tarix (Audit log)</h2>
          {data.audit_log.length === 0 ? (
            <p className="text-sm text-gray-500">Hali harakat yo&apos;q</p>
          ) : (
            <ol className="space-y-2 text-sm">
              {data.audit_log.map((a, idx) => (
                <li key={idx} className="flex gap-3">
                  <span className="shrink-0 text-gray-400">{fmt(a.created_at)}</span>
                  <span>
                    {a.action}
                    {a.details ? ` — ${JSON.stringify(a.details)}` : ""}
                  </span>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </Shell>
  );
}
