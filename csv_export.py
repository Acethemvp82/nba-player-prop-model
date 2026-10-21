"""Safe spreadsheet export of unconfirmed NBA research rows.

Prevent spreadsheet formula interpretation of untrusted provider strings.
Numeric values and missing observations remain unchanged.
"""


def safe_spreadsheet_cell(value):
    if not isinstance(value, str):
        return value
    # Strip only for detection: preserve original content in the escaped cell.
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value
