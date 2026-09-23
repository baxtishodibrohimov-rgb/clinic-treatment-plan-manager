"use client";

import { useEffect, useState, use as useUnwrap } from "react";
import Link from "next/link";
import { Shell } from "@/components/shell";
import { AuthenticatedImage } from "@/components/authenticated-image";
import { AnnotationCanvas } from "@/components/annotation-canvas";
import { api, ApiError } from "@/lib/api";
import { COLOR_HEX, splitMarks } from "@/lib/annotations";
import { PILL_CODES, WIZARD_FLOW } from "@/lib/wizard-flow";
import { containBox, fetchImageForExport, hexNoHash } from "@/lib/pptx-export";
import type { AnalysisQuestionOut, AnyMark, Arrow, CaseDetail, ClinicalImageOut, ImageTypeOut, Mark } from "@/lib/types";

interface RowDef {
  idx: number;
  question: string;
  answer: string;
}
type SlideDef =
  | { kind: "title" }
  | { kind: "photo"; code: string; rows: RowDef[]; marks: Mark[]; arrows: Arrow[] };

function fmt(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("uz-UZ", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function PresentationPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = useUnwrap(params);
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [questions, setQuestions] = useState<AnalysisQuestionOut[]>([]);
  const [annotationsByImage, setAnnotationsByImage] = useState<Record<string, AnyMark[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSlide, setActiveSlide] = useState(0);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [cd, qs] = await Promise.all([
          api.get<CaseDetail>(`/api/cases/${id}`),
          api.get<AnalysisQuestionOut[]>(`/api/cases/${id}/analysis-questions`),
        ]);
        setCaseDetail(cd);
        setQuestions(qs);

        const imageTypeByCode = new Map(cd.image_types.map((t) => [t.code, t]));
        const imageByTypeId = new Map(cd.images.map((img) => [img.image_type_id, img]));
        const ids = new Set<string>();
        for (const code of PILL_CODES) {
          const t = imageTypeByCode.get(code);
          const img = t ? imageByTypeId.get(t.id) : null;
          if (img) ids.add(img.id);
        }
        const faceType = cd.image_types.find((t) => t.code === "face_frontal");
        const faceImg = faceType ? imageByTypeId.get(faceType.id) : null;
        if (faceImg) ids.add(faceImg.id);

        const idList = Array.from(ids);
        const results = await Promise.all(
          idList.map((imgId) =>
            api.get<{ annotation_json: AnyMark[] } | null>(`/api/images/${imgId}/annotations`).catch(() => null),
          ),
        );
        const map: Record<string, AnyMark[]> = {};
        idList.forEach((imgId, i) => {
          map[imgId] = results[i]?.annotation_json ?? [];
        });
        setAnnotationsByImage(map);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Xatolik");
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  if (loading || !caseDetail) {
    return (
      <Shell>
        <p className="text-muted">Yuklanmoqda...</p>
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
  const faceType = caseDetail.image_types.find((t) => t.code === "face_frontal");
  const faceImg = faceType ? imageByTypeId.get(faceType.id) : null;

  const rowsForCode = (code: string): RowDef[] => {
    const rows: RowDef[] = [];
    WIZARD_FLOW.forEach((step, idx) => {
      if (step.photoCode !== code) return;
      const q = questionByKey.get(`${code}::${step.question}`);
      if (!q || !q.answer || q.answer.answer_value === null || q.answer.answer_value === undefined) return;
      const val = q.answer.answer_value.value;
      const answer = typeof val === "boolean" ? (val ? "Ha" : "Yo'q") : Array.isArray(val) ? val.join(", ") : String(val).trim();
      if (!answer) return;
      rows.push({ idx, question: step.question, answer });
    });
    return rows;
  };

  const slideDefs: SlideDef[] = [{ kind: "title" }];
  for (const code of PILL_CODES) {
    const rows = rowsForCode(code);
    slideDefs.push({ kind: "photo", code, rows, marks: [], arrows: [] });
    const t = imageTypeByCode.get(code);
    const img = t ? imageByTypeId.get(t.id) : null;
    const marks = img ? annotationsByImage[img.id] ?? [] : [];
    const { marks: drawnMarks, arrows } = splitMarks(marks);
    if (drawnMarks.length > 0 || arrows.length > 0) {
      slideDefs.push({ kind: "photo", code, rows, marks: drawnMarks, arrows });
    }
  }
  const activeIdx = Math.min(activeSlide, slideDefs.length - 1);
  const activeDef = slideDefs[activeIdx];

  const exportPptx = async () => {
    setExporting(true);
    setExportError(null);
    try {
      const mod = await import("pptxgenjs");
      const PptxGenJS = mod.default;
      const pres = new PptxGenJS();
      pres.layout = "LAYOUT_WIDE"; // 13.33in x 7.5in, 16:9 — matches the deck's black-slide format
      const W = 13.333;
      const H = 7.5;

      for (const def of slideDefs) {
        const slide = pres.addSlide();
        slide.background = { color: "000000" };

        if (def.kind === "title") {
          slide.addText(caseDetail.patient?.full_name ?? "Bemor", {
            x: 0.5, y: 0.5, w: 7.5, h: 1, color: "FFFFFF", fontSize: 32, fontFace: "Arial",
          });
          const lines = [
            `Birinchi qabul kuni: ${fmt(caseDetail.consultation_datetime)}`,
            `Tug'ilgan sana: ${caseDetail.patient?.birth_date ?? "—"}`,
            `Tel no: ${caseDetail.patient?.phone ?? "—"}`,
            `Doktor: ${caseDetail.doctor_name ?? "—"}`,
          ];
          slide.addText(
            lines.map((text) => ({ text, options: { bullet: true, breakLine: true, paraSpaceAfter: 10 } })),
            { x: 0.5, y: 1.9, w: 7, h: 3, color: "FFFFFF", fontSize: 18, fontFace: "Arial" },
          );
          if (faceImg?.external_url) {
            try {
              const fetched = await fetchImageForExport(faceImg.external_url);
              slide.addImage({ data: fetched.dataUrl, x: 8.5, y: 0, w: W - 8.5, h: H, sizing: { type: "cover", w: W - 8.5, h: H } });
            } catch {
              // photo unavailable — title slide still ships with the text
            }
          }
          continue;
        }

        const t = imageTypeByCode.get(def.code);
        const img = t ? imageByTypeId.get(t.id) : null;
        const tableH = def.rows.length > 0 ? 0.5 + def.rows.length * 0.45 : 0;
        const photoBox = { x: 0, y: 0, w: W, h: H - tableH };

        if (img?.external_url) {
          try {
            const fetched = await fetchImageForExport(img.external_url);
            const box = containBox(fetched.width, fetched.height, photoBox);
            slide.addImage({ data: fetched.dataUrl, x: box.x, y: box.y, w: box.w, h: box.h });

            for (const mark of def.marks) {
              const mx = box.x + (Math.min(mark.x1, mark.x2) / 100) * box.w;
              const my = box.y + (Math.min(mark.y1, mark.y2) / 100) * box.h;
              const mw = Math.max(0.05, (Math.abs(mark.x2 - mark.x1) / 100) * box.w);
              const mh = Math.max(0.05, (Math.abs(mark.y2 - mark.y1) / 100) * box.h);
              slide.addShape(mark.shape === "rect" ? pres.ShapeType.rect : pres.ShapeType.ellipse, {
                x: mx, y: my, w: mw, h: mh,
                fill: { type: "none" },
                line: { color: hexNoHash(COLOR_HEX[mark.color]), width: mark.width },
              });
            }
            for (const a of def.arrows) {
              const ax1 = box.x + (a.x1 / 100) * box.w;
              const ay1 = box.y + (a.y1 / 100) * box.h;
              const ax2 = box.x + (a.x2 / 100) * box.w;
              const ay2 = box.y + (a.y2 / 100) * box.h;
              slide.addShape(pres.ShapeType.line, {
                x: Math.min(ax1, ax2), y: Math.min(ay1, ay2),
                w: Math.max(0.02, Math.abs(ax2 - ax1)), h: Math.max(0.02, Math.abs(ay2 - ay1)),
                flipH: ax2 < ax1, flipV: ay2 < ay1,
                line: { color: hexNoHash(COLOR_HEX[a.color]), width: a.width, endArrowType: a.shape === "arrow" ? "triangle" : "none" },
              });
            }
          } catch {
            slide.addText("Rasmni yuklab bo'lmadi", { x: 0, y: 0, w: W, h: photoBox.h, color: "888888", fontSize: 18, align: "center", valign: "middle" });
          }
        } else {
          slide.addText("Rasm yuklanmagan", { x: 0, y: 0, w: W, h: photoBox.h, color: "888888", fontSize: 18, align: "center", valign: "middle" });
        }

        if (def.rows.length > 0) {
          const tableRows = def.rows.map((r) => [
            {
              text: `${r.question}: ${r.answer}`,
              options: { fill: { color: "168A4A" }, color: "FFFFFF", bold: true, margin: 0.12 },
            },
          ]);
          slide.addTable(tableRows, {
            x: 0.25,
            y: H - tableH + 0.12,
            w: W - 0.5,
            h: Math.max(0.3, tableH - 0.24),
            fontSize: 13,
            border: { type: "solid", color: "168A4A", pt: 1 },
          });
        }
      }

      const safeName = (caseDetail.patient?.full_name ?? "bemor").replace(/[^\w\- ]/g, "").trim() || "bemor";
      await pres.writeFile({ fileName: `${safeName} — prezentatsiya.pptx` });
    } catch (e) {
      setExportError(e instanceof Error ? e.message : "PPTX tayyorlashda xatolik");
    } finally {
      setExporting(false);
    }
  };

  return (
    <Shell>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link href={`/cases/${id}`} className="text-sm text-muted hover:text-ink">
            ← Case&apos;ga qaytish
          </Link>
          <div className="min-w-0 flex-1 text-center">
            <div className="truncate text-sm font-medium text-ink">{caseDetail.patient?.full_name ?? "Bemor"}</div>
          </div>
          <button
            type="button"
            onClick={exportPptx}
            disabled={exporting}
            className="shrink-0 rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50"
          >
            {exporting ? "Tayyorlanmoqda..." : "PPTX yuklab olish"}
          </button>
        </div>

        {error && <div className="rounded-md bg-status-other-bg px-3 py-2 text-sm text-status-other">{error}</div>}
        {exportError && <div className="rounded-md bg-status-other-bg px-3 py-2 text-sm text-status-other">{exportError}</div>}

        <div className="flex flex-wrap gap-1.5">
          {slideDefs.map((_, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setActiveSlide(i)}
              className={`flex h-7 min-w-7 items-center justify-center rounded border px-1.5 text-xs font-medium ${
                i === activeIdx ? "border-accent bg-accent text-white" : "border-divider bg-surface text-body hover:bg-tag-neutral-bg"
              }`}
            >
              {i + 1}
            </button>
          ))}
        </div>

        <div className="mx-auto w-full max-w-5xl overflow-hidden rounded-lg" style={{ background: "#000000", aspectRatio: "16/9" }}>
          <SlidePanel def={activeDef} caseDetail={caseDetail} faceImg={faceImg ?? null} imageTypeByCode={imageTypeByCode} imageByTypeId={imageByTypeId} />
        </div>

        <div className="flex items-center justify-center gap-3">
          <button
            type="button"
            disabled={activeIdx === 0}
            onClick={() => setActiveSlide((i) => Math.max(0, i - 1))}
            className="rounded-md border border-divider px-3 py-1.5 text-sm text-body hover:bg-tag-neutral-bg disabled:opacity-40"
          >
            ← Oldingi
          </button>
          <span className="text-sm text-muted">
            {activeIdx + 1} / {slideDefs.length}
          </span>
          <button
            type="button"
            disabled={activeIdx === slideDefs.length - 1}
            onClick={() => setActiveSlide((i) => Math.min(slideDefs.length - 1, i + 1))}
            className="rounded-md border border-divider px-3 py-1.5 text-sm text-body hover:bg-tag-neutral-bg disabled:opacity-40"
          >
            Keyingi →
          </button>
        </div>
      </div>
    </Shell>
  );
}

function SlidePanel({
  def,
  caseDetail,
  faceImg,
  imageTypeByCode,
  imageByTypeId,
}: {
  def: SlideDef;
  caseDetail: CaseDetail;
  faceImg: ClinicalImageOut | null;
  imageTypeByCode: Map<string, ImageTypeOut>;
  imageByTypeId: Map<string | null, ClinicalImageOut>;
}) {
  if (def.kind === "title") {
    return (
      <div className="grid h-full grid-cols-[1fr_320px]">
        <div className="flex flex-col justify-center gap-4 p-8 text-white">
          <div className="font-heading text-2xl">{caseDetail.patient?.full_name ?? "Bemor"}</div>
          <ul className="list-disc space-y-2 pl-5 text-sm">
            <li>
              <b>Birinchi qabul kuni:</b> {fmt(caseDetail.consultation_datetime)}
            </li>
            <li>
              <b>Tug&apos;ilgan sana:</b> {caseDetail.patient?.birth_date ?? "—"}
            </li>
            <li>
              <b>Tel no:</b> {caseDetail.patient?.phone ?? "—"}
            </li>
            <li>
              <b>Doktor:</b> {caseDetail.doctor_name ?? "—"}
            </li>
          </ul>
        </div>
        <div className="h-full w-full bg-black">
          {faceImg?.external_url && <AuthenticatedImage src={faceImg.external_url} alt="Bemor rasmi" className="h-full w-full object-cover" />}
        </div>
      </div>
    );
  }

  const t = imageTypeByCode.get(def.code);
  const img = t ? imageByTypeId.get(t.id) : null;
  const hasOverlay = def.marks.length > 0 || def.arrows.length > 0;

  return (
    <div className="flex h-full flex-col">
      <div className="relative min-h-0 flex-1 bg-black">
        {img?.external_url ? (
          <>
            <AuthenticatedImage src={img.external_url} alt={t?.label ?? def.code} className="h-full w-full object-contain" />
            {hasOverlay && (
              <div className="absolute inset-0">
                <AnnotationCanvas idSalt={`pres-${def.code}`} marks={[...def.marks, ...def.arrows]} />
              </div>
            )}
          </>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-white/50">Rasm yuklanmagan</div>
        )}
      </div>
      {def.rows.length > 0 && (
        <div className="flex flex-wrap gap-2 bg-black px-3 py-2.5">
          {def.rows.map((r) => (
            <div key={r.idx} className="rounded-md bg-[#168a4a] px-3 py-1.5 text-sm font-semibold text-white shadow-sm">
              {r.question}: {r.answer}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
