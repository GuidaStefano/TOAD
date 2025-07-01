from pathlib import Path
from app.tasks import prepare_job_directory


def test_prepare_job_directory_creates_files(tmp_path, monkeypatch):
    """
    Verifica che prepare_job_directory crei correttamente la cartella, input.csv e toad_stdin.txt.
    """
    # Monkeypatch la base path "csv" per scrivere in tmp_path/csv
    monkeypatch.setattr("app.tasks.Path", lambda *args: tmp_path.joinpath(*args[1:]))

    job_id = "test-job"
    author = "alice"
    repo = "sample-repo"
    end_date = "2025-07-01"

    job_dir = prepare_job_directory(job_id, author, repo, end_date)

    # Verifica la directory
    assert job_dir.exists()
    assert job_dir.name == job_id

    # Verifica input.csv
    input_csv = job_dir / "input.csv"
    assert input_csv.exists()
    content = input_csv.read_text().strip()
    assert content == f"{author},{repo},{end_date}"

    # Verifica toad_stdin.txt
    stdin_txt = job_dir / "toad_stdin.txt"
    assert stdin_txt.exists()
    lines = stdin_txt.read_text().splitlines()
    assert lines == [str(input_csv), str(job_dir), "output"]
