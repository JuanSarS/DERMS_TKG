import pytest
from pydantic import ValidationError

from backend.app.contracts.upstream import QSTSInput, QSTSResult, SolveQSTS
from backend.app.integrations.opendss_ws import websocket_url


def test_valid_3_step_request():
    data = SolveQSTS(
        qsts=QSTSInput(duration_hours=0.25, step_minutes=5, load_multipliers=[0.8, 1, 1.2])
    )
    assert data.simulation_type == "qsts"
    assert len(data.qsts.load_multipliers) == 3


def test_bad_steps_and_zero_rejected():
    with pytest.raises(ValidationError):
        QSTSInput(load_multipliers=[1, 2])
    with pytest.raises(ValidationError):
        QSTSInput(load_multipliers=[0] * 48)


def test_ws_url_tls():
    assert (
        websocket_url("https://d2u0styn2zl3g5.cloudfront.net", "s")
        == "wss://d2u0styn2zl3g5.cloudfront.net/ws/simulations/s"
    )


def test_result_incomplete_or_nonconvergent_rejected():
    rows = [{"step": 1, "simulated_minutes": 0, "converged": False, "load_multiplier": 1}]
    with pytest.raises(ValidationError):
        QSTSResult(session_id="s", simulation_type="qsts", steps=rows, summary={"failed_steps": 1})
