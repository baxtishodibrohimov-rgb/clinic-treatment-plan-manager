"use client";

import { useEffect, useState, use as useUnwrap } from "react";
import Link from "next/link";
import { Shell } from "@/components/shell";
import { DentalChart } from "@/components/dental-chart";
import { AuthenticatedImage } from "@/components/authenticated-image";
import { api, ApiError } from "@/lib/api";
import type { AnalysisQuestionOut, CaseDetail, DentalChartOut } from "@/lib/types";

// The clinic's confirmed photo-capture order for the wizard — one image per
// step, in exactly this sequence. Anything not in this list (X-rays,
// leftover face_profile_right/left/3-4 view/face_profile_smile) isn't part
// of this flow.
const WIZARD_ORDER = [
  "intraoral_frontal",
  "intraoral_right_buccal",
  "intraoral_left_buccal",
  "overjet",
  "intraoral_upper_occlusal",
  "intraoral_lower_occlusal",
  "face_frontal",
  "face_frontal_m",
  "face_frontal_smile",
  "face_45_smile",
  "face_profile_90_rest",
  "face_profile_90_m",
  "face_profile_90_smile",
];

// The dental chart is one shared object per case, not a per-photo
// question — the upper/lower occlusal steps each show their own jaw's
// half of it (see dental-chart.tsx for click mechanics).
const DENTAL_CHART_JAW_BY_CODE: Record<string, "upper" | "lower"> = {
  intraoral_upper_occlusal: "upper",
  intraoral_lower_occlusal: "lower",
};

