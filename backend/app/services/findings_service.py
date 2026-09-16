"""Auto-generates Master Problem List (Finding) rows from analysis-answer
values, per the clinic's own confirmed rule table (given directly, one
question at a time) — no clinical judgment is invented here.

A question the clinic didn't give a rule for (only "Profil turi":
Protrusion/Retrusion, which has no defined "normal" baseline at rest)
intentionally produces no finding — it's recorded as an answer only.

Every finding this file creates starts unconfirmed (`is_confirmed=False`):
a doctor still reviews it. Confirm/reject, severity and manual entries are
a later pass (tracked, not built here) — this file only keeps the
candidate list in sync with the answers as they're edited, including
removing a finding again if the answer is changed back to "normal".
"""
from dataclasses import dataclass
from typing import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisAnswer, AnalysisTemplate
from app.models.finding import Finding
from app.models.image import ImageType

_NONE_WORDS = {"", "yo'q", "yoq", "yo`q", "yo'q.", "-", "norma", "normal"}


@dataclass
class Rule:
    image_type_code: str
    question: str
    category: str
    evaluate: Callable[[object], tuple[str, str] | None]


def _choice(image_type_code: str, question: str, category: str, problem_options: dict[str, str]) -> Rule:
    def evaluate(value: object) -> tuple[str, str] | None:
        if isinstance(value, str) and value in problem_options:
            return category, problem_options[value]
        return None

    return Rule(image_type_code, question, category, evaluate)


def _text(image_type_code: str, question: str, category: str, label: str) -> Rule:
    def evaluate(value: object) -> tuple[str, str] | None:
        text = value.strip() if isinstance(value, str) else ""
        if text.lower() in _NONE_WORDS:
            return None
        return category, f"{label}: {text}"

    return Rule(image_type_code, question, category, evaluate)


RULES: list[Rule] = [
    _choice("intraoral_frontal", "Pastki jag' markaziy chizig'i", "Frontal", {
        "O'ngga siljigan": "Pastki jag' markaziy chizig'i o'ngga siljigan",
        "Chapga siljigan": "Pastki jag' markaziy chizig'i chapga siljigan",
    }),
    _choice("intraoral_frontal", "Prikus turi (old, vertikal)", "Frontal", {
        "Ochiq": "Ochiq prikus",
        "Chuqur": "Chuqur prikus",
        "Teskari": "Teskari prikus",
        "Kesishgan": "Old tishlar kesishgan prikusi",
    }),
    _choice("intraoral_frontal", "Orqa prikus", "Frontal", {
        "Kesishgan": "Orqa tishlar kesishgan prikusi",
    }),
    _choice("intraoral_right_buccal", "Angle klassi, molyar (6-tish), o'ng", "Buccal", {
        "II": "Angle II klassi (molyar, o'ng)",
        "III": "Angle III klassi (molyar, o'ng)",
    }),
    _choice("intraoral_right_buccal", "Angle klassi, klyk (3-tish), o'ng", "Buccal", {
        "II": "Angle II klassi (klyk, o'ng)",
        "III": "Angle III klassi (klyk, o'ng)",
    }),
    _choice("intraoral_left_buccal", "Angle klassi, molyar (6-tish), chap", "Buccal", {
        "II": "Angle II klassi (molyar, chap)",
        "III": "Angle III klassi (molyar, chap)",
    }),
    _choice("intraoral_left_buccal", "Angle klassi, klyk (3-tish), chap", "Buccal", {
        "II": "Angle II klassi (klyk, chap)",
        "III": "Angle III klassi (klyk, chap)",
    }),
    _choice("overjet", "Overjet holati", "Overjet", {
        "Ko'p": "Overjet ortiqcha",
        "Kam": "Overjet kam",
    }),
    _text("intraoral_upper_occlusal", "Joy yetishmasligi / qiyshiqlik darajasi", "Okklyuzion",
          "Yuqori jag'da joy yetishmasligi/qiyshiqlik"),
    _text("intraoral_lower_occlusal", "Joy yetishmasligi / qiyshiqlik darajasi", "Okklyuzion",
          "Pastki jag'da joy yetishmasligi/qiyshiqlik"),
    _choice("face_frontal", "Lablar holati", "Profil", {
        "Majburiy yopilgan": "Lablar majburiy yopilgan holatda",
    }),
    _text("face_frontal_m", "Yuqori kurak tishlarning ko'rinish darajasi", "Profil",
          "Yuqori kurak tishlar ko'rinishi (\"M\" holatida)"),
    _choice("face_frontal_smile", "Ekspozitsiya darajasi", "Tabassum", {
        "Ko'p": "Tabassumda ekspozitsiya ortiqcha",
        "Kam": "Tabassumda ekspozitsiya kam",
    }),
    _choice("face_frontal_smile", "Milk holati (gummy smile)", "Tabassum", {
        "Kam": "Yengil gummy smile",
        "Ko'p": "Ifodali gummy smile",
    }),
    _choice("face_frontal_smile", "Tepa jag' markaziy chizig'i (yuzga nisbatan)", "Tabassum", {
        "O'ngga siljigan": "Tepa jag' markaziy chizig'i o'ngga siljigan",
        "Chapga siljigan": "Tepa jag' markaziy chizig'i chapga siljigan",
    }),
    _choice("face_45_smile", "Arka (smile arc) holati", "Tabassum", {
        "Ko'p": "Smile arc me'yordan ko'p",
        "Kam": "Smile arc me'yordan kam",
    }),
    _choice("face_profile_90_rest", "Klass moyilligi", "Profil 90°", {
        "2-klassga moyillik": "Profilda II klassga moyillik (tinch holatda)",
        "3-klassga moyillik": "Profilda III klassga moyillik (tinch holatda)",
    }),
    # "Profil turi" (Protrusion/Retrusion) has no rule on purpose: the
    # clinic confirmed it has no "normal" baseline at rest, so it stays an
    # answer only, never a finding.
    _choice("face_profile_90_m", "Tishlar holati", "Profil 90°", {
        "Protrusiya": "\"M\" holatida tishlar protruziyasi (90°)",
        "Retrusiya": "\"M\" holatida tishlar retruziyasi (90°)",
    }),
    _choice("face_profile_90_smile", "Tishlar holati", "Profil 90°", {
        "Protrusiya": "Kulgan holatda tishlar protruziyasi (90°)",
        "Retrusiya": "Kulgan holatda tishlar retruziyasi (90°)",
    }),
]

