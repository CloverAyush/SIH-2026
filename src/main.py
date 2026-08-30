import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from src.pipeline import run_pipeline

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = PROJECT_ROOT / "generated_artifacts"
UPLOAD_DIR = PROJECT_ROOT / "staging_uploads"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Oil Spill Detection API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _safe_name(filename: str) -> str:
    cleaned = Path(filename).name
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in cleaned)


def _copy_artifact_to_api_store(source_path: str) -> str | None:
    if not source_path:
        return None
    source = Path(source_path).expanduser().resolve()
    if not source.exists() or not source.is_file():
        return None

    target_name = source.name
    target_path = ARTIFACT_DIR / target_name
    if target_path.exists():
        stem = target_path.stem
        suffix = target_path.suffix
        target_path = ARTIFACT_DIR / f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"

    shutil.copy2(source, target_path)
    return str(target_path)


def _artifact_url(request: Request, source_path: str) -> str | None:
    copied = _copy_artifact_to_api_store(source_path)
    if not copied:
        return None
    return str(request.url_for("serve_artifact", filename=Path(copied).name))


def _make_json_safe(value):
    if isinstance(value, dict):
        return {str(key): _make_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "item"):
        try:
            return _make_json_safe(value.item())
        except (TypeError, ValueError):
            pass
    if isinstance(value, Path):
        return str(value)
    return str(value)


def _rewrite_result_artifacts(result: dict, request: Request) -> dict:
    if not isinstance(result, dict):
        return result

    proof_path = result.get("proof_image_path")
    if isinstance(proof_path, str):
        result["proof_image_path"] = _artifact_url(request, proof_path)

    trajectory = result.get("trajectory")
    if isinstance(trajectory, dict):
        for key in ("netcdf_path", "visualization_path"):
            value = trajectory.get(key)
            if isinstance(value, str):
                trajectory[key] = _artifact_url(request, value)

    phase4 = result.get("phase4")
    if isinstance(phase4, dict):
        sources = phase4.get("sources")
        if isinstance(sources, dict):
            for source in sources.values():
                if isinstance(source, dict) and isinstance(source.get("path"), str):
                    source["path"] = _artifact_url(request, source["path"])

    return _make_json_safe(result)


async def _stage_uploaded_image(upload_file: UploadFile) -> Path:
    if not upload_file or not upload_file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    suffix = Path(upload_file.filename).suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a JPG, PNG, BMP, or TIFF image.",
        )

    unique_dir = UPLOAD_DIR / uuid.uuid4().hex
    unique_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = _safe_name(upload_file.filename)
    staged_path = unique_dir / safe_filename

    try:
        with staged_path.open("wb") as destination:
            shutil.copyfileobj(upload_file.file, destination)
    finally:
        upload_file.file.close()

    return staged_path


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "spill-detection-pipeline"}


@app.get("/api/artifacts/{filename}")
def serve_artifact(filename: str) -> FileResponse:
    sanitized = Path(filename).name
    if sanitized != filename or not sanitized:
        raise HTTPException(status_code=404, detail="Artifact not found.")

    artifact_root = ARTIFACT_DIR.resolve()
    candidate = (artifact_root / sanitized).resolve()
    try:
        candidate.relative_to(artifact_root)
    except ValueError:
        raise HTTPException(status_code=404, detail="Artifact not found.")

    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found.")

    return FileResponse(candidate)


@app.post("/api/analyze")
async def analyze_image(request: Request, file: UploadFile = File(...)):
    staging_path = None
    try:
        staging_path = await _stage_uploaded_image(file)
        image_name = staging_path.name
        result = run_pipeline(
            image_name=Path(file.filename).name,
            image_path=str(staging_path),
            base_dir=str(SRC_DIR),
        )
        response_payload = _rewrite_result_artifacts(result, request)
        return JSONResponse(content=response_payload)
    except FileNotFoundError as exc:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "detail": str(exc), "error_type": "validation"},
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "detail": str(exc), "error_type": "validation"},
        )
    except Exception as exc:  # pragma: no cover - defensive API response
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "detail": "Pipeline execution failed.",
                "error_type": "pipeline",
                "message": str(exc),
            },
        )
    finally:
        if staging_path is not None:
            staging_parent = staging_path.parent
            if staging_parent.exists():
                shutil.rmtree(staging_parent, ignore_errors=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
