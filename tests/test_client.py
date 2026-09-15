"""Test unitari per SECClient: rate limiter, header Host e retry resiliente."""
from unittest.mock import MagicMock, patch
import pytest
import requests
from edgarpulse import SECClient


def test_client_sets_correct_host_headers():
    client = SECClient(user_agent="TestApp test@test.com")
    mock_resp = MagicMock(status_code=200)

    with patch.object(client.session, "get", return_value=mock_resp) as mock_get:
        # data.sec.gov
        client.get("https://data.sec.gov/submissions/CIK0001045810.json")
        headers = mock_get.call_args[1]["headers"]
        assert headers["Host"] == "data.sec.gov"
        assert headers["User-Agent"] == "TestApp test@test.com"

        # www.sec.gov
        client.get("https://www.sec.gov/files/company_tickers.json")
        headers = mock_get.call_args[1]["headers"]
        assert headers["Host"] == "www.sec.gov"

        # efts.sec.gov
        client.get("https://efts.sec.gov/LATEST/search-index?q=tender")
        headers = mock_get.call_args[1]["headers"]
        assert headers["Host"] == "efts.sec.gov"

        # Custom override
        client.get("https://efts.sec.gov/LATEST/search-index", headers={"Host": "custom.sec.gov"})
        headers = mock_get.call_args[1]["headers"]
        assert headers["Host"] == "custom.sec.gov"


def test_client_retries_on_500_and_recovers():
    client = SECClient(max_retries=2, backoff_factor=0.01)

    resp_500 = MagicMock(status_code=500)
    resp_200 = MagicMock(status_code=200)

    with patch.object(client.session, "get", side_effect=[resp_500, resp_200]) as mock_get, \
         patch("time.sleep") as mock_sleep:
        resp = client.get("https://efts.sec.gov/LATEST/search-index")
        assert resp.status_code == 200
        assert mock_get.call_count == 2
        mock_sleep.assert_called()


def test_client_exhausts_retries_on_500():
    client = SECClient(max_retries=2, backoff_factor=0.01)

    resp_500 = MagicMock(status_code=500)
    resp_500.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")

    with patch.object(client.session, "get", return_value=resp_500) as mock_get, \
         patch("time.sleep"):
        with pytest.raises(requests.exceptions.HTTPError, match="500 Server Error"):
            client.get("https://efts.sec.gov/LATEST/search-index")
        # 1 iniziale + 2 retry = 3 chiamate totali
        assert mock_get.call_count == 3


def test_client_retries_on_429_with_retry_after():
    client = SECClient(max_retries=2, backoff_factor=0.01)

    resp_429 = MagicMock(status_code=429, headers={"Retry-After": "3"})
    resp_200 = MagicMock(status_code=200)

    with patch.object(client.session, "get", side_effect=[resp_429, resp_200]) as mock_get, \
         patch("time.sleep") as mock_sleep:
        resp = client.get("https://data.sec.gov/submissions/CIK0001045810.json")
        assert resp.status_code == 200
        assert mock_get.call_count == 2
        mock_sleep.assert_any_call(3)


def test_client_retries_on_connection_error_and_recovers():
    client = SECClient(max_retries=2, backoff_factor=0.01)

    resp_200 = MagicMock(status_code=200)

    with patch.object(client.session, "get", side_effect=[
        requests.exceptions.ConnectionError("Connection aborted"),
        resp_200
    ]) as mock_get, patch("time.sleep"):
        resp = client.get("https://efts.sec.gov/LATEST/search-index")
        assert resp.status_code == 200
        assert mock_get.call_count == 2


def test_client_does_not_retry_on_404_or_403():
    client = SECClient(max_retries=3, backoff_factor=0.01)

    resp_404 = MagicMock(status_code=404)
    resp_404.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")

    with patch.object(client.session, "get", return_value=resp_404) as mock_get, \
         patch.object(client, "_rate_limit"), \
         patch("time.sleep") as mock_sleep:
        with pytest.raises(requests.exceptions.HTTPError, match="404 Not Found"):
            client.get("https://www.sec.gov/files/not_found.json")
        assert mock_get.call_count == 1
        mock_sleep.assert_not_called()

    resp_403 = MagicMock(status_code=403)
    resp_403.raise_for_status.side_effect = requests.exceptions.HTTPError("403 Forbidden")

    with patch.object(client.session, "get", return_value=resp_403) as mock_get, \
         patch.object(client, "_rate_limit"), \
         patch("time.sleep") as mock_sleep:
        with pytest.raises(requests.exceptions.HTTPError, match="403 Forbidden"):
            client.get("https://data.sec.gov/submissions/forbidden.json")
        assert mock_get.call_count == 1
        mock_sleep.assert_not_called()

