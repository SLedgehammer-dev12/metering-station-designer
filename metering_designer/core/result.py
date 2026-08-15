"""Standard result envelope for all calculation functions."""
import datetime
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Result:
    data: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provenance: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    @classmethod
    def from_value(cls, key: str, value: Any) -> "Result":
        return cls(data={key: value})

    def merge(self, other: "Result") -> "Result":
        return Result(
            data={**self.data, **other.data},
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            provenance=self.provenance + other.provenance,
        )

    def add_provenance(
        self,
        function_name: str,
        parameters: dict | None = None,
        standard_ref: str = "",
        timestamp: str | None = None,
    ) -> None:
        self.provenance.append({
            "function": function_name,
            "parameters": parameters or {},
            "standard_ref": standard_ref,
            "timestamp": timestamp or datetime.datetime.now().isoformat(),
        })
