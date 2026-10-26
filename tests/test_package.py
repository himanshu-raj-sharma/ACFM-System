from base64 import b64encode

import cv2
import numpy as np
import pytest

from acfm_net import __version__
from acfm_net.api import create_app
from acfm_net.artifact import ensure_model
from acfm_net.dataset_report import summarize_manifest
from acfm_net.edge_impulse import convert_labels
from acfm_net.features import FaceFeatureExtractor, FrameFeatures
from acfm_net.labeling import create_template
from acfm_net.model import FatigueModel
from acfm_net.prepare_dataset import prepare_dataset
from acfm_net.review_export import create_review_page
from acfm_net.service import MonitoringService
from acfm_net.temporal import aggregate
from acfm_net.training import evaluate, read_dataset, train


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
    assert response.json["model_loaded"] is True
    assert response.json["privacy"]["frames_persisted"] is False
    assert response.headers["Cache-Control"] == "no-store"


def test_production_app_serves_frontend_assets(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.get("/")

    assert response.status_code == 200
    assert b"ACFM-Net" in response.data


def test_analyze_requires_an_image(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/api/analyze",
        json={"consent": True},
        headers={"Origin": "http://127.0.0.1:3000"},
    )

    assert response.status_code == 400
    assert "image" in response.json["error"]


def test_analyze_requires_consent(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/api/analyze",
        json={"images": ["not-used"]},
        headers={"Origin": "http://127.0.0.1:3000"},
    )

    assert response.status_code == 400
    assert "consent" in response.json["error"]


def test_analyze_rejects_unknown_origin(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/api/analyze",
        json={"consent": True, "images": ["not-used"]},
        headers={"Origin": "https://untrusted.example"},
    )

    assert response.status_code == 403


def test_analyze_preflight_allows_configured_origin(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.options(
        "/api/analyze",
        headers={"Origin": "http://127.0.0.1:3000"},
    )

    assert response.status_code == 204
    assert response.headers["Access-Control-Allow-Origin"] == ("http://127.0.0.1:3000")


def test_analyze_rejects_non_object_json(tmp_path) -> None:
    client = _client(tmp_path)

    response = client.post(
        "/api/analyze",
        json=["not-an-object"],
        headers={"Origin": "http://127.0.0.1:3000"},
    )

    assert response.status_code == 400
    assert "JSON object" in response.json["error"]


def test_analyze_rejects_a_window_without_a_face(tmp_path) -> None:
    client = _client(tmp_path)
    image = np.zeros((120, 160, 3), dtype=np.uint8)
    success, encoded = cv2.imencode(".jpg", image)
    assert success
    frame = "data:image/jpeg;base64," + b64encode(encoded).decode("ascii")

    response = client.post(
        "/api/analyze",
        json={"consent": True, "images": [frame] * 12},
        headers={"Origin": "http://127.0.0.1:3000"},
    )

    assert response.status_code == 400
    assert "face" in response.json["error"]


def test_analyze_accepts_a_valid_frame_window(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        FaceFeatureExtractor,
        "extract",
        lambda _self, _image: FrameFeatures(True, 0.0, 0.0, 0.5),
    )
    client = _client(tmp_path)
    image = np.zeros((120, 160, 3), dtype=np.uint8)
    success, encoded = cv2.imencode(".jpg", image)
    assert success
    frame = "data:image/jpeg;base64," + b64encode(encoded).decode("ascii")

    response = client.post(
        "/api/analyze",
        json={"consent": True, "images": [frame] * 12},
        headers={"Origin": "http://127.0.0.1:3000"},
    )

    assert response.status_code == 200
    assert response.json["frames_analyzed"] == 12
    assert response.json["features"]["face_detection_rate"] == 1.0
    assert "prediction" in response.json


def test_dataset_requires_subject_ids(tmp_path) -> None:
    dataset = tmp_path / "features.csv"
    dataset.write_text(
        "eye_closure_rate,longest_eye_closure,mouth_opening_rate,"
        "mouth_opening_peak,brightness_mean,brightness_std,"
        "face_detection_rate,label\n"
        "0,0,0,0,1,0,1,alert\n",
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


def test_model_artifact_hash_is_verified(tmp_path, monkeypatch) -> None:
    import hashlib

    artifact = tmp_path / "model.joblib"
    artifact.write_bytes(b"trusted model")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    monkeypatch.setenv("ACFM_MODEL_SHA256", digest)

    ensure_model(str(artifact))

    monkeypatch.setenv("ACFM_MODEL_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="does not match"):
        ensure_model(str(artifact))


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
    assert features.face_detection_rate == 1.0


def test_face_extractor_marks_a_blank_frame_as_missing() -> None:
    features = FaceFeatureExtractor().extract(np.zeros((240, 320, 3), dtype=np.uint8))

    assert features.face_detected is False
    assert features.eye_closure == 0.0


def test_decode_image_rejects_excessive_dimensions() -> None:
    image = np.zeros((1, 5000, 3), dtype=np.uint8)
    success, encoded = cv2.imencode(".jpg", image)
    assert success

    with pytest.raises(ValueError, match="dimensions"):
        MonitoringService._decode_image(b64encode(encoded).decode("ascii"))


def test_evaluation_keeps_subjects_in_separate_folds() -> None:
    features = np.array(
        [[0.0] * 6, [1.0] * 6] * 10,
        dtype=np.float32,
    )
    labels = np.array(["alert", "fatigued"] * 10)
    groups = np.repeat(list("abcdefghij"), 2)

    report = evaluate(features, labels, groups, folds=5)

    assert len(report["folds"]) == 5
    assert report["confusion_matrix"] == [[10, 0], [0, 10]]


def test_training_metadata_contains_dataset_and_model_hashes(tmp_path) -> None:
    dataset = tmp_path / "features.csv"
    header = (
        "eye_closure_rate,longest_eye_closure,mouth_opening_rate,"
        "mouth_opening_peak,brightness_mean,brightness_std,"
        "face_detection_rate,label,subject_id\n"
    )
    rows = []
    for index in range(10):
        label = "alert" if index < 5 else "fatigued"
        value = "0" if label == "alert" else "1"
        rows.append(f"{value},{value},{value},{value},{value},0,1,{label},s{index}\n")
    dataset.write_text(header + "".join(rows), encoding="utf-8")
    artifact = tmp_path / "model.joblib"
    metadata = tmp_path / "model.metadata.json"

    report = train(dataset, artifact, metadata, folds=5)

    assert len(report["dataset_sha256"]) == 64
    assert len(report["model_sha256"]) == 64
    assert report["quality_column"] == "face_detection_rate"


def test_edge_impulse_manifest_preserves_labels_and_split(tmp_path) -> None:
    images = tmp_path / "images"
    images.mkdir()
    image = images / "training" / "frame_001_alice.jpg"
    image.parent.mkdir()
    image.write_bytes(b"image")
    labels = tmp_path / "info.labels"
    labels.write_text(
        '{"version": 1, "files": [{"path": '
        '"training/frame_001_alice.jpg.ingestion-abc.jpg", '
        '"name": "frame_001_alice.jpg", "category": "training", '
        '"boundingBoxes": [{"label": "mata_terbuka"}, '
        '{"label": "menguap"}]}]}',
        encoding="utf-8",
    )
    output = tmp_path / "manifest.csv"
    metadata = tmp_path / "manifest.json"

    assert convert_labels(labels, images, output, metadata) == 1
    row = output.read_text(encoding="utf-8").splitlines()[1].split(",")
    assert row[2] == "training"
    assert row[3] == "alice"
    assert row[4:8] == ["1", "0", "0", "1"]
    assert "not direct alert/fatigued ground truth" in metadata.read_text(
        encoding="utf-8",
    )


def test_dataset_report_counts_annotation_prevalence(tmp_path) -> None:
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "split,subject_id,open_eye_count,closed_eye_count,"
        "not_yawning_count,yawning_count\n"
        "training,alice,2,0,1,0\n"
        "testing,bob,1,1,0,1\n",
        encoding="utf-8",
    )

    report = summarize_manifest(manifest)

    assert report["rows"] == 2
    assert report["splits"] == {"training": 1, "testing": 1}
    assert report["subjects"] == ["alice", "bob"]
    assert report["annotation_counts"]["menguap"] == 1
    assert report["image_prevalence"]["has_closed_eye"] == 0.5


def test_prepare_dataset_creates_fixed_labeled_windows(tmp_path) -> None:
    images = tmp_path / "images"
    source = images / "training"
    source.mkdir(parents=True)
    rows = []
    for index in range(12):
        filename = f"frame_{index:04d}_alice.jpg"
        (source / filename).write_bytes(b"image")
        rows.append(
            f"training/{filename},training/{filename},training,alice,alert,\n",
        )
    labels = tmp_path / "labels.csv"
    labels.write_text(
        "image_path,source_path,split,subject_id,label,label_notes\n" + "".join(rows),
        encoding="utf-8",
    )
    output = tmp_path / "raw"

    assert prepare_dataset(labels, images, output) == 1
    assert len(list(output.glob("alert/alice/*/*.jpg"))) == 12


def test_labeling_template_has_blank_direct_labels(tmp_path) -> None:
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "image_path,source_path,split,subject_id\n"
        "training/a.jpg,training/a.jpg,training,alice\n",
        encoding="utf-8",
    )
    output = tmp_path / "labels.csv"

    assert create_template(manifest, output) == 1
    assert output.read_text(encoding="utf-8").splitlines() == [
        "image_path,source_path,split,subject_id,label,label_notes",
        "training/a.jpg,training/a.jpg,training,alice,,",
    ]


def test_review_export_creates_local_page_and_csv(tmp_path) -> None:
    images = tmp_path / "images"
    images.mkdir()
    (images / "a.jpg").write_bytes(b"image")
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "image_path,source_path,split,subject_id,open_eye_count,"
        "closed_eye_count,not_yawning_count,yawning_count\n"
        "a.jpg,a.jpg,training,alice,1,0,1,0\n",
        encoding="utf-8",
    )
    output = tmp_path / "review"

    assert create_review_page(manifest, images, output) == 1
    assert (output / "index.html").exists()
    assert "image_path,source_path,split,subject_id,label,label_notes" in (
        output / "alertness_labels.csv"
    ).read_text(encoding="utf-8")
