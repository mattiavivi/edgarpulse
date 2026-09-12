"""Offline test: Atom feed filtering with mocked HTTP client (no network)."""
from edgarpulse import SECFeed

ATOM_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>8-K - NVIDIA CORP (0001045810) (Filer)</title>
    <updated>2026-09-03T10:00:00-04:00</updated>
    <link href="https://www.sec.gov/Archives/edgar/data/1045810/xxx/nvda-8k.htm"/>
    <summary>AccNo: 0001045810-26-000078</summary>
  </entry>
  <entry>
    <title>10-Q - NVIDIA CORP (0001045810) (Filer)</title>
    <updated>2026-09-03T09:00:00-04:00</updated>
    <link href="https://www.sec.gov/Archives/edgar/data/1045810/yyy/nvda-10q.htm"/>
    <summary>AccNo: 0001045810-26-000079</summary>
  </entry>
</feed>
"""


class _FakeResponse:
    content = ATOM_SAMPLE.encode("utf-8")


class _FakeClient:
    def get(self, url, **kwargs):
        return _FakeResponse()

    def get_cik(self, ticker):
        return "0001045810"


def test_feed_filters_target_forms():
    feed = SECFeed(client=_FakeClient())
    filings = feed.get_latest_filings(target_forms=["8-K"], count=10)
    assert len(filings) == 1
    assert filings[0].form == "8-K"
    assert filings[0].accession_number == "0001045810-26-000078"
