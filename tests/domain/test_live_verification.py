from datetime import date, datetime

from guanbi_automation.domain.live_verification import canonicalize_publish_cell


def test_canonicalize_datetime_to_iso_date():
    value = canonicalize_publish_cell(datetime(2026, 3, 9, 0, 0, 0))

    assert value == "2026-03-09"


def test_canonicalize_datetime_with_time_component():
    value = canonicalize_publish_cell(datetime(2026, 3, 9, 14, 30, 15))

    assert value == "2026-03-09 14:30:15"


def test_canonicalize_date_to_iso_string():
    value = canonicalize_publish_cell(date(2026, 3, 9))

    assert value == "2026-03-09"


def test_canonicalize_none_to_empty_string():
    value = canonicalize_publish_cell(None)

    assert value == ""


def test_canonicalize_numeric_values_without_stringifying():
    assert canonicalize_publish_cell(12) == 12
    assert canonicalize_publish_cell(12.5) == 12.5
