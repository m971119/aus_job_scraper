from datetime import date, timedelta
from unittest.mock import patch
from scraper import parse_location, parse_listing_date, build_seek_url


def test_parse_listing_date_days_ago():
    fixed = date(2026, 5, 24)
    with patch("scraper.date") as mock_date:
        mock_date.today.return_value = fixed
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        assert parse_listing_date("3d ago") == "2026-05-21"


def test_parse_listing_date_with_expiring_suffix():
    fixed = date(2026, 5, 24)
    with patch("scraper.date") as mock_date:
        mock_date.today.return_value = fixed
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        assert parse_listing_date("12d ago•Expiring") == "2026-05-12"


def test_parse_listing_date_featured_falls_back_to_today():
    fixed = date(2026, 5, 24)
    with patch("scraper.date") as mock_date:
        mock_date.today.return_value = fixed
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        assert parse_listing_date("Featured") == "2026-05-24"


def test_build_seek_url_contains_seek_domain():
    url = build_seek_url("python developer", "Melbourne VIC", page=1)
    assert "seek.com.au" in url


def test_build_seek_url_contains_keywords():
    url = build_seek_url("python developer", "Melbourne VIC", page=1)
    assert "python" in url.lower() or "keywords" in url.lower()


def test_build_seek_url_sorts_by_listed_date():
    url = build_seek_url("python developer", "Melbourne VIC", page=1)
    assert "sortmode=ListedDate" in url


def test_parse_location_extracts_state():
    result = parse_location("CBD Melbourne VIC 3000")
    assert result["state"] == "VIC"


def test_parse_location_empty_string():
    result = parse_location("")
    assert result["state"] is None
    assert result["city"] is None
    assert result["suburb"] is None


def test_parse_location_nsw():
    result = parse_location("Sydney CBD NSW 2000")
    assert result["state"] == "NSW"


def test_parse_location_city_suburb():
    result = parse_location("CBD Melbourne VIC 3000")
    assert result["suburb"] == "CBD"
    assert result["city"] == "Melbourne"


def test_parse_location_city_only():
    result = parse_location("Sydney NSW")
    assert result["city"] == "Sydney"
    assert result["suburb"] is None


import pytest
from unittest.mock import AsyncMock
from scraper import detect_total_pages


@pytest.mark.asyncio
async def test_detect_total_pages_reads_aria_labels():
    mock_page = AsyncMock()
    link1 = AsyncMock()
    link1.get_attribute = AsyncMock(return_value="Page 1")
    link2 = AsyncMock()
    link2.get_attribute = AsyncMock(return_value="Page 4")
    mock_page.query_selector_all = AsyncMock(return_value=[link1, link2])
    result = await detect_total_pages(mock_page)
    assert result == 4


@pytest.mark.asyncio
async def test_detect_total_pages_falls_back_to_one_on_error():
    mock_page = AsyncMock()
    mock_page.query_selector_all = AsyncMock(side_effect=Exception("timeout"))
    result = await detect_total_pages(mock_page)
    assert result == 1


@pytest.mark.asyncio
async def test_detect_total_pages_returns_one_when_no_links():
    mock_page = AsyncMock()
    mock_page.query_selector_all = AsyncMock(return_value=[])
    result = await detect_total_pages(mock_page)
    assert result == 1
