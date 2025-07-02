import shutil
from pathlib import Path
from app.tasks import clean_up


def test_clean_up_removes_all_paths():
    """
    Verifica che clean_up rimuova tutte le cartelle e file previsti nelle path reali (non tmp_path).
    """
    job_id = "job-123"
    author = "bob"
    repo = "demo"

    # Path reali (hardcoded, come nel codice)
    paths = [
        Path("csv") / job_id,
        Path("data") / author / repo,
        Path("graphs") / author / repo,
        Path("repositories") / f"{author}.{repo}"
    ]

    # Crea le cartelle con un file dummy
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
        (path / "dummy.txt").write_text("test")

    # Verifica che esistano prima della pulizia
    for path in paths:
        assert path.exists()

    # Chiama la funzione reale
    clean_up(job_id, author, repo)

    # Verifica che siano state rimosse
    for path in paths:
        assert not path.exists()