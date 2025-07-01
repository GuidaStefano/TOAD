import pytest
from app.utils import calculate_start_date

# Verifica che venga calcolata correttamente la data 3 mesi prima di una data valida
def test_valid_date():
    result = calculate_start_date("2024-07-01")
    assert result == "2024-04-02"
