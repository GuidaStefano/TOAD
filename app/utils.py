from datetime import datetime, timedelta

# Calcola la start_date sottraendo 90 giorni alla end_date
def calculate_start_date(end_date_str: str) -> str:
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    start_date = end_date - timedelta(days=90)
    return start_date.strftime("%Y-%m-%d")
