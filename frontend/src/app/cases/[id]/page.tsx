"use client";

import { useEffect, useRef, useState, use as useUnwrap } from "react";
import Link from "next/link";
import { Shell } from "@/components/shell";
import { AuthenticatedImage } from "@/components/authenticated-image";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { AnalysisQuestionOut, CaseDetail, CaseStatus, UserOut } from "@/lib/types";

const CATEGORY_ORDER = ["intraoral", "extraoral", "radiology"] as const;
const CATEGORY_LABELS: Record<string, string> = {
  intraoral: "Intraoral",
  extraoral: "Extraoral",
  radiology: "Radiologiya",
};

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

function statusColor(status: CaseStatus): string {
  if (status === "READY" || status === "CONSULTATION_COMPLETED") return "#15803D";
  if (status === "NEW") return "#6B7280";
  return "#B91C1C";
}

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("uz-UZ", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function answerText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Ha" : "Yo'q";
  if (Array.isArray(value)) return value.join(", ");
  return String(value);
}

export default function CaseDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = useUnwrap(params);
  const { isAdmin } = useAuth();
  const [data, setData] = useState<CaseDetail | null>(null);
  const [questions, setQuestions] = useState<AnalysisQuestionOut[]>([]);
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
  const [photoFullscreen, setPhotoFullscreen] = useState(false);
  const [selectedTypeId, setSelectedTypeId] = useState<string | null>(null);
  const [draftAssignments, setDraftAssignments] = useState<Record<string, string>>({});
  const [savingAssignments, setSavingAssignments] = useState(false);

  const load = async () => {
    const [detail, qs] = await Promise.all([
      api.get<CaseDetail>(`/api/cases/${id}`),
      api.get<AnalysisQuestionOut[]>(`/api/cases/${id}/analysis-questions`),
    ]);
    setData(detail);
    setQuestions(qs);
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

  const choosePoolImage = (poolImageId: string) => {
    if (!selectedTypeId || !data) return;
    const nextDraft = { ...draftAssignments, [selectedTypeId]: poolImageId };
    setDraftAssignments(nextDraft);

    const currentIndex = data.image_types.findIndex((type) => type.id === selectedTypeId);
    const ordered = [...data.image_types.slice(currentIndex + 1), ...data.image_types.slice(0, currentIndex + 1)];
    const occupied = new Set([...data.images.map((image) => image.image_type_id), ...Object.keys(nextDraft)]);
    const nextType = ordered.find((type) => type.is_required && !occupied.has(type.id));
    setSelectedTypeId(nextType?.id ?? null);
  };

  const saveDraftAssignments = async () => {
    const assignments = Object.entries(draftAssignments).map(([image_type_id, pool_image_id]) => ({ image_type_id, pool_image_id }));
    if (assignments.length === 0) return;
    setSavingAssignments(true);
    setError(null);
    try {
      const detail = await api.post<CaseDetail>(`/api/cases/${id}/images/batch-assign`, { assignments });
      setData(detail);
      setDraftAssignments({});
      setSelectedTypeId(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Rasmlarni saqlashda xatolik");
    } finally {
      setSavingAssignments(false);
    }
  };

  const isImageDrag = (e: React.DragEvent) => Array.from(e.dataTransfer.items || []).some((it) => it.kind === "file");

  if (error) {
    return (
      <Shell>
        <div className="rounded-md bg-status-other-bg px-3 py-2 text-sm text-status-other">{error}</div>
      </Shell>
    );
  }

  if (!data) {
    return (
      <Shell>
        <p className="text-muted">Yuklanmoqda...</p>
      </Shell>
    );
  }

  const imagesByType = new Map(data.images.map((img) => [img.image_type_id, img]));
  const poolImages = data.pool_images ?? [];
  const poolImagesById = new Map(poolImages.map((image) => [image.id, image]));
  const draftedImageIds = new Set(Object.values(draftAssignments));
  const visiblePoolImages = poolImages.filter((image) => !draftedImageIds.has(image.id));
  const displayImagesByType = new Map(imagesByType);
  Object.entries(draftAssignments).forEach(([typeId, imageId]) => {
    const image = poolImagesById.get(imageId);
    if (image) displayImagesByType.set(typeId, { ...image, image_type_id: typeId });
  });
  const faceType = data.image_types.find((t) => t.code === "face_frontal");
  const faceImage = faceType ? imagesByType.get(faceType.id) : null;

  const answeredQuestions = questions.filter((q) => q.answer && q.answer.answer_value !== null && q.answer.answer_value !== undefined);
  const findingsByAnswerId = new Map(data.findings.filter((f) => f.source_answer_id).map((f) => [f.source_answer_id as string, f]));

  return (
    <Shell>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <Link href="/dashboard" className="text-sm text-muted hover:text-ink">
            ← Orqaga
          </Link>
          <div className="min-w-0 flex-1">
            <div className="truncate text-base font-medium text-ink">{data.patient?.full_name ?? "Noma'lum bemor"}</div>
            <div className="text-xs text-muted">2-konsultatsiya: {fmt(data.consultation_datetime)}</div>
          </div>
          <span
            className="whitespace-nowrap rounded px-2.5 py-1 text-xs"
            style={{ color: statusColor(data.status), border: `1px solid ${statusColor(data.status)}` }}
          >
            {STATUS_LABELS[data.status] ?? data.status}
          </span>
          <Link
            href={`/cases/${id}/present`}
            className="whitespace-nowrap rounded-md border border-divider px-3 py-1.5 text-sm text-body hover:bg-tag-neutral-bg"
          >
            Prezentatsiya tayyorlash
          </Link>
        </div>

        <div className="grid gap-4 lg:grid-cols-[220px_repeat(3,minmax(0,1fr))]">
          <div className="relative mx-auto aspect-[3/4] w-full max-w-[220px] overflow-hidden rounded-lg bg-tag-neutral-bg lg:mx-0 lg:max-w-none">
            <button
              type="button"
              onClick={() => {
                if (!faceType) return;
                setSingleUploadTypeId(faceType.id);
                singleInputRef.current?.click();
              }}
              title="Bosh rasmni almashtirish"
              className="flex h-full w-full items-center justify-center"
            >
              {faceImage && faceImage.external_url ? (
                <AuthenticatedImage
                  key={`${faceImage.id}-${uploadVersion}`}
                  src={`${faceImage.external_url}?v=${uploadVersion}`}
                  alt={data.patient?.full_name ?? ""}
                  thumbnail
                  className="h-full w-full object-cover"
                />
              ) : (
                <span className="text-xs text-muted">+ Bosh rasm</span>
              )}
            </button>
            {faceImage && faceImage.external_url && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setPhotoFullscreen(true);
                }}
                title="To'liq ekran"
                className="absolute top-2 right-2 flex h-7 w-7 items-center justify-center rounded-md border border-white/60 bg-black/45 text-sm text-white"
              >
                ⛶
              </button>
            )}
          </div>

          <div className="rounded-lg border border-divider bg-surface p-4 text-sm">
            <h2 className="mb-1.5 font-medium text-ink">Case ma&apos;lumotlari</h2>
            <div className="text-body"><span className="text-muted">Doktor:</span> {data.doctor_name ?? "—"}</div>
            <div className="text-body"><span className="text-muted">Telefon:</span> {data.patient?.phone ?? "—"}</div>
            <div className="text-body"><span className="text-muted">Tug&apos;ilgan sana:</span> {data.patient?.birth_date ?? "—"}</div>
            <div className="text-body"><span className="text-muted">Deadline:</span> {fmt(data.deadline)}</div>
          </div>

          <div className="rounded-lg border border-divider bg-surface p-4">
            <h2 className="mb-1.5 text-sm font-medium text-ink">Mas&apos;ul planner</h2>
            <div className="text-sm text-body">{data.planner_name ?? <span className="text-muted">Biriktirilmagan</span>}</div>
            {isAdmin && (
              <select
                defaultValue=""
                disabled={assigning}
                onChange={(e) => onAssign(e.target.value)}
                className="mt-2 w-full rounded-md border border-divider px-2 py-1.5 text-sm"
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

          <div className="rounded-lg border border-divider bg-surface p-4">
            <h2 className="mb-1.5 text-sm font-medium text-ink">Diagnostika progress</h2>
            <div className="my-1.5 h-1.5 w-full overflow-hidden rounded-full bg-tag-neutral-bg">
              <div className="h-full bg-accent" style={{ width: `${data.images_progress_percent}%` }} />
            </div>
            <div className="mb-2 text-xs text-muted">{data.images_progress_percent}% majburiy rasmlar tayyor</div>
            <Link
              href={`/cases/${id}/analysis`}
              className="block w-full rounded-md bg-accent px-3 py-2 text-center text-sm font-medium text-white hover:bg-accent-hover"
            >
              Tahlilni boshlash
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
          className={`space-y-4 rounded-lg border p-4 transition-colors ${
            dragOverBulk ? "border-accent bg-tag-accent-bg" : "border-divider bg-surface"
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h2 className="font-medium text-ink">Diagnostik rasmlar</h2>
              <p className="text-xs text-muted">
                Chapdan kerakli joyni, keyin o&apos;ngdan mos rasmni bosing. Dastur avtomatik keyingi bo&apos;sh joyga o&apos;tadi;
                hammasini oxirida bir marta saqlaysiz.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {Object.keys(draftAssignments).length > 0 && (
                <>
                  <button
                    type="button"
                    onClick={() => { setDraftAssignments({}); setSelectedTypeId(null); }}
                    className="rounded-md border border-divider px-3 py-2 text-sm text-body hover:bg-tag-neutral-bg"
                  >
                    Bekor qilish
                  </button>
                  <button
                    type="button"
                    disabled={savingAssignments}
                    onClick={saveDraftAssignments}
                    className="rounded-md bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-60"
                  >
                    {savingAssignments ? "Saqlanmoqda..." : `${Object.keys(draftAssignments).length} ta rasmni saqlash`}
                  </button>
                </>
              )}
              <label className="shrink-0 cursor-pointer rounded-md border border-accent px-3 py-2 text-sm font-medium text-accent hover:bg-tag-accent-bg">
                {uploading ? "Yuklanmoqda..." : "Kompyuterdan rasmlar qo‘shish"}
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
          </div>

          <input ref={singleInputRef} type="file" accept="image/*" className="hidden" onChange={(e) => onSingleUpload(e.target.files)} />
          <div className="grid gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(320px,2fr)]">
          <div className="space-y-4">
          {CATEGORY_ORDER.map((cat) => {
            const typesInCat = data.image_types.filter((t) => t.category === cat);
            if (typesInCat.length === 0) return null;
            return (
              <div key={cat} className="space-y-2">
                <h3 className="text-sm font-medium text-ink">{CATEGORY_LABELS[cat] ?? cat}</h3>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
                  {typesInCat.map((t) => {
                    const img = displayImagesByType.get(t.id);
                    const isSelected = selectedTypeId === t.id;
                    const isDraft = Boolean(draftAssignments[t.id]);
                    return (
                      <div
                        key={t.id}
                        onClick={() => setSelectedTypeId(t.id)}
                        className={`cursor-pointer space-y-1 rounded-md border p-2 transition ${
                          isSelected ? "border-accent bg-tag-accent-bg ring-2 ring-accent/20" : "border-divider hover:border-accent"
                        }`}
                      >
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
                            dragOverSlot === t.id ? "bg-tag-accent-bg ring-2 ring-accent" : "bg-tag-neutral-bg"
                          }`}
                        >
                          {img && img.external_url ? (
                            <AuthenticatedImage
                              key={`${img.id}-${uploadVersion}`}
                              src={`${img.external_url}?v=${uploadVersion}`}
                              alt={t.label}
                              thumbnail
                              className="h-full w-full object-cover"
                            />
                          ) : (
                            <span className="text-xs text-muted">Bo&apos;sh</span>
                          )}
                        </div>
                        <div className="truncate text-xs font-medium text-ink">{t.label}</div>
                        {t.is_required && !img && (
                          <span className="inline-block rounded bg-status-other-bg px-1.5 py-0.5 text-[10px] text-status-other">Majburiy</span>
                        )}
                        {img && <span className="inline-block rounded bg-tag-neutral-bg px-1.5 py-0.5 text-[10px] text-tag-neutral-text">{isDraft ? "Tanlandi" : "Bor"}</span>}
                        <div className="flex gap-1 pt-1">
                          <button
                            type="button"
                            title="Kompyuterdan tanlab yuklash"
                            onClick={() => {
                              setSingleUploadTypeId(t.id);
                              singleInputRef.current?.click();
                            }}
                            className="flex h-7 w-7 items-center justify-center rounded border border-divider text-sm hover:bg-tag-neutral-bg"
                          >
                            +
                          </button>
                          <button
                            type="button"
                            title="O‘ng tomondan rasm tanlash"
                            onClick={(event) => { event.stopPropagation(); setSelectedTypeId(t.id); }}
                            className="flex h-7 w-7 items-center justify-center rounded border border-divider text-sm hover:bg-tag-neutral-bg"
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
          </div>

          <div className="space-y-2 rounded-lg border border-divider bg-tag-neutral-bg/40 p-3 xl:sticky xl:top-4 xl:max-h-[calc(100vh-2rem)] xl:self-start xl:overflow-y-auto">
            <div className="flex items-center justify-between gap-2">
              <h3 className="text-sm font-medium text-ink">Clinic Cards rasmlari ({visiblePoolImages.length})</h3>
              <span className="text-xs text-muted">{selectedTypeId ? "Rasmni bosing" : "Avval chapdan joy tanlang"}</span>
            </div>
            {visiblePoolImages.length === 0 ? (
              <p className="text-xs text-muted">Bulutda rasm yo&apos;q — &quot;Hammasini yuklash&quot; orqali qo&apos;shing.</p>
            ) : (
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 xl:grid-cols-3">
                {visiblePoolImages.map((p) => (
                  <button
                    type="button"
                    disabled={!selectedTypeId}
                    onClick={() => choosePoolImage(p.id)}
                    key={p.id}
                    className="aspect-square overflow-hidden rounded border border-divider bg-tag-neutral-bg transition hover:border-accent hover:ring-2 hover:ring-accent/20 disabled:cursor-not-allowed disabled:opacity-70"
                  >
                    {p.external_url && (
                      <AuthenticatedImage src={p.external_url} alt="Clinic Cards rasmi" thumbnail className="h-full w-full object-cover" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
          </div>
        </div>

        <div className="rounded-lg border border-divider bg-surface p-4">
          <h2 className="mb-2 font-medium text-ink">Master Problem List</h2>
          {answeredQuestions.length === 0 ? (
            <p className="text-sm text-muted">Hali savollarga javob berilmagan — Clinical Analysis Wizard orqali to&apos;ldiriladi.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {answeredQuestions.map((q) => {
                const finding = q.answer ? findingsByAnswerId.get(q.answer.id) : undefined;
                return (
                  <li key={q.template.id} className="border-b border-divider pb-2 last:border-0">
                    <span className="font-medium text-ink">{q.template.category}:</span> {q.template.question} —{" "}
                    {answerText(q.answer?.answer_value?.value)}
                    {finding && (
                      <span className="ml-2 inline-block rounded border border-status-other px-1.5 py-0.5 text-[10px] text-status-other">
                        Muammo
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="rounded-lg border border-divider bg-surface p-4">
          <h2 className="mb-2 font-medium text-ink">Tarix (Audit log)</h2>
          {data.audit_log.length === 0 ? (
            <p className="text-sm text-muted">Hali harakat yo&apos;q</p>
          ) : (
            <ol className="space-y-2 text-sm">
              {data.audit_log.map((a, idx) => (
                <li key={idx} className="flex gap-3">
                  <span className="shrink-0 text-muted">{fmt(a.created_at)}</span>
                  <span className="text-body">
                    {a.action}
                    {a.details ? ` — ${JSON.stringify(a.details)}` : ""}
                  </span>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>

      {photoFullscreen && faceImage && faceImage.external_url && (
        <div
          onClick={() => setPhotoFullscreen(false)}
          className="fixed inset-0 z-[1000] flex items-center justify-center p-5"
          style={{ background: "rgba(22,36,28,0.92)" }}
        >
          <AuthenticatedImage src={`${faceImage.external_url}?v=${uploadVersion}`} alt={data.patient?.full_name ?? ""} className="max-h-full max-w-full object-contain" />
        </div>
      )}

    </Shell>
  );
}
