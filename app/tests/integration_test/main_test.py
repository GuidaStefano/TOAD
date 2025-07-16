import time
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_analysis_flow():
    # 1. Avviare l'analisi
    payload = {
        "author": "bundler",
        "repository": "bundler",
        "end_date": "2019-05-01"
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert job_id

    # 2. Controllare lo stato fino al completamento
    timeout = 300
    start_time = time.time()
    while time.time() - start_time < timeout:
        status_response = client.get(f"/status/{job_id}")
        assert status_response.status_code == 200
        status = status_response.json()["status"]
        if status == "SUCCESS":
            break
        elif status == "FAILURE":
            pytest.fail("L'analisi è fallita")
        time.sleep(5)
    else:
        pytest.fail("Timeout in attesa del completamento dell'analisi")

    # 3. Richiedere il risultato
    result_response = client.get(f"/result/{job_id}")
    assert result_response.status_code == 200
    result = result_response.json()
    assert result
    assert result["status"] == "SUCCESS"
    assert "results" in result
