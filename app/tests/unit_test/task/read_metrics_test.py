import json
from pathlib import Path
from app.tasks import read_metrics


def test_read_metrics_file_not_exists(tmp_path):
    """
    Verifica che venga restituito un errore se il file metrics.json non esiste.
    """
    metrics_path = tmp_path / "metrics.json"
    result = read_metrics(metrics_path)
    assert result == {"error": "metrics.json non trovato"}


def test_read_metrics_invalid_json(tmp_path):
    """
    Verifica che un file metrics.json non valido restituisca un errore esplicativo.
    """
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text("not-a-valid-json")
    result = read_metrics(metrics_path)
    assert "error" in result
    assert "Errore lettura metrics.json" in result["error"]


def test_read_metrics_empty_sections(tmp_path):
    """
    Verifica che un file JSON valido ma senza sezioni specifiche restituisca dizionari vuoti.
    """
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(json.dumps({}))  # JSON vuoto

    result = read_metrics(metrics_path)
    assert "dispersion" in result
    assert result["dispersion"] == {}
    assert result["longevity"]["longevity"]["value"] is None  # Longevity chiave mancante = None


def test_read_metrics_complete_file(tmp_path):
    """
    Verifica che un file metrics.json completo venga correttamente letto e mappato.
    """
    data = {
        "dispersion": {
            "geo_distance_variance": 42.5,
            "avg_geo_distance": 100.0
        },
        "engagement": {
            "m_comment_per_pr": 3.1
        },
        "formality": {
            "milestones": 5
        },
        "longevity": 300,
        "structure": {
            "repo_connections": 1
        }
    }

    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(json.dumps(data))

    result = read_metrics(metrics_path)

    assert result["dispersion"]["geo_distance_variance"]["value"] == 42.5
    assert "description" in result["dispersion"]["geo_distance_variance"]
    assert result["engagement"]["m_comment_per_pr"]["value"] == 3.1
    assert result["formality"]["milestones"]["value"] == 5
    assert result["longevity"]
