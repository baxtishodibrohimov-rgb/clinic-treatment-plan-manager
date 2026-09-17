"use client";

import { useEffect, useState, use as useUnwrap } from "react";
import Link from "next/link";
import { Shell } from "@/components/shell";
import { DentalChart } from "@/components/dental-chart";
import { AuthenticatedImage } from "@/components/authenticated-image";
import { AnnotationCanvas } from "@/components/annotation-canvas";
import { api, ApiError } from "@/lib/api";
import { DENTAL_CHART_JAW_BY_CODE, PILL_CODES, WIZARD_FLOW } from "@/lib/wizard-flow";
import type { AnalysisAnswerOut, AnalysisQuestionOut, AnyMark, CaseDetail, DentalChartOut } from "@/lib/types";

function QuestionField({
  q,
  onSave,
  dark = false,
}: {
  q: AnalysisQuestionOut;
  onSave: (templateId: string, value: string | boolean) => void;
  dark?: boolean;
}) {
  const currentValue = q.answer?.answer_value?.value ?? null;
  const [text, setText] = useState(typeof currentValue === "string" && q.template.answer_type === "text" ? currentValue : "");
  useEffect(() => {
    setText(typeof currentValue === "string" && q.template.answer_type === "text" ? currentValue : "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q.template.id, currentValue]);

  const labelClass = dark ? "block text-base font-medium text-white" : "block text-base font-medium text-ink";

  if (q.template.answer_type === "single_choice") {
    return (
      <div className="space-y-2">
        <label className={labelClass}>{q.template.question}</label>
        <div className="flex flex-wrap gap-2">
          {q.template.options.map((opt) => (
            <button
              key={opt}
              onClick={() => onSave(q.template.id, opt)}
              className={`rounded-full border px-4 py-1.5 text-sm font-semibold transition-colors ${
                currentValue === opt
                  ? "border-accent bg-accent text-white"
                  : dark
                    ? "border-white/30 text-white/80 hover:bg-white/10"
                    : "border-divider text-body hover:bg-tag-neutral-bg"
              }`}
            >
              {opt}
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (q.template.answer_type === "boolean") {
    return (
      <div className="space-y-2">
        <label className={labelClass}>{q.template.question}</label>
        <div className="flex gap-2">
          {[
            { label: "Ha", val: true },
            { label: "Yo'q", val: false },
          ].map((opt) => (
            <button
              key={opt.label}
              onClick={() => onSave(q.template.id, opt.val)}
              className={`rounded-full border px-4 py-1.5 text-sm font-semibold transition-colors ${
                currentValue === opt.val
                  ? "border-accent bg-accent text-white"
                  : dark
                    ? "border-white/30 text-white/80 hover:bg-white/10"
                    : "border-divider text-body hover:bg-tag-neutral-bg"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  // text
  return (
    <div className="space-y-2">
      <label className={labelClass}>{q.template.question}</label>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={() => { if (text !== currentValue) onSave(q.template.id, text); }}
        rows={2}
        className={`w-full max-w-xl rounded-md border px-3 py-2 text-sm ${dark ? "border-white/30 bg-white/10 text-white" : "border-divider"}`}
      />
    </div>
  );
}

export default function CaseAnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = useUnwrap(params);
  const [questions, setQuestions] = useState<AnalysisQuestionOut[]>([]);
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [chart, setChart] = useState<DentalChartOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [flowIndex, setFlowIndex] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);
  const [annotationsByImage, setAnnotationsByImage] = useState<Record<string, AnyMark[]>>({});

  const load = async () => {
    const [q, c, cd] = await Promise.all([
      api.get<AnalysisQuestionOut[]>(`/api/cases/${id}/analysis-questions`),
      api.get<DentalChartOut>(`/api/cases/${id}/dental-chart`),
      api.get<CaseDetail>(`/api/cases/${id}`),
    ]);
    setQuestions(q);
    setChart(c);
    setCaseDetail(cd);
  };

  useEffect(() => {
    load()
      .catch((e) => setError(e instanceof ApiError ? e.message : "Xatolik"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const saveAnswer = async (templateId: string, value: string | boolean) => {
    try {
      const saved = await api.put<AnalysisAnswerOut>(`/api/cases/${id}/analysis-answers/${templateId}`, { value });
      setQuestions((prev) => prev.map((q) => (q.template.id === templateId ? { ...q, answer: saved } : q)));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Saqlashda xatolik");
    }
  };

  const clickTooth = async (quadrant: number, position: number, clickType: "single" | "double") => {
    try {
      await api.post(`/api/cases/${id}/dental-chart/click`, { quadrant, position, click_type: clickType });
      const c = await api.get<DentalChartOut>(`/api/cases/${id}/dental-chart`);
      setChart(c);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Xatolik");
    }
  };

  const resetChart = async (dentition: "permanent" | "primary") => {
    try {
      const c = await api.post<DentalChartOut>(`/api/cases/${id}/dental-chart/reset?dentition=${dentition}`);
      setChart(c);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Xatolik");
    }
  };

  const imageTypeByCode = new Map((caseDetail?.image_types ?? []).map((t) => [t.code, t]));
  const imageByTypeId = new Map((caseDetail?.images ?? []).map((img) => [img.image_type_id, img]));
  const questionByKey = new Map<string, AnalysisQuestionOut>();
  for (const q of questions) {
    if (!q.template.image_type_code) continue;
    questionByKey.set(`${q.template.image_type_code}::${q.template.question}`, q);
  }

  const currentItem = WIZARD_FLOW[flowIndex];
  const currentCode = currentItem.photoCode;
  const currentType = imageTypeByCode.get(currentCode);
  const currentImage = currentType ? imageByTypeId.get(currentType.id) : null;
  const currentQuestion = questionByKey.get(`${currentCode}::${currentItem.question}`) ?? null;
  const dentalChartJaw = DENTAL_CHART_JAW_BY_CODE[currentCode];
  const currentImageId = currentImage?.id ?? null;

  useEffect(() => {
    if (!currentImageId || currentImageId in annotationsByImage) return;
    api
      .get<{ annotation_json: AnyMark[] } | null>(`/api/images/${currentImageId}/annotations`)
      .then((res) => setAnnotationsByImage((prev) => ({ ...prev, [currentImageId]: res?.annotation_json ?? [] })))
      .catch(() => setAnnotationsByImage((prev) => ({ ...prev, [currentImageId]: [] })));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentImageId]);

  const saveAnnotations = async (imageId: string, marks: AnyMark[]) => {
    setAnnotationsByImage((prev) => ({ ...prev, [imageId]: marks }));
    try {
      await api.put(`/api/images/${imageId}/annotations`, { annotation_json: marks });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Belgilarni saqlashda xatolik");
    }
  };

  if (loading || !caseDetail) {
    return (
      <Shell>
        <p className="text-muted">Yuklanmoqda...</p>
      </Shell>
    );
  }

  const isVeryFirst = flowIndex === 0;
  const isVeryLast = flowIndex === WIZARD_FLOW.length - 1;

  const goNext = () => setFlowIndex((i) => Math.min(WIZARD_FLOW.length - 1, i + 1));
  const goBack = () => setFlowIndex((i) => Math.max(0, i - 1));
  const goToPill = (code: string) => {
    const idx = WIZARD_FLOW.findIndex((item) => item.photoCode === code);
    if (idx >= 0) setFlowIndex(idx);
  };

  return (
    <Shell>
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Link href={`/cases/${id}`} className="text-sm text-muted hover:text-ink">
            ← Case&apos;ga qaytish
          </Link>
          <div>
            <h1 className="font-heading text-xl font-medium text-ink">Clinical Analysis Wizard</h1>
            <p className="text-sm text-muted">Savol {flowIndex + 1} / {WIZARD_FLOW.length}</p>
          </div>
        </div>

        {error && <div className="rounded-md bg-status-other-bg px-3 py-2 text-sm text-status-other">{error}</div>}

        <div className="flex flex-wrap gap-1.5">
          {PILL_CODES.map((code, idx) => {
            const t = imageTypeByCode.get(code);
            const hasImage = t && imageByTypeId.has(t.id);
            const isActive = code === currentCode;
            return (
              <button
                key={code}
                onClick={() => goToPill(code)}
                title={t?.label ?? code}
                className={`flex h-7 min-w-7 items-center justify-center rounded border px-1.5 text-xs font-medium ${
                  isActive
                    ? "border-accent bg-accent text-white"
                    : hasImage
                      ? "border-divider bg-surface text-body hover:bg-tag-neutral-bg"
                      : "border-dashed border-divider text-muted hover:bg-tag-neutral-bg"
                }`}
              >
                {idx + 1}
              </button>
            );
          })}
        </div>

        {!currentType ? (
          <div className="rounded-lg border border-divider bg-surface p-4">
            <p className="text-sm text-muted">
              Bu rasm turi (&quot;{currentCode}&quot;) hali sozlanmagan — migratsiya to&apos;liq qo&apos;llanilmagan bo&apos;lishi mumkin.
            </p>
          </div>
        ) : (
          <>
            <div className="space-y-1 rounded-lg border border-divider bg-surface p-4">
              <div className="flex items-center gap-2">
                <h2 className="font-medium text-ink">{currentType.label}</h2>
                <span className="rounded bg-tag-neutral-bg px-1.5 py-0.5 text-[10px] text-tag-neutral-text">{currentType.category}</span>
              </div>
              <div className="relative flex h-[58vh] w-full items-center justify-center overflow-hidden rounded bg-tag-neutral-bg">
                {currentImage && currentImage.external_url ? (
                  <>
                    <AuthenticatedImage src={currentImage.external_url} alt={currentType.label} className="h-full w-full object-contain" />
                    <button
                      type="button"
                      onClick={() => setFullscreen(true)}
                      title="To'liq ekran"
                      className="absolute top-2 right-2 flex h-8 w-8 items-center justify-center rounded-md border border-white/60 bg-black/45 text-sm text-white"
                    >
                      ⛶
                    </button>
                  </>
                ) : (
                  <span className="text-sm text-muted">Rasm hali yuklanmagan</span>
                )}
              </div>
              {!currentImage && (
                <p className="pt-1 text-sm text-muted">
                  Bu rasm hali case sahifasida yuklanmagan. Savollarga baribir javob berishingiz mumkin, lekin avval rasmni yuklashni tavsiya qilamiz.
                </p>
              )}
            </div>

            <div className="rounded-lg border border-divider bg-surface p-6">
              {currentQuestion ? (
                <QuestionField q={currentQuestion} onSave={saveAnswer} />
              ) : (
                <p className="text-sm text-muted">
                  Bu savol topilmadi (&quot;{currentItem.question}&quot;) — migratsiya to&apos;liq qo&apos;llanilmagan bo&apos;lishi mumkin.
                </p>
              )}
            </div>

            {dentalChartJaw && chart && (
              <div className="space-y-3 rounded-lg border border-divider bg-surface p-4">
                <h2 className="font-medium text-ink">Tish jadvali (FDI) — {dentalChartJaw === "upper" ? "yuqori jag'" : "pastki jag'"}</h2>
                <DentalChart chart={chart} onClick={clickTooth} onReset={resetChart} jaw={dentalChartJaw} showReset={dentalChartJaw === "upper"} />
              </div>
            )}
          </>
        )}

        <div className="flex justify-between">
          <button
            disabled={isVeryFirst}
            onClick={goBack}
            className="rounded-md border border-divider px-4 py-2 text-sm font-medium text-body hover:bg-tag-neutral-bg disabled:opacity-40"
          >
            ← Orqaga
          </button>
          {isVeryLast ? (
            <Link
              href={`/cases/${id}`}
              className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover"
            >
              Yakunlash
            </Link>
          ) : (
            <button
              onClick={goNext}
              className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover"
            >
              Keyingisi →
            </button>
          )}
        </div>
      </div>

      {fullscreen && currentType && currentImage && currentImage.external_url && (
        <div className="fixed inset-0 z-[1000] flex flex-col" style={{ background: "#12241a" }}>
          <div className="flex items-center justify-between px-4 py-2.5">
            <div className="text-xs text-white/80">
              Savol {flowIndex + 1} / {WIZARD_FLOW.length} · {currentType.label}
            </div>
            <button type="button" onClick={() => setFullscreen(false)} className="text-sm text-white hover:underline">
              Yopish ×
            </button>
          </div>

          <div className="relative min-h-0 flex-1">
            <AuthenticatedImage src={currentImage.external_url} alt={currentType.label} className="h-full w-full object-contain" />
            <div className="absolute inset-0">
              <AnnotationCanvas
                editable
                idSalt={currentImage.id}
                marks={annotationsByImage[currentImage.id] ?? []}
                onChange={(next) => saveAnnotations(currentImage.id, next)}
              />
            </div>
          </div>

          <div className="p-4 pt-3" style={{ background: "rgba(18,36,26,0.92)" }}>
            {currentQuestion ? (
              <QuestionField q={currentQuestion} onSave={saveAnswer} dark />
            ) : (
              <p className="text-sm" style={{ color: "#f5b5b5" }}>
                Bu savol topilmadi (&quot;{currentItem.question}&quot;) — migratsiya to&apos;liq qo&apos;llanilmagan bo&apos;lishi mumkin.
              </p>
            )}
            <div className="mt-3.5 flex flex-wrap items-center justify-between gap-4">
              <button
                disabled={isVeryFirst}
                onClick={goBack}
                className="shrink-0 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
              >
                ← Orqaga
              </button>
              {isVeryLast ? (
                <button onClick={() => setFullscreen(false)} className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white">
                  Yakunlash
                </button>
              ) : (
                <button onClick={goNext} className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white">
                  Keyingisi →
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </Shell>
  );
}
