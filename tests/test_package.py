import numpy as np
import pytest

from acfm_net import __version__
from acfm_net.api import create_app
from acfm_net.features import FrameFeatures
from acfm_net.model import FatigueModel
from acfm_net.temporal import aggregate
from acfm_net.training import read_dataset


def test_version_is_available() -> None:
    assert __version__ == "0.1.0"


def _client(tmp_path):
    model = FatigueModel()
    model.fit(
        np.array([[0.0] * 6, [1.0] * 6] * 5),
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


def test_dataset_requires_subject_ids(tmp_path) -> None:
    dataset = tmp_path / "features.csv"
    dataset.write_text(
        "eye_closure_rate,longest_eye_closure,mouth_opening_rate,"
        "mouth_opening_peak,brightness_mean,brightness_std,label\n"
        "0,0,0,0,1,0,alert\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="subject_id"):
        read_dataset(dataset)


def test_model_rejects_wrong_feature_count(tmp_path) -> None:
    model = FatigueModel()
    artifact = tmp_path / "model.joblib"
    model.fit(
        np.array([[0.0] * 6, [1.0] * 6] * 5),
        np.array(["alert", "fatigued"] * 5),
    )
    model.save(artifact)

    with pytest.raises(ValueError, match="six feature"):
        FatigueModel.load(str(artifact)).predict(np.array([0.0, 0.0]))


def test_temporal_features_capture_longest_closed_run() -> None:
    frames = [
        FrameFeatures(True, 0.0, 0.0, 0.5),
        FrameFeatures(True, 1.0, 0.6, 0.6),
        FrameFeatures(True, 1.0, 0.8, 0.7),
        FrameFeatures(True, 0.0, 0.0, 0.8),
    ]

    features = aggregate(frames)

    assert features.eye_closure_rate == 0.5
    assert features.longest_eye_closure == 0.5
    assert features.mouth_opening_rate == 0.5
    assert features.mouth_opening_peak == pytest.approx(0.8)
