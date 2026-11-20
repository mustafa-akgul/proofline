import pytest

from proofline import synth
from proofline.audit import AuditLog
from proofline.clock import DeterministicClock
from proofline.contracts import RiskEvent
from proofline.investigation import Investigation


@pytest.fixture(scope="session")
def db_path(tmp_path_factory):
    path = tmp_path_factory.mktemp("data") / "synthetic.db"
    synth.generate(str(path))
    return str(path)


@pytest.fixture
def risk():
    r = synth.example_risk_event()
    return RiskEvent(**{**r, "detection_evidence": tuple(r["detection_evidence"]),
                        "source_refs": tuple(r["source_refs"])})


@pytest.fixture
def clock():
    return DeterministicClock()


@pytest.fixture
def audit(tmp_path, clock):
    return AuditLog(str(tmp_path / "audit.db"), clock)


@pytest.fixture
def inv(db_path, audit, clock):
    return Investigation(db_path, audit, clock)
