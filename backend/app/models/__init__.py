"""Import every model module so Base.metadata is complete for Alembic
autogenerate and for `Base.metadata.create_all()` in tests."""
from app.models.analysis import AnalysisAnswer, AnalysisTemplate, ImageAnnotation  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.case import ALLOWED_TRANSITIONS, TreatmentPlanCase  # noqa: F401
from app.models.cliniccards import CliniccardsAppointmentCache, CliniccardsPatientCache  # noqa: F401
from app.models.dental import DentalChart, ToothStatus  # noqa: F401
from app.models.finding import Finding  # noqa: F401
from app.models.image import ClinicalImage, ImageType  # noqa: F401
from app.models.notification import Notification, ReminderRule, ReminderSentLog  # noqa: F401
from app.models.presentation import Presentation  # noqa: F401
from app.models.settings import AppSetting, AssignmentConfig  # noqa: F401
from app.models.sync_log import IntegrationSyncLog  # noqa: F401
from app.models.treatment_plan import (  # noqa: F401
    Review,
    TreatmentObjective,
    TreatmentPlan,
    TreatmentPlanVersion,
    TreatmentProblem,
)
from app.models.user import User, UserRole  # noqa: F401