function QuestionField({ q, onSave }: { q: AnalysisQuestionOut; onSave: (templateId: string, value: string | boolean) => void }) {
  const currentValue = q.answer?.answer_value?.value ?? null;
  const [text, setText] = useState(typeof currentValue === "string" && q.template.answer_type === "text" ? currentValue : "");
  useEffect(() => {
    setText(typeof currentValue === "string" && q.template.answer_type === "text" ? currentValue : "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q.template.id, currentValue]);

  if (q.template.answer_type === "single_choice") {
    return (
      <div className="space-y-1.5">
        <label className="block text-sm font-medium text-gray-700">{q.template.question}</label>
        <div className="flex flex-wrap gap-1.5">
          {q.template.options.map((opt) => (
            <button
              key={opt}
              onClick={() => onSave(q.template.id, opt)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                currentValue === opt ? "border-blue-500 bg-blue-50 text-blue-700" : "border-gray-300 text-gray-600 hover:bg-gray-50"
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
      <div className="space-y-1.5">
        <label className="block text-sm font-medium text-gray-700">{q.template.question}</label>
        <div className="flex gap-1.5">
          {[
            { label: "Ha", val: true },
            { label: "Yo'q", val: false },
          ].map((opt) => (
            <button
              key={opt.label}
              onClick={() => onSave(q.template.id, opt.val)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                currentValue === opt.val ? "border-blue-500 bg-blue-50 text-blue-700" : "border-gray-300 text-gray-600 hover:bg-gray-50"
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
    <div className="space-y-1.5">
      <label className="block text-sm font-medium text-gray-700">{q.template.question}</label>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={() => { if (text !== currentValue) onSave(q.template.id, text); }}
        rows={2}
        className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
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
  const [stepIndex, setStepIndex] = useState(0);

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
      await api.put(`/api/cases/${id}/analysis-answers/${templateId}`, { value });
      setQuestions((prev) =>
        prev.map((q) =>
          q.template.id === templateId
            ? { ...q, answer: { template_id: templateId, answer_value: { value }, note: null, answered_by_user_id: null, answered_at: new Date().toISOString() } }
            : q
        )
      );
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

  if (loading || !caseDetail) {
    return (
      <Shell>
        <p className="text-gray-500">Yuklanmoqda...</p>
      </Shell>
    );
  }

  const imageTypeByCode = new Map(caseDetail.image_types.map((t) => [t.code, t]));
  const imageByTypeId = new Map(caseDetail.images.map((img) => [img.image_type_id, img]));
  const questionsByTypeCode = new Map<string, AnalysisQuestionOut[]>();
  for (const q of questions) {
    const code = q.template.image_type_code;
    if (!code) continue;
    if (!questionsByTypeCode.has(code)) questionsByTypeCode.set(code, []);
    questionsByTypeCode.get(code)!.push(q);
  }

  const currentCode = WIZARD_ORDER[stepIndex];
  const currentType = imageTypeByCode.get(currentCode);
  const currentImage = currentType ? imageByTypeId.get(currentType.id) : null;
  const currentQuestions = (questionsByTypeCode.get(currentCode) ?? []).sort((a, b) => a.template.sort_order - b.template.sort_order);
  const isFirst = stepIndex === 0;
  const isLast = stepIndex === WIZARD_ORDER.length - 1;
  const dentalChartJaw = DENTAL_CHART_JAW_BY_CODE[currentCode];

  return (
    <Shell>
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Link href={`/cases/${id}`} className="text-gray-500 hover:text-gray-700">
            ← Case&apos;ga qaytish
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Clinical Analysis Wizard</h1>
            <p className="text-sm text-gray-500">Bosqich {stepIndex + 1} / {WIZARD_ORDER.length}</p>
          </div>
        </div>

        {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

        <div className="flex flex-wrap gap-1.5">
          {WIZARD_ORDER.map((code, idx) => {
            const t = imageTypeByCode.get(code);
            const hasImage = t && imageByTypeId.has(t.id);
            return (
              <button
                key={code}
                onClick={() => setStepIndex(idx)}
                title={t?.label ?? code}
                className={`flex h-7 min-w-7 items-center justify-center rounded border px-1.5 text-xs font-medium ${
                  idx === stepIndex
                    ? "border-blue-600 bg-blue-600 text-white"
                    : hasImage
                      ? "border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
                      : "border-dashed border-gray-300 text-gray-400 hover:bg-gray-50"
                }`}
              >
                {idx + 1}
              </button>
            );
          })}
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="mb-3 flex items-center gap-2">
            <h2 className="font-semibold">{currentType?.label ?? currentCode}</h2>
            {currentType && (
              <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600">{currentType.category}</span>
            )}
          </div>

          {!currentType ? (
            <p className="text-sm text-gray-500">
              Bu rasm turi (&quot;{currentCode}&quot;) hali sozlanmagan — migratsiya to&apos;liq qo&apos;llanilmagan bo&apos;lishi mumkin.
            </p>
          ) : (
            <div className="grid gap-4 md:grid-cols-[280px_1fr]">
              <div className="flex aspect-square items-center justify-center overflow-hidden rounded bg-gray-100">
                {currentImage && currentImage.external_url ? (
                  <AuthenticatedImage src={currentImage.external_url} alt={currentType.label} className="h-full w-full object-contain" />
                ) : (
                  <span className="text-xs text-gray-400">Rasm hali yuklanmagan</span>
                )}
              </div>
              <div className="space-y-4">
                {!currentImage && (
                  <p className="text-sm text-gray-500">
                    Bu rasm hali case sahifasida yuklanmagan. Savollarga baribir javob berishingiz mumkin, lekin avval rasmni yuklashni tavsiya qilamiz.
                  </p>
                )}
                {currentQuestions.length === 0 ? (
                  <p className="text-sm text-gray-500">Bu rasm uchun savol kiritilmagan.</p>
                ) : (
                  currentQuestions.map((q) => <QuestionField key={q.template.id} q={q} onSave={saveAnswer} />)
                )}
              </div>
            </div>
          )}
        </div>

        {dentalChartJaw && chart && (
          <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
            <h2 className="font-semibold">Tish jadvali (FDI) — {dentalChartJaw === "upper" ? "yuqori jag'" : "pastki jag'"}</h2>
            <DentalChart chart={chart} onClick={clickTooth} onReset={resetChart} jaw={dentalChartJaw} showReset={dentalChartJaw === "upper"} />
          </div>
        )}

        <div className="flex justify-between">
          <button
            disabled={isFirst}
            onClick={() => setStepIndex((i) => Math.max(0, i - 1))}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium disabled:opacity-40 hover:bg-gray-50"
          >
            ← Orqaga
          </button>
          {isLast ? (
            <Link
              href={`/cases/${id}`}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Yakunlash
            </Link>
          ) : (
            <button
              onClick={() => setStepIndex((i) => Math.min(WIZARD_ORDER.length - 1, i + 1))}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Keyingisi →
            </button>
          )}
        </div>
      </div>
    </Shell>
  );
}
