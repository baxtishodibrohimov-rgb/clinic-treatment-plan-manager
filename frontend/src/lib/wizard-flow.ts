// The full wizard walk-through, one question per item, in the exact order
// the clinic wants. Almost all items follow "photo N's questions in a
// row," but the midline pair is special: the clinic wants the upper-jaw
// midline judged against the face (asked on the frontal-smile photo)
// immediately followed by the lower-jaw midline judged intraorally — so
// after the smile photo's other questions, the wizard jumps back to the
// intraoral-frontal photo for one more question before moving on to 45°
// smile. `photoCode` matches image_types.code; `question` must match the
// exact analysis_templates.question text (see the alembic seed).
//
// Shared by the analysis wizard (src/app/cases/[id]/analysis) and the
// presentation slide deck (src/app/cases/[id]/present) so both walk the
// exact same 22-step order and 13-photo pill list.
export const WIZARD_FLOW: { photoCode: string; question: string }[] = [
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
export const PILL_CODES = [
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
export const DENTAL_CHART_JAW_BY_CODE: Record<string, "upper" | "lower"> = {
  intraoral_upper_occlusal: "upper",
  intraoral_lower_occlusal: "lower",
};
