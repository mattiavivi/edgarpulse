"""Offline test: 8-K HTML cleaning + Item segmentation (no network)."""
from edgarpulse import SECEventManager

HTML_SAMPLE = """
<html><head><style>.x{color:red}</style><script>alert(1)</script></head>
<body>
<p>Item 1.01 Entry into a Material Definitive Agreement</p>
<p>On Sep 2, 2026 NVIDIA entered into a definitive merger agreement to acquire XYZ for $1B.</p>
<p>Item 9.01 Financial Statements and Exhibits</p>
<p>(d) Exhibits</p>
<p>SIGNATURES</p>
<p>Pursuant to the requirements...</p>
</body></html>
"""


def test_clean_html_strips_noise():
    mgr = SECEventManager.__new__(SECEventManager)
    text = SECEventManager.clean_html(mgr, HTML_SAMPLE)
    assert "alert(1)" not in text
    assert "merger agreement" in text.lower()


def test_extract_items_and_ma_flag():
    mgr = SECEventManager.__new__(SECEventManager)
    text = SECEventManager.clean_html(mgr, HTML_SAMPLE)
    items = SECEventManager.extract_items_from_text(mgr, text)
    codes = [i.item_code for i in items]
    assert "1.01" in codes
    assert "9.01" in codes
    ma = [i for i in items if i.item_code == "1.01"][0]
    assert ma.is_ma_related is True
    other = [i for i in items if i.item_code == "9.01"][0]
    assert other.is_ma_related is False
