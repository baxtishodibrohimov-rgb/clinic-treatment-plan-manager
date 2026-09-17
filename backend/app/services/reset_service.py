"""Danger-zone: wipes every patient/case record so the clinic can start
over and re-pull everything from Cliniccards, while leaving configuration
(staff/users, clinics, image types, the analysis questionnaire, reminder
rules, app settings) untouched.

TRUNCATE ... CASCADE on these four "root" tables is enough — every other
patient-data table (clinical_images, analysis_answers, findings,
dental_charts, treatment plans/reviews, notifications, presentations,
audit_log) has an ON DELETE CASCADE foreign key back to cases, and CASCADE
here also follows cliniccards_appointments -> cliniccards_patients."""
from sqlalchemy import text
from sqlalchemy.orm import Session

RESET_CONFIRM_PHRASE = "HAMMASINI TOZALA"

_TABLES = "cases, cliniccards_appointments, cliniccards_patients, integration_sync_log"


def reset_patient_data(db: Session) -> None:
    db.execute(text(f"TRUNCATE TABLE {_TABLES} CASCADE"))
