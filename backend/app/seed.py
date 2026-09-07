"""Development-only demo data (spec section 38): a super admin, 3 planners,
2 doctors, 5 mock Cliniccards patients, and 10 cases spanning every status.

Run with:  PYTHONPATH=. .venv/bin/python -m app.seed

Safe to re-run: it checks for existing rows by natural key before inserting.
"""
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models.case import TreatmentPlanCase
from app.models.cliniccards import CliniccardsAppointmentCache, CliniccardsPatientCache
from app.models.enums import CaseStatus, Role
from app.models.user import User, UserRole
from app.security.passwords import hash_password


def get_or_create_user(db, *, email, full_name, telegram_id, roles, max_workload=None) -> User:
    user = db.query(User).filter(User.email == email).one_or_none()
    if user:
        return user
    user = User(
        email=email,
        hashed_password=hash_password("password123"),
        full_name=full_name,
        telegram_id=telegram_id,
        max_workload=max_workload,
    )
    db.add(user)
    db.flush()
    for role in roles:
        db.add(UserRole(user_id=user.id, role=role))
    return user


def get_or_create_patient(db, *, patient_id, full_name, birth_date, phone) -> CliniccardsPatientCache:
    row = db.query(CliniccardsPatientCache).filter(CliniccardsPatientCache.cliniccards_patient_id == patient_id).one_or_none()
    if row:
        return row
    row = CliniccardsPatientCache(
        cliniccards_patient_id=patient_id,
        full_name=full_name,
        birth_date=birth_date,
        phone=phone,
        raw_payload={"demo": True},
        synced_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    return row


def get_or_create_appointment(db, *, appointment_id, patient_id, doctor_name, scheduled_at) -> CliniccardsAppointmentCache:
    row = db.query(CliniccardsAppointmentCache).filter(CliniccardsAppointmentCache.cliniccards_appointment_id == appointment_id).one_or_none()
    if row:
        return row
    row = CliniccardsAppointmentCache(
        cliniccards_appointment_id=appointment_id,
        cliniccards_patient_id=patient_id,
        appointment_type_code="consultation_2",
        appointment_type_label="2-konsultatsiya",
        doctor_name=doctor_name,
        scheduled_at=scheduled_at,
        raw_payload={"demo": True},
        synced_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    return row


def get_or_create_case(db, *, appointment_id, patient_id, doctor, doctor_name, planner, status, consultation_at, deadline, progress) -> None:
    existing = db.query(TreatmentPlanCase).filter(TreatmentPlanCase.cliniccards_appointment_id == appointment_id).one_or_none()
    if existing:
        return
    db.add(
        TreatmentPlanCase(
            cliniccards_patient_id=patient_id,
            cliniccards_appointment_id=appointment_id,
            consultation_datetime=consultation_at,
            primary_doctor_user_id=doctor.id if doctor else None,
            primary_doctor_name=doctor_name,
            responsible_planner_user_id=planner.id if planner else None,
            status=status,
            images_progress_percent=progress,
            deadline=deadline,
        )
    )


def run() -> None:
    db = SessionLocal()
    try:
        admin = get_or_create_user(
            db, email="admin@clinic.local", full_name="Super Admin", telegram_id=None, roles=[Role.SUPER_ADMIN]
        )

        planner1 = get_or_create_user(db, email="planner1@clinic.local", full_name="Dilshod Rahimov", telegram_id=900000001, roles=[Role.PLANNER], max_workload=6)
        planner2 = get_or_create_user(db, email="planner2@clinic.local", full_name="Kamola Yusupova", telegram_id=900000002, roles=[Role.PLANNER], max_workload=6)
        planner3 = get_or_create_user(db, email="planner3@clinic.local", full_name="Bekzod Nazarov", telegram_id=900000003, roles=[Role.PLANNER], max_workload=4)

        doctor1 = get_or_create_user(db, email="doctor1@clinic.local", full_name="Dr. Aziz Karimov", telegram_id=900000011, roles=[Role.DOCTOR])
        doctor2 = get_or_create_user(db, email="doctor2@clinic.local", full_name="Dr. Nilufar Rashidova", telegram_id=900000012, roles=[Role.DOCTOR])

        patients = [
            get_or_create_patient(db, patient_id="DEMO-P1", full_name="Dilnoza Yusupova", birth_date="2005-03-12", phone="+998901234501"),
            get_or_create_patient(db, patient_id="DEMO-P2", full_name="Sardor Toshev", birth_date="1998-11-02", phone="+998901234502"),
            get_or_create_patient(db, patient_id="DEMO-P3", full_name="Madina Alieva", birth_date="2010-07-19", phone="+998901234503"),
            get_or_create_patient(db, patient_id="DEMO-P4", full_name="Jasur Nematov", birth_date="1995-01-27", phone="+998901234504"),
            get_or_create_patient(db, patient_id="DEMO-P5", full_name="Ozoda Karimova", birth_date="2003-09-08", phone="+998901234505"),
        ]

        now = datetime.now(timezone.utc)

        appts = [
            get_or_create_appointment(db, appointment_id="DEMO-A1", patient_id="DEMO-P1", doctor_name=doctor1.full_name, scheduled_at=now + timedelta(hours=6)),
            get_or_create_appointment(db, appointment_id="DEMO-A2", patient_id="DEMO-P2", doctor_name=doctor1.full_name, scheduled_at=now + timedelta(days=1)),
            get_or_create_appointment(db, appointment_id="DEMO-A3", patient_id="DEMO-P3", doctor_name=doctor2.full_name, scheduled_at=now + timedelta(days=2)),
            get_or_create_appointment(db, appointment_id="DEMO-A4", patient_id="DEMO-P4", doctor_name=doctor2.full_name, scheduled_at=now + timedelta(days=3)),
            get_or_create_appointment(db, appointment_id="DEMO-A5", patient_id="DEMO-P5", doctor_name=doctor1.full_name, scheduled_at=now + timedelta(days=4)),
            get_or_create_appointment(db, appointment_id="DEMO-A6", patient_id="DEMO-P1", doctor_name=doctor1.full_name, scheduled_at=now + timedelta(days=5)),
            get_or_create_appointment(db, appointment_id="DEMO-A7", patient_id="DEMO-P2", doctor_name=doctor2.full_name, scheduled_at=now + timedelta(days=6)),
            get_or_create_appointment(db, appointment_id="DEMO-A8", patient_id="DEMO-P3", doctor_name=doctor1.full_name, scheduled_at=now + timedelta(hours=1)),
            get_or_create_appointment(db, appointment_id="DEMO-A9", patient_id="DEMO-P4", doctor_name=doctor2.full_name, scheduled_at=now - timedelta(days=1)),
            get_or_create_appointment(db, appointment_id="DEMO-A10", patient_id="DEMO-P5", doctor_name=doctor1.full_name, scheduled_at=now - timedelta(days=3)),
        ]
        db.flush()

        cases = [
            dict(appointment_id="DEMO-A1", patient_id="DEMO-P1", doctor=doctor1, planner=None, status=CaseStatus.NEW, consultation_at=now + timedelta(hours=6), deadline=now - timedelta(hours=18), progress=0),
            dict(appointment_id="DEMO-A2", patient_id="DEMO-P2", doctor=doctor1, planner=None, status=CaseStatus.WAITING_ASSIGNMENT, consultation_at=now + timedelta(days=1), deadline=now + timedelta(hours=1), progress=0),
            dict(appointment_id="DEMO-A3", patient_id="DEMO-P3", doctor=doctor2, planner=planner1, status=CaseStatus.ASSIGNED, consultation_at=now + timedelta(days=2), deadline=now + timedelta(days=1), progress=20),
            dict(appointment_id="DEMO-A4", patient_id="DEMO-P4", doctor=doctor2, planner=planner2, status=CaseStatus.IMAGES_READY, consultation_at=now + timedelta(days=3), deadline=now + timedelta(days=2), progress=100),
            dict(appointment_id="DEMO-A5", patient_id="DEMO-P5", doctor=doctor1, planner=planner3, status=CaseStatus.ANALYSIS_IN_PROGRESS, consultation_at=now + timedelta(days=4), deadline=now + timedelta(days=3), progress=100),
            dict(appointment_id="DEMO-A6", patient_id="DEMO-P1", doctor=doctor1, planner=planner1, status=CaseStatus.PLAN_IN_PROGRESS, consultation_at=now + timedelta(days=5), deadline=now + timedelta(days=4), progress=100),
            dict(appointment_id="DEMO-A7", patient_id="DEMO-P2", doctor=doctor2, planner=planner2, status=CaseStatus.REVIEW_REQUIRED, consultation_at=now + timedelta(days=6), deadline=now + timedelta(days=5), progress=100),
            dict(appointment_id="DEMO-A8", patient_id="DEMO-P3", doctor=doctor1, planner=planner3, status=CaseStatus.READY, consultation_at=now + timedelta(hours=1), deadline=now - timedelta(hours=23), progress=100),
            dict(appointment_id="DEMO-A9", patient_id="DEMO-P4", doctor=doctor2, planner=planner1, status=CaseStatus.CONSULTATION_COMPLETED, consultation_at=now - timedelta(days=1), deadline=now - timedelta(days=2), progress=100),
            dict(appointment_id="DEMO-A10", patient_id="DEMO-P5", doctor=doctor1, planner=planner2, status=CaseStatus.OVERDUE, consultation_at=now - timedelta(days=3), deadline=now - timedelta(days=4), progress=40),
        ]

        for c in cases:
            get_or_create_case(
                db,
                appointment_id=c["appointment_id"],
                patient_id=c["patient_id"],
                doctor=c["doctor"],
                doctor_name=c["doctor"].full_name,
                planner=c["planner"],
                status=c["status"],
                consultation_at=c["consultation_at"],
                deadline=c["deadline"],
                progress=c["progress"],
            )

        db.commit()
        print("Seeded: 1 super admin, 3 planners, 2 doctors, 5 patients, 10 cases.")
        print("Login: admin@clinic.local / password123 (change this in production!)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
