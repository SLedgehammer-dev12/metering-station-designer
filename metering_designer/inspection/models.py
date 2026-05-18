from dataclasses import dataclass, field
from typing import Optional


@dataclass
class InspectionPoint:
    position_label: str
    measured: Optional[float] = None
    nominal: float = 0.0
    tol_lower: Optional[float] = None
    tol_upper: Optional[float] = None

    @property
    def status(self) -> str:
        if self.measured is None:
            return "PENDING"
        if self.tol_lower is not None and self.measured < self.tol_lower:
            return "FAIL"
        if self.tol_upper is not None and self.measured > self.tol_upper:
            return "FAIL"
        return "PASS"


@dataclass
class InspectionParameter:
    key: str
    label: str
    unit: str
    points: list[InspectionPoint] = field(default_factory=list)
    tolerance_spec: dict = field(default_factory=dict)
    standard_clause: str = ""
    criticality: str = "MINOR"
    uncertainty_factor: float = 0.0
    options: list[dict] = field(default_factory=list)
    qualitative_value: Optional[str] = None

    @property
    def is_qualitative(self) -> bool:
        return self.unit == "qualitative"

    @property
    def overall_status(self) -> str:
        if self.is_qualitative:
            if self.qualitative_value is None:
                return "PENDING"
            for opt in self.options:
                if opt["value"] == self.qualitative_value:
                    return opt.get("status", "PENDING")
            return "FAIL"
        statuses = [p.status for p in self.points if p.measured is not None]
        if not statuses:
            return "PENDING"
        if any(s == "FAIL" for s in statuses):
            return "FAIL"
        if self.criticality == "CRITICAL" and any(s == "FAIL" for s in statuses):
            return "FAIL"
        return "PASS"


@dataclass
class ComponentInspection:
    component_name: str
    standard: str
    parameters: list[InspectionParameter] = field(default_factory=list)

    @property
    def all_statuses(self) -> list[str]:
        return [p.overall_status for p in self.parameters]

    @property
    def passed_count(self) -> int:
        return sum(1 for s in self.all_statuses if s == "PASS")

    @property
    def failed_count(self) -> int:
        return sum(1 for s in self.all_statuses if s == "FAIL")

    @property
    def critical_failures(self) -> list[InspectionParameter]:
        return [p for p in self.parameters if p.criticality == "CRITICAL" and p.overall_status == "FAIL"]

    @property
    def component_status(self) -> str:
        if any(s == "PENDING" for s in self.all_statuses):
            return "PENDING"
        if self.critical_failures:
            return "FAIL"
        if self.failed_count > 0:
            return "CONDITIONAL"
        return "PASS"


@dataclass
class InspectionReport:
    meter_type: str
    conditioner_type: Optional[str]
    nps: int
    beta: Optional[float]
    D_mm: float
    components: list[ComponentInspection] = field(default_factory=list)

    @property
    def all_inspections(self) -> list[InspectionParameter]:
        return [p for c in self.components for p in c.parameters]

    @property
    def total_params(self) -> int:
        return len(self.all_inspections)

    @property
    def passed_params(self) -> int:
        return sum(1 for p in self.all_inspections if p.overall_status == "PASS")

    @property
    def failed_params(self) -> int:
        return sum(1 for p in self.all_inspections if p.overall_status == "FAIL")

    @property
    def conditional_params(self) -> int:
        return sum(1 for p in self.all_inspections if p.overall_status == "CONDITIONAL")

    @property
    def pass_rate(self) -> float:
        total = self.total_params
        if total == 0:
            return 0
        return self.passed_params / total * 100

    @property
    def overall_status(self) -> str:
        if self.passed_params + self.failed_params + self.conditional_params == 0:
            return "PENDING"
        critical_fails = [c for comp in self.components for c in comp.critical_failures]
        if critical_fails:
            return f"FAIL — {len(critical_fails)} Critical hata"
        if self.failed_params > 0:
            return f"CONDITIONAL — {self.failed_params} Major/Minor non-conformance"
        if self.conditional_params > 0:
            return "CONDITIONAL — Kabul edilebilir sapmalar var"
        return "PASS — Tam uyumlu"

    def get_failed_parameters(self) -> list[InspectionParameter]:
        return [p for p in self.all_inspections if p.overall_status == "FAIL"]

    def get_critical_failures(self) -> list[InspectionParameter]:
        return [p for comp in self.components for p in comp.critical_failures if p.overall_status == "FAIL"]
