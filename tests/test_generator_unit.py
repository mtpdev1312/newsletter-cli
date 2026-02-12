from newsletter_cli.generator import _extract_first_detail_image, _format_currency


def test_format_currency_uses_german_format():
    assert _format_currency(1234.5) == "1.234,50"


def test_extract_first_detail_image_prefers_article_match():
    urls = [
        "https://cdn.example.com/OTHER.jpg",
        "https://cdn.example.com/MTP102004.jpg",
    ]
    assert _extract_first_detail_image(urls, "MTP102004") == urls[1]


def test_extract_first_detail_image_fallbacks_to_first():
    urls = ["https://cdn.example.com/first.jpg", "https://cdn.example.com/second.jpg"]
    assert _extract_first_detail_image(urls, "NOT_FOUND") == urls[0]
