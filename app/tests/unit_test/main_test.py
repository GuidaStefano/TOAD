import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# === /analyze ===

@patch("app.main.calculate_start_date", return_value="2025-06-01")
@patch("app.main.Redis")
@patch("app.main.run_analysis.apply_async")
def test_analyze_endpoint(mock_apply_async, mock_redis_cls, mock_calc_start):
    mock_task = MagicMock()
    mock_task.id = "fake-task-id"
    mock_apply_async.return_value = mock_task

    mock_redis = MagicMock()
    mock_redis_cls.return_value = mock_redis

    payload = {
        "author": "alice",
        "repository": "sample-repo",
        "end_date": "2025-07-01"
    }

    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    assert response.json() == {"job_id": "fake-task-id"}
    mock_apply_async.assert_called_once()
    mock_redis.set.assert_called_once()


# === /status/{job_id} ===

@patch("app.main.Redis")
@patch("app.main.AsyncResult")
def test_status_success(mock_async_result_cls, mock_redis_cls):
    job_id = "123"
    mock_result = MagicMock()
    mock_result.status = "SUCCESS"
    mock_result.info = {
        "author": "alice",
        "repository": "repo",
        "start_date": "2025-06-01",
        "end_date": "2025-07-01",
    }
    mock_async_result_cls.return_value = mock_result

    response = client.get(f"/status/{job_id}")
    assert response.status_code == 200
    assert response.json() == {
        "job_id": job_id,
        "status": "SUCCESS",
        "author": "alice",
        "repository": "repo",
        "start_date": "2025-06-01",
        "end_date": "2025-07-01"
    }

@patch("app.main.Redis")
@patch("app.main.AsyncResult")
def test_status_pending_with_redis_metadata(mock_async_result_cls, mock_redis_cls):
    job_id = "456"
    mock_result = MagicMock()
    mock_result.status = "PENDING"
    mock_result.info = None
    mock_async_result_cls.return_value = mock_result

    redis_mock = MagicMock()
    redis_mock.get.return_value = json.dumps({
        "meta": {
            "author": "bob",
            "repository": "test-repo",
            "start_date": "2025-06-01",
            "end_date": "2025-07-01"
        }
    })
    mock_redis_cls.return_value = redis_mock

    response = client.get(f"/status/{job_id}")
    assert response.status_code == 200
    assert response.json() == {
        "job_id": job_id,
        "status": "PENDING",
        "author": "bob",
        "repository": "test-repo",
        "start_date": "2025-06-01",
        "end_date": "2025-07-01"
    }


# === /result/{job_id} ===

@patch("app.main.AsyncResult")
def test_result_ready(mock_async_result_cls):
    job_id = "789"
    expected_result = {"status": "SUCCESS", "data": "some-result"}

    mock_result = MagicMock()
    mock_result.ready.return_value = True
    mock_result.result = expected_result
    mock_async_result_cls.return_value = mock_result

    response = client.get(f"/result/{job_id}")
    assert response.status_code == 200
    assert response.json() == expected_result


@patch("app.main.AsyncResult")
def test_result_from_log_file(mock_async_result_cls, tmp_path):
    job_id = "job-from-log"
    expected_data = {"status": "SUCCESS", "results": {"ok": True}}

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_path = logs_dir / f"{job_id}.json"

    with open(log_path, "w") as f:
        json.dump(expected_data, f)

    mock_result = MagicMock()
    mock_result.ready.return_value = False
    mock_async_result_cls.return_value = mock_result

    response = client.get(f"/result/{job_id}")
    assert response.status_code == 200
    assert response.json() == expected_data

    log_path.unlink()  # clean up


@patch("app.main.AsyncResult")
def test_result_not_found(mock_async_result_cls):
    job_id = "non-existent"

    mock_result = MagicMock()
    mock_result.ready.return_value = False
    mock_async_result_cls.return_value = mock_result

    # Assicuriamoci che il file non esista
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_path = logs_dir / f"{job_id}.json"
    if log_path.exists():
        log_path.unlink()

    response = client.get(f"/result/{job_id}")
    assert response.status_code == 404
    assert "Risultato non trovato" in response.json()["detail"]
