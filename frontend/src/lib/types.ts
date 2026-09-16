export type Role = "super_admin" | "admin" | "planner" | "doctor" | "consultant";

export interface ClinicOut {
  id: string;
  name: string;
  is_active: boolean;
  is_default: boolean;
  cliniccards_branch_code: string | null;
}

export type CaseStatus =
  | "NEW"
  | "WAITING_ASSIGNMENT"
  | "ASSIGNED"
  | "IMAGES_READY"
  | "ANALYSIS_IN_PROGRESS"
  | "PLAN_IN_PROGRESS"
  | "REVIEW_REQUIRED"
  | "READY"
  | "CONSULTATION_COMPLETED"
  | "OVERDUE";

export interface UserOut {
  id: string;
  email: string;
  full_name: string;
  telegram_id: number | null;
  is_active: boolean;
  max_workload: number | null;
  roles: Role[];
  clinic: ClinicOut | null;
}

export interface CaseListItem {
  id: string;
  status: CaseStatus;
  priority: string;
  consultation_datetime: string | null;
  deadline: string | null;
  images_progress_percent: number;
  patient_name: string;
  doctor_name: string | null;
  planner_name: string | null;
  clinic_id: string | null;
  clinic_name: string | null;
  face_photo_url: string | null;
}

export interface DoctorOut {
  id: string;
  full_name: string;
}

export interface DashboardStats {
  today_consultations: number;
  new_cases: number;
  in_progress: number;
  review_pending: number;
  ready: number;
  overdue: number;
}

export interface DailyConsultationCount {
  date: string;
  count: number;
}

export interface ImageTypeOut {
  id: string;
  code: string;
  label: string;
  category: string;
  is_required: boolean;
}

export interface ClinicalImageOut {
  id: string;
  image_type_id: string | null;
  external_url: string | null;
  source: string;
}

export interface FindingOut {
  id: string;
  category: string;
  description: string;
  severity: string | null;
  is_confirmed: boolean;
  source_answer_id: string | null;
}

export interface AuditLogOut {
  action: string;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface CaseDetail {
  id: string;
  status: CaseStatus;
  priority: string;
  consultation_datetime: string | null;
  deadline: string | null;
  images_progress_percent: number;
  patient: { cliniccards_patient_id: string; full_name: string; birth_date: string | null; phone: string | null } | null;
  doctor_name: string | null;
  planner_id: string | null;
  planner_name: string | null;
  image_types: ImageTypeOut[];
  images: ClinicalImageOut[];
  pool_images: ClinicalImageOut[];
  findings: FindingOut[];
  audit_log: AuditLogOut[];
}

export interface ReminderRuleOut {
  id: string;
  name: string;
  trigger_type: string;
  offset_minutes: number | null;
  notify_roles: string[];
  is_active: boolean;
  sort_order: number;
}

export interface AssignmentConfigOut {
  mode: "manual" | "auto";
  strategy: "least_workload" | "round_robin";
}

export type AnswerType = "single_choice" | "multi_choice" | "boolean" | "text" | "measurement";

export interface AnalysisTemplateOut {
  id: string;
  image_type_id: string | null;
  image_type_code: string | null;
  category: string | null;
  question: string;
  answer_type: AnswerType;
  options: string[];
  sort_order: number;
}

export interface AnalysisAnswerOut {
  id: string;
  template_id: string;
  answer_value: { value: string | boolean | string[] } | null;
  note: string | null;
  answered_by_user_id: string | null;
  answered_at: string | null;
}

export interface AnalysisQuestionOut {
  template: AnalysisTemplateOut;
  answer: AnalysisAnswerOut | null;
}

export interface ToothStatusOut {
  quadrant: number;
  position: number;
  dentition: "permanent" | "primary" | null;
  tooth_code: string;
  notes: string | null;
}

export interface DentalChartOut {
  id: string;
  numbering_system: string;
  teeth: ToothStatusOut[];
}

export interface SyncLogOut {
  id: string;
  sync_type: string;
  status: string;
  records_seen: number;
  cases_created: number;
  error: string | null;
}
