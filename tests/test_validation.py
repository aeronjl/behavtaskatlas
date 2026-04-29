from pathlib import Path

from behavtaskatlas.models import DataRequest, VerticalSlice
from behavtaskatlas.validation import validate_repository


def test_seed_records_validate() -> None:
    root = Path(__file__).resolve().parents[1]
    report = validate_repository(root)
    assert report.ok, [f"{issue.path}: {issue.message}" for issue in report.issues]
    assert len(report.records) >= 18
    assert sum(isinstance(record, VerticalSlice) for record in report.records) == 9
    assert sum(isinstance(record, DataRequest) for record in report.records) == 1
