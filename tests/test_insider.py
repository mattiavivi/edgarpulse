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