_RULES_BY_KEY = {(r.image_type_code, r.question): r for r in RULES}

# The one pair the clinic wants combined into a single finding: the
# asymmetry side note is only meaningful together with the symmetry answer.
_FACE_FRONTAL_CODE = "face_frontal"
_SYMMETRY_QUESTION = "Pastki jag' holati (simmetriya)"
_SYMMETRY_SIDE_QUESTION = "Agar asimmetrik bo'lsa — tomonini yozing"


def _template_context(db: Session, template: AnalysisTemplate) -> tuple[str | None, str]:
    code = None
    if template.image_type_id:
        image_type = db.get(ImageType, template.image_type_id)
        code = image_type.code if image_type else None
    return code, template.question


def _upsert_or_clear(db: Session, case_id: UUID, source_answer_id: UUID, result: tuple[str, str] | None) -> None:
    existing = db.execute(select(Finding).where(Finding.source_answer_id == source_answer_id)).scalar_one_or_none()
    if result is None:
        if existing:
            db.delete(existing)
        return
    category, description = result
    if existing:
        existing.category = category
        existing.description = description
    else:
        db.add(Finding(case_id=case_id, category=category, description=description, source_answer_id=source_answer_id, is_confirmed=False))


def _find_answer(db: Session, case_id: UUID, image_type_code: str, question: str) -> AnalysisAnswer | None:
    template = db.execute(
        select(AnalysisTemplate)
        .join(ImageType, ImageType.id == AnalysisTemplate.image_type_id)
        .where(ImageType.code == image_type_code, AnalysisTemplate.question == question)
    ).scalar_one_or_none()
    if not template:
        return None
    return db.execute(
        select(AnalysisAnswer).where(AnalysisAnswer.case_id == case_id, AnalysisAnswer.template_id == template.id)
    ).scalar_one_or_none()


def _answer_value(answer: AnalysisAnswer | None) -> object:
    return (answer.answer_value or {}).get("value") if answer else None


def _sync_mandible_symmetry(db: Session, case_id: UUID) -> None:
    symmetry_answer = _find_answer(db, case_id, _FACE_FRONTAL_CODE, _SYMMETRY_QUESTION)
    if not symmetry_answer:
        return
    side_answer = _find_answer(db, case_id, _FACE_FRONTAL_CODE, _SYMMETRY_SIDE_QUESTION)
    symmetry_value = _answer_value(symmetry_answer)
    side_value = _answer_value(side_answer)

    if symmetry_value != "Asimmetrik":
        _upsert_or_clear(db, case_id, symmetry_answer.id, None)
        return

    description = "Pastki jag' asimmetriyasi"
    if isinstance(side_value, str) and side_value.strip():
        description += f" ({side_value.strip()})"
    _upsert_or_clear(db, case_id, symmetry_answer.id, ("Profil", description))


def sync_finding_for_answer(db: Session, case_id: UUID, template: AnalysisTemplate, answer: AnalysisAnswer) -> None:
    """Call once after every analysis-answer save — recomputes (creating,
    updating, or removing) the Finding this one answer can produce."""
    code, question = _template_context(db, template)
    if code is None:
        return

    if code == _FACE_FRONTAL_CODE and question in (_SYMMETRY_QUESTION, _SYMMETRY_SIDE_QUESTION):
        _sync_mandible_symmetry(db, case_id)
        return

    rule = _RULES_BY_KEY.get((code, question))
    if not rule:
        return

    result = rule.evaluate(_answer_value(answer))
    _upsert_or_clear(db, case_id, answer.id, result)
