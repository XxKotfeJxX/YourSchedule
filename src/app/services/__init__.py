"""Services layer package."""

from app.services.auth_service import AuthService
from app.services.greedy_scheduler import (
    CoverageDashboard,
    CoverageReason,
    FeasibilityIssue,
    FeasibilityReport,
    GreedySchedulerService,
    RequirementCoverageItem,
    ScheduleEntryCrudItem,
    ScheduleRunResult,
    ScheduleScenarioSummary,
    SchedulingDiagnostic,
    ScenarioComparison,
    ScenarioDiffItem,
)
from app.services.schedule_visualization import (
    ScheduleVisualizationService,
    WeeklyGridRow,
    WeeklyScheduleGrid,
)
from app.services.schedule_validator import (
    ScheduleValidatorService,
    ValidationIssue,
    ValidationReport,
)
from app.services.time_block_generator import TimeBlockGeneratorService
from app.services.avatar_storage import AvatarStorageService
from app.services.empty_day_template_service import EmptyDayTemplateService
from app.services.template_service import TemplateService
from app.services.template_models import (
    DayTemplateOverview,
    DayTemplatePreview,
    MarkTypeOverview,
    TemplatesOverview,
    WeekTemplateOverview,
    WeekTemplatePreview,
)

__all__ = [
    "AuthService",
    "TimeBlockGeneratorService",
    "GreedySchedulerService",
    "ScheduleRunResult",
    "SchedulingDiagnostic",
    "CoverageDashboard",
    "CoverageReason",
    "RequirementCoverageItem",
    "ScheduleEntryCrudItem",
    "FeasibilityIssue",
    "FeasibilityReport",
    "ScheduleScenarioSummary",
    "ScenarioComparison",
    "ScenarioDiffItem",
    "ScheduleVisualizationService",
    "WeeklyGridRow",
    "WeeklyScheduleGrid",
    "ScheduleValidatorService",
    "ValidationIssue",
    "ValidationReport",
    "AvatarStorageService",
    "EmptyDayTemplateService",
    "TemplateService",
    "TemplatesOverview",
    "MarkTypeOverview",
    "DayTemplateOverview",
    "DayTemplatePreview",
    "WeekTemplateOverview",
    "WeekTemplatePreview",
]
