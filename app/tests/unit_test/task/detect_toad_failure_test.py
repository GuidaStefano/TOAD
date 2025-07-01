import pytest
from app.tasks import detect_toad_failure

def test_detect_known_toad_error():
    """
    Verifica che un messaggio di errore noto venga correttamente rilevato.
    """
    output = "There must be at least 100 commits in the repository."
    result = detect_toad_failure(output)
    assert result == "Invalid Repository: There must be at least 100 commits!"


def test_detect_known_toad_error_case_insensitive():
    """
    Verifica che il matching degli errori noti sia case-insensitive.
    """
    output = "there must be at least 2 MEMBERS in the repository"
    result = detect_toad_failure(output)
    assert result == "Invalid Repository: Not enough members (min. 2)!"


def test_detect_unknown_error_returns_none():
    """
    Verifica che un output senza errori noti restituisca None.
    """
    output = "Analysis completed successfully with 3 patterns found."
    result = detect_toad_failure(output)
    assert result is None


def test_detect_partial_match_does_not_trigger():
    """
    Verifica che una stringa parzialmente simile a un errore noto non venga rilevata erroneamente.
    """
    output = "There must be at least some data in the repository."
    result = detect_toad_failure(output)
    assert result is None