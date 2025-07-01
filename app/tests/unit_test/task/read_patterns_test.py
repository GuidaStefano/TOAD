import pytest
from pathlib import Path
import csv
from app.tasks import read_patterns


def test_read_patterns_file_missing(tmp_path):
    """
    Verifica che se il file output.csv non esiste venga restituita una lista vuota.
    """
    fake_path = tmp_path / "output.csv"
    result = read_patterns(fake_path)
    assert result == []


def test_read_patterns_empty_file(tmp_path):
    """
    Verifica che un file CSV esistente ma vuoto restituisca una lista vuota.
    """
    csv_path = tmp_path / "output.csv"
    csv_path.write_text("")  # Crea file vuoto
    result = read_patterns(csv_path)
    assert result == []


def test_read_patterns_valid_file_with_true_and_false(tmp_path):
    """
    Verifica la corretta interpretazione dei valori 'true'/'false' nel CSV.
    """
    csv_path = tmp_path / "output.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["IC", "CoP"])
        writer.writeheader()
        writer.writerow({"IC": "true", "CoP": "false"})

    result = read_patterns(csv_path)
    assert isinstance(result, list)
    assert any(p["name"] == "Informal Community (IC)" and p["detected"] is True for p in result)
    assert any(p["name"] == "Community of Practice (CoP)" and p["detected"] is False for p in result)


def test_read_patterns_skips_unknown_keys(tmp_path):
    """
    Verifica che vengano considerati solo i pattern presenti in PATTERN_DESCRIPTIONS.
    """
    csv_path = tmp_path / "output.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["IC", "UNKNOWN"])
        writer.writeheader()
        writer.writerow({"IC": "true", "UNKNOWN": "true"})

    result = read_patterns(csv_path)
    names = [p["name"] for p in result]
    assert "Informal Community (IC)" in names
    assert all("UNKNOWN" not in p["name"] for p in result)


def test_read_patterns_handles_read_error(monkeypatch, tmp_path):
    """
    Verifica che in caso di eccezione nella lettura venga restituita una lista vuota.
    """
    path = tmp_path / "output.csv"
    path.write_text("bad content")

    # Forza un'eccezione simulando un errore di apertura
    def bad_open(*args, **kwargs):
        raise IOError("Simulated read error")

    monkeypatch.setattr("builtins.open", bad_open)
    result = read_patterns(path)
    assert result == []
