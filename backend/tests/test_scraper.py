from scraper import parse_location, build_seek_url


def test_build_seek_url_contains_seek_domain():
    url = build_seek_url("python developer", "Melbourne VIC", page=1)
    assert "seek.com.au" in url


def test_build_seek_url_contains_keywords():
    url = build_seek_url("python developer", "Melbourne VIC", page=1)
    assert "python" in url.lower() or "keywords" in url.lower()


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
