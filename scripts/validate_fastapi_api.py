import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from main import app

client = TestClient(app)


def run_validation():
    health = client.get("/api/health")
    assert health.status_code == 200, health.text
    assert health.json()["status"] == "ok"

    image_path = ROOT / "data" / "DARTIS" / "ow-0450.jpg"
    with image_path.open("rb") as image_file:
        response = client.post(
            "/api/analyze",
            files={"file": (image_path.name, image_file, "image/jpeg")},
        )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] in {"success", "phase4_failed", "no_oil_detected", "no_oil_contours", "no_origin_zone"}, payload
    assert payload["phase4"]["status"] in {"success", "failed", "not_run"}, payload
    assert isinstance(payload.get("proof_image_path"), str) or payload.get("proof_image_path") is None

    artifact_name = None
    if payload.get("proof_image_path"):
        artifact_name = payload["proof_image_path"].split("/")[-1]
    elif payload.get("trajectory", {}).get("visualization_path"):
        artifact_name = payload["trajectory"]["visualization_path"].split("/")[-1]

    if artifact_name:
        artifact_response = client.get(f"/api/artifacts/{artifact_name}")
        assert artifact_response.status_code == 200, artifact_response.text

    print("FASTAPI validation ok")
    print(payload["status"])
    print(payload["phase4"]["status"])


if __name__ == "__main__":
    run_validation()
