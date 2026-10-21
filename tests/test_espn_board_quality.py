from espn_board_quality import history_sample_status


def test_history_status_no_verified_data():
    assert history_sample_status(None, None, None) == "No verified history"
    assert history_sample_status(0, 0, 0) == "No verified history"


def test_history_status_describes_sample_size_not_betting_confidence():
    assert history_sample_status(3, 3, 3) == "Limited verified history"
    assert history_sample_status(7, 5, 7) == "5–9 verified games"
    assert history_sample_status(10, 5, 10) == "10+ verified games"


def test_history_status_rejects_inconsistent_counts():
    assert history_sample_status(3, 5, 3) == "Invalid history metadata"
    assert history_sample_status(5, 4, 3) == "Invalid history metadata"
    assert history_sample_status(True, 1, 1) == "Invalid history metadata"
    assert history_sample_status(-1, 0, 0) == "Invalid history metadata"


def test_history_status_treats_dataframe_nan_as_missing():
    nan = float("nan")
    assert history_sample_status(nan, nan, nan) == "No verified history"
    assert history_sample_status(3, nan, nan) == "Limited verified history"
