"use client";

import { useEffect, useState, use as useUnwrap } from "react";
import Link from "next/link";
import { Shell } from "@/components/shell";
import { DentalChart } from "@/components/dental-chart";
import { AuthenticatedImage } from "@/components/authenticated-image";
import { api, ApiError } from "@/lib/api";
import type { AnalysisQuestionOut, CaseDetail, DentalChartOut } from "@/lib/types";

// The full wizard walk-through, one question per item, in the exact order
// the clinic wants. Almost all items follow "photo N's questions in a
// row," but the midline pair is special: the clinic wants the upper-jaw
// midline judged against the face (asked on the frontal-smile photo)
// immediately followed by the lower-jaw midline judged intraorally — so
// after the smile photo's other questions, the wizard jumps back to the
// intraoral-frontal photo for one more question before moving on to 45°
// smile. `photoCode` matches image_types.code; `question` must match the
// exact analysis_templates.question text (see the alembic seed).
const WIZARD_FLOW: { photoCode: string; question: string }[] = [
  { photoCode: "intraoral_frontal", question: "Prikus turi (old, vertikal)" },
  { photoCode: "intraoral_frontal", question: "Orqa prikus" },
  { photoCode: "intraoral_right_buccal", question: "Angle klassi, molyar (6-tish), o'ng" },
  { photoCode: "intraoral_right_buccal", question: "Angle klassi, klyk (3-tish), o'ng" },
  { photoCode: "intraoral_left_buccal", question: "Angle klassi, molyar (6-tish), chap" },
  { photoCode: "intraoral_left_buccal", question: "Angle klassi, klyk (3-tish), chap" },
  { photoCode: "overjet", question: "Overjet holati" },
  { photoCode: "intraoral_upper_occlusal", question: "Joy yetishmasligi / qiyshiqlik darajasi" },
  { photoCode: "intraoral_lower_occlusal", question: "Joy yetishmasligi / qiyshiqlik darajasi" },
  { photoCode: "face_frontal", question: "Lablar holati" },
  { photoCode: "face_frontal", question: "Pastki jag' holati (simmetriya)" },
  { photoCode: "face_frontal", question: "Agar asimmetrik bo'lsa — tomonini yozing" },
  { photoCode: "face_frontal_m", question: "Yuqori kurak tishlarning ko'rinish darajasi" },
  { photoCode: "face_frontal_smile", question: "Ekspozitsiya darajasi" },
  { photoCode: "face_frontal_smile", question: "Milk holati (gummy smile)" },
  { photoCode: "face_frontal_smile", question: "Tepa jag' markaziy chizig'i (yuzga nisbatan)" },
  { photoCode: "intraoral_frontal", question: "Pastki jag' markaziy chizig'i" },
  { photoCode: "face_45_smile", question: "Arka (smile arc) holati" },
  { photoCode: "face_profile_90_rest", question: "Profil turi" },
  { photoCode: "face_profile_90_rest", question: "Klass moyilligi" },
  { photoCode: "face_profile_90_m", question: "Tishlar holati" },
  { photoCode: "face_profile_90_smile", question: "Tishlar holati" },
];

// Numbered pills still represent the 13 photos in their natural order —
// each jumps to that photo's FIRST question in WIZARD_FLOW (so pill 1
// lands on "Prikus turi", not the later midline jump-back that also uses
// the intraoral-frontal photo).
const PILL_CODES = [
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
      <div className="space-y-2">
        <label className="block text-base font-medium text-gray-800">{q.template.question}</label>
        <div className="flex flex-wrap gap-2">
          {q.template.options.map((opt) => (
            <button
              key={opt}
              onClick={() => onSave(q.template.id, opt)}
              className={`rounded-full border px-4 py-1.5 text-sm font-medium transition-colors ${
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
      <div className="space-y-2">
        <label className="block text-base font-medium text-gray-800">{q.template.question}</label>
        <div className="flex gap-2">
          {[
            { label: "Ha", val: true },
            { label: "Yo'q", val: false },
          ].map((opt) => (
            <button
              key={opt.label}
              onClick={() => onSave(q.template.id, opt.val)}
              className={`rounded-full border px-4 py-1.5 text-sm font-medium transition-colors ${
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
    <div className="space-y-2">
      <label className="block text-base font-medium text-gray-800">{q.template.question}</label>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={() => { if (text !== currentValue) onSave(q.template.id, text); }}
        rows={2}
        className="w-full max-w-xl rounded-md border border-gray-300 px-3 py-2 text-sm"
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
          <Link href={`/cases/${id}`} className="text-gray-500 hover:text-gray-700">
            ← Case&apos;ga qaytish
          </Link>
          <div>
            <h1 className="text-2xl font-bold">Clinical Analysis Wizard</h1>
            <p className="text-sm text-gray-500">Savol {flowIndex + 1} / {WIZARD_FLOW.length}</p>
          </div>
        </div>

        {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

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

        {!currentType ? (
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="text-sm text-gray-500">
              Bu rasm turi (&quot;{currentCode}&quot;) hali sozlanmagan — migratsiya to&apos;liq qo&apos;llanilmagan bo&apos;lishi mumkin.
            </p>
          </div>
        ) : (
          <>
            <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-1">
              <div className="flex items-center gap-2">
                <h2 className="font-semibold">{currentType.label}</h2>
                <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600">{currentType.category}</span>
              </div>
              <div className="flex h-[58vh] w-full items-center justify-center overflow-hidden rounded bg-gray-100">
                {currentImage && currentImage.external_url ? (
                  <AuthenticatedImage src={currentImage.external_url} alt={currentType.label} className="h-full w-full object-contain" />
                ) : (
                  <span className="text-sm text-gray-400">Rasm hali yuklanmagan</span>
                )}
              </div>
              {!currentImage && (
                <p className="pt-1 text-sm text-gray-500">
                  Bu rasm hali case sahifasida yuklanmagan. Savollarga baribir javob berishingiz mumkin, lekin avval rasmni yuklashni tavsiya qilamiz.
                </p>
              )}
            </div>

            <div className="rounded-lg border border-gray-200 bg-white p-6">
              {currentQuestion ? (
                <QuestionField q={currentQuestion} onSave={saveAnswer} />
              ) : (
                <p className="text-sm text-gray-500">
                  Bu savol topilmadi (&quot;{currentItem.question}&quot;) — migratsiya to&apos;liq qo&apos;llanilmagan bo&apos;lishi mumkin.
                </p>
              )}
            </div>

            {dentalChartJaw && chart && (
              <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
                <h2 className="font-semibold">Tish jadvali (FDI) — {dentalChartJaw === "upper" ? "yuqori jag'" : "pastki jag'"}</h2>
                <DentalChart chart={chart} onClick={clickTooth} onReset={resetChart} jaw={dentalChartJaw} showReset={dentalChartJaw === "upper"} />
              </div>
            )}
          </>
        )}

        <div className="flex justify-between">
          <button
            disabled={isVeryFirst}
            onClick={goBack}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium disabled:opacity-40 hover:bg-gray-50"
          >
            ← Orqaga
          </button>
          {isVeryLast ? (
            <Link
              href={`/cases/${id}`}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Yakunlash
            </Link>
          ) : (
            <button
              onClick={goNext}
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
