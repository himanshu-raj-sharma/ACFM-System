import numpy as np

from acfm_net import __version__
from acfm_net.api import create_app
from acfm_net.model import FatigueModel


def test_version_is_available() -> None:
    assert __version__ == "0.1.0"


def _client(tmp_path):
    model = FatigueModel()
    model.fit(
        np.array([[0.0, 0.0, 0.8], [1.0, 1.0, 0.2]] * 5),
        np.array(["alert", "fatigued"] * 5),
    )
    model_path = tmp_path / "test-model.joblib"
    model.save(model_path)
    return create_app(str(model_path)).test_client()


def test_health_endpoint(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_analyze_requires_an_image(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.post("/api/analyze", json={})

    assert response.status_code == 400
    assert "image" in response.json["error"]
