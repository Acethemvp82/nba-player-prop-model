from csv_export import safe_spreadsheet_cell


def test_csv_export_escapes_formula_like_provider_text():
    for text in ("=1+1", "+SUM(A1:A2)", "-2+3", "@SUM(A1)", "  =cmd", "\t=cmd", "\r=cmd"):
        assert safe_spreadsheet_cell(text) == "'" + text


def test_csv_export_preserves_safe_text_numbers_and_missing_data():
    for value in ("Boston Celtics", "NYK", "Player One", "", 0, 24.5, None):
        assert safe_spreadsheet_cell(value) == value
