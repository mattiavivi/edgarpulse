"""Offline test: Form 4 XML parsing (no network)."""
from edgarpulse import SECInsider

FORM4_SAMPLE = """<?xml version="1.0"?>
<ownershipDocument>
  <issuer>
    <issuerTradingSymbol>NVDA</issuerTradingSymbol>
    <issuerName>NVIDIA CORP</issuerName>
  </issuer>
  <periodOfReport>2026-09-03</periodOfReport>
  <reportingOwnerId>
    <rptOwnerName>DOE JOHN</rptOwnerName>
  </reportingOwnerId>
  <reportingOwnerRelationship>
    <isOfficer>1</isOfficer>
    <isDirector>0</isDirector>
    <isTenPercentOwner>0</isTenPercentOwner>
    <officerTitle>Chief Financial Officer</officerTitle>
  </reportingOwnerRelationship>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionDate><value>2026-09-03</value></transactionDate>
      <transactionCoding><transactionCode>S</transactionCode></transactionCoding>
      <transactionShares><value>100</value></transactionShares>
      <transactionPricePerShare><value>200.0</value></transactionPricePerShare>
      <transactionAcquiredDisposedCode><value>D</value></transactionAcquiredDisposedCode>
      <directOrIndirectOwnership><value>D</value></directOrIndirectOwnership>
    </nonDerivativeTransaction>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionDate><value>2026-09-03</value></transactionDate>
      <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
      <transactionShares><value>50</value></transactionShares>
      <transactionPricePerShare><value>190.0</value></transactionPricePerShare>
      <transactionAcquiredDisposedCode><value>A</value></transactionAcquiredDisposedCode>
      <directOrIndirectOwnership><value>D</value></directOrIndirectOwnership>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>
"""


import logging
from unittest.mock import MagicMock

import requests


def test_parse_form4_summary():
    mgr = SECInsider.__new__(SECInsider)
    filing = SECInsider.parse_form4_xml(mgr, FORM4_SAMPLE)

    assert filing.ticker == "NVDA"
    assert filing.owner_name == "DOE JOHN"
    assert filing.is_officer is True
    assert filing.officer_title == "Chief Financial Officer"
    assert len(filing.transactions) == 2
    assert filing.total_shares_sold == 100
    assert filing.total_shares_bought == 50
    assert filing.total_usd_sold == 100 * 200.0
    assert filing.total_usd_bought == 50 * 190.0
    assert filing.to_dict()["ticker"] == "NVDA"


def test_get_latest_insider_trades_handling_and_logging(caplog):
    mock_client = MagicMock()
    mock_client.get_submissions.return_value = {
        "cik": "0001045810",
        "filings": {
            "recent": {
                "form": ["4", "4", "4"],
                "accessionNumber": ["0001-26-000001", "0001-26-000002", "0001-26-000003"],
                "primaryDocument": ["xslF345X06/form4_1.xml", "form4_2.xml", "form4_3.xml"],
                "filingDate": ["2026-09-01", "2026-09-02", "2026-09-03"],
            }
        },
    }
    mock_client.get_archive_url.side_effect = lambda cik, acc, doc: f"https://sec.gov/{cik}/{acc}/{doc}"

    # Response 1: Valid XML
    res1 = MagicMock()
    res1.text = FORM4_SAMPLE

    # Response 2: Request error (e.g. 404 or connection error)
    # response.get() raises RequestException

    # Response 3: Corrupted XML
    res3 = MagicMock()
    res3.text = "<ownershipDocument><invalid_xml>"

    def mock_get(url):
        if "000001" in url:
            return res1
        elif "000002" in url:
            raise requests.exceptions.RequestException("404 Not Found")
        elif "000003" in url:
            return res3
        raise ValueError("Unexpected URL")

    mock_client.get.side_effect = mock_get

    insider = SECInsider(client=mock_client)

    with caplog.at_level(logging.WARNING):
        results = insider.get_latest_insider_trades("NVDA", limit=5)

    assert len(results) == 1
    assert results[0].ticker == "NVDA"
    assert results[0].accession_number == "0001-26-000001"

    # Verify that warnings were logged for the failed requests
    warnings = [rec.message for rec in caplog.records if rec.levelno == logging.WARNING]
    assert len(warnings) == 2
    assert "Failed to fetch or parse Form 4 XML" in warnings[0]
    assert "404 Not Found" in warnings[0]
    assert "Failed to fetch or parse Form 4 XML" in warnings[1]
