"use client";

import { useEffect, useRef, useState, use as useUnwrap } from "react";
import Link from "next/link";
import { Shell } from "@/components/shell";
import { AuthenticatedImage } from "@/components/authenticated-image";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { CaseDetail, ClinicalImageOut, UserOut } from "@/lib/types";

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
  const [uploading, setUploading] = useState(false);
  const bulkInputRef = useRef<HTMLInputElement>(null);
  const singleInputRef = useRef<HTMLInputElement>(null);
  const [singleUploadTypeId, setSingleUploadTypeId] = useState<string | null>(null);
  // A slot's external_url string doesn't change when its file is replaced
  // (same image id), so AuthenticatedImage wouldn't know to re-fetch —
  // bump this after every successful upload to force a remount/refetch.
  const [uploadVersion, setUploadVersion] = useState(0);
  const [dragOverBulk, setDragOverBulk] = useState(false);
  const [dragOverSlot, setDragOverSlot] = useState<string | null>(null);
  const [poolPickerFor, setPoolPickerFor] = useState<string | null>(null);

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

  const onBulkUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      Array.from(files).forEach((f) => form.append("files", f));
      await api.postForm(`/api/cases/${id}/images/bulk-upload`, form);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Yuklashda xatolik");
    } finally {
      setUploading(false);
      if (bulkInputRef.current) bulkInputRef.current.value = "";
    }
  };

  const onSingleUpload = async (files: FileList | null, typeId?: string | null) => {
    const targetTypeId = typeId ?? singleUploadTypeId;
    if (!files || files.length === 0 || !targetTypeId) return;
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("file", files[0]);
      await api.postForm(`/api/cases/${id}/images/${targetTypeId}`, form);
      await load();
      setUploadVersion((v) => v + 1);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Yuklashda xatolik");
    } finally {
      setUploading(false);
      setSingleUploadTypeId(null);
      if (singleInputRef.current) singleInputRef.current.value = "";
    }
  };

  const onAssignFromPool = async (imageTypeId: string, poolImageId: string) => {
    setError(null);
    try {
      await api.post(`/api/cases/${id}/images/${imageTypeId}/assign-from-pool`, { pool_image_id: poolImageId });
      await load();
      setUploadVersion((v) => v + 1);
      setPoolPickerFor(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Bulutdan biriktirishda xatolik");
    }
  };

  const isImageDrag = (e: React.DragEvent) => Array.from(e.dataTransfer.items || []).some((it) => it.kind === "file");

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
  const poolImages = data.pool_images ?? [];
  const categories = ["extraoral", "intraoral", "radiology"];
  const poolPickerType = poolPickerFor ? data.image_types.find((t) => t.id === poolPickerFor) : null;

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

        <div
          onDragOver={(e) => {
            if (!isImageDrag(e)) return;
            e.preventDefault();
            setDragOverBulk(true);
          }}
          onDragLeave={() => setDragOverBulk(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOverBulk(false);
            if (e.dataTransfer.files?.length) onBulkUpload(e.dataTransfer.files);
          }}
          className={`rounded-lg border p-4 space-y-4 transition-colors ${
            dragOverBulk ? "border-blue-400 bg-blue-50" : "border-gray-200 bg-white"
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="font-semibold">Diagnostik rasmlar</h2>
              <p className="text-xs text-gray-500">
                &quot;Hammasini yuklash&quot; rasmlarni pastdagi <strong>bulutga</strong> tashlaydi — hali avtomatik
                aniqlash yo&apos;q. Har bir katak ostidagi <strong>+</strong> tugmasi kompyuterdan to&apos;g&apos;ridan-to&apos;g&apos;ri
                yuklaydi, <strong>☁️</strong> tugmasi esa bulutdagi rasmlardan birini shu joyga biriktiradi.
              </p>
            </div>
            <label className="shrink-0 cursor-pointer rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700">
              {uploading ? "Yuklanmoqda..." : "Hammasini yuklash (bulutga)"}
              <input
                ref={bulkInputRef}
                type="file"
                accept="image/*"
                multiple
                disabled={uploading}
                onChange={(e) => onBulkUpload(e.target.files)}
                className="hidden"
              />
            </label>
          </div>

          <input
            ref={singleInputRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => onSingleUpload(e.target.files)}
          />

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
                        <div
                          onDragOver={(e) => {
                            if (!isImageDrag(e)) return;
                            e.preventDefault();
                            e.stopPropagation();
                            setDragOverSlot(t.id);
                          }}
                          onDragLeave={(e) => {
                            e.stopPropagation();
                            setDragOverSlot((cur) => (cur === t.id ? null : cur));
                          }}
                          onDrop={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            setDragOverSlot(null);
                            if (e.dataTransfer.files?.length) onSingleUpload(e.dataTransfer.files, t.id);
                          }}
                          className={`flex aspect-square w-full items-center justify-center overflow-hidden rounded transition-colors ${
                            dragOverSlot === t.id ? "bg-blue-100 ring-2 ring-blue-400" : "bg-gray-100"
                          }`}
                        >
                          {img && img.external_url ? (
                            <AuthenticatedImage
                              key={`${img.id}-${uploadVersion}`}
                              src={img.external_url}
                              alt={t.label}
                              className="h-full w-full object-cover"
                            />
                          ) : (
                            <span className="text-xs text-gray-400">Bo&apos;sh</span>
                          )}
                        </div>
                        <div className="truncate text-xs font-medium">{t.label}</div>
                        {t.is_required && !img && (
                          <span className="inline-block rounded bg-red-100 px-1.5 py-0.5 text-[10px] text-red-700">
                            Majburiy — yo&apos;q
                          </span>
                        )}
                        {img && <span className="inline-block rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600">Bor</span>}
                        <div className="flex gap-1 pt-1">
                          <button
                            type="button"
                            title="Kompyuterdan tanlab yuklash"
                            onClick={() => {
                              setSingleUploadTypeId(t.id);
                              singleInputRef.current?.click();
                            }}
                            className="flex h-7 w-7 items-center justify-center rounded border border-gray-300 text-sm hover:bg-gray-50"
                          >
                            +
                          </button>
                          <button
                            type="button"
                            title="Bulutdan tanlash"
                            onClick={() => setPoolPickerFor(t.id)}
                            className="flex h-7 w-7 items-center justify-center rounded border border-gray-300 text-sm hover:bg-gray-50"
                          >
                            ☁️
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}

          <div className="space-y-2 border-t border-gray-100 pt-3">
            <h3 className="text-sm font-semibold">☁️ Bulut ({poolImages.length})</h3>
            {poolImages.length === 0 ? (
              <p className="text-xs text-gray-400">Bulutda rasm yo&apos;q — &quot;Hammasini yuklash&quot; orqali qo&apos;shing.</p>
            ) : (
              <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6">
                {poolImages.map((p) => (
                  <div key={p.id} className="aspect-square overflow-hidden rounded border border-gray-200 bg-gray-100">
                    {p.external_url && (
                      <AuthenticatedImage key={`${p.id}-${uploadVersion}`} src={p.external_url} alt="bulut" className="h-full w-full object-cover" />
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
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

      {poolPickerFor && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={() => setPoolPickerFor(null)}
        >
          <div className="w-full max-w-lg rounded-lg bg-white p-4 space-y-3" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h3 className="font-semibold">Bulutdan tanlang — {poolPickerType?.label}</h3>
              <button onClick={() => setPoolPickerFor(null)} className="text-gray-400 hover:text-gray-600">
                ✕
              </button>
            </div>
            {poolImages.length === 0 ? (
              <p className="text-sm text-gray-500">Bulut bo&apos;sh</p>
            ) : (
              <div className="grid grid-cols-4 gap-2">
                {poolImages.map((p: ClinicalImageOut) => (
                  <button
                    key={p.id}
                    onClick={() => onAssignFromPool(poolPickerFor, p.id)}
                    className="aspect-square overflow-hidden rounded border border-gray-200 bg-gray-100 hover:border-blue-400"
                  >
                    {p.external_url && <AuthenticatedImage src={p.external_url} alt="bulut" className="h-full w-full object-cover" />}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </Shell>
  );
}
