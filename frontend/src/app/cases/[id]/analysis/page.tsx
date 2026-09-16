"use client";

import { useEffect, useState, use as useUnwrap } from "react";
import Link from "next/link";
import { Shell } from "@/components/shell";
import { DentalChart } from "@/components/dental-chart";
import { api, ApiError } from "@/lib/api";
import type { AnalysisQuestionOut, DentalChartOut } from "@/lib/types";

const CATEGORY_LABELS: Record<string, string> = {
  intraoral: "Og'iz ichi",
  extraoral: "Yuz / Profil",
  radiology: "Rentgen",
};

function groupQuestions(questions: AnalysisQuestionOut[]) {
  const byCategory = new Map<string, Map<string, AnalysisQuestionOut[]>>();
  for (const q of questions) {
    const cat = q.template.category ?? "boshqa";
    const sub = q.template.image_type_code ?? "umumiy";
    if (!byCategory.has(cat)) byCategory.set(cat, new Map());
    const subMap = byCategory.get(cat)!;
    if (!subMap.has(sub)) subMap.set(sub, []);
    subMap.get(sub)!.push(q);
  }
  return byCategory;
}

function QuestionField({ q, onSave }: { q: AnalysisQuestionOut; onSave: (templateId: string, value: string | boolean) => void }) {
  const currentValue = q.answer?.answer_value?.value ?? null;
  const [text, setText] = useState(typeof currentValue === "string" && q.template.answer_type === "text" ? currentValue : "");

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
        onBlur={() => onSave(q.template.id, text)}
        rows={2}
        className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
      />
    </div>
  );
}

export default function CaseAnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = useUnwrap(params);
  const [questions, setQuestions] = useState<AnalysisQuestionOut[]>([]);
  const [chart, setChart] = useState<DentalChartOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    const [q, c] = await Promise.all([
      api.get<AnalysisQuestionOut[]>(`/api/cases/${id}/analysis-questions`),
      api.get<DentalChartOut>(`/api/cases/${id}/dental-chart`),
    ]);
    setQuestions(q);
    setChart(c);
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

  if (loading) {
    return (
      <Shell>
        <p className="text-gray-500">Yuklanmoqda...</p>
      </Shell>
    );
  }

  const grouped = groupQuestions(questions);
  const categoryOrder = ["intraoral", "extraoral", "radiology"];

  return (
    <Shell>
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Link href={`/cases/${id}`} className="text-gray-500 hover:text-gray-700">
            ← Case&apos;ga qaytish
          </Link>
          <h1 className="text-2xl font-bold">Klinik tahlil</h1>
        </div>

        {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}

        <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
          <h2 className="font-semibold">Tish jadvali (okklyuzion)</h2>
          {chart && <DentalChart chart={chart} onClick={clickTooth} onReset={resetChart} />}
        </div>

        {categoryOrder
          .filter((cat) => grouped.has(cat))
          .map((cat) => (
            <div key={cat} className="rounded-lg border border-gray-200 bg-white p-4 space-y-5">
              <h2 className="font-semibold">{CATEGORY_LABELS[cat] ?? cat}</h2>
              {Array.from(grouped.get(cat)!.entries()).map(([sub, qs]) => (
                <div key={sub} className="space-y-3 border-t border-gray-100 pt-3 first:border-0 first:pt-0">
                  {qs
                    .sort((a, b) => a.template.sort_order - b.template.sort_order)
                    .map((q) => (
                      <QuestionField key={q.template.id} q={q} onSave={saveAnswer} />
                    ))}
                </div>
              ))}
            </div>
          ))}
      </div>
    </Shell>
  );
}
