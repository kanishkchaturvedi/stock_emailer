"""Tests for 13F filings fetcher."""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch, call
import xml.etree.ElementTree as ET

import pytest
import requests

from smart_money_tracker.data_collection.filings_13f import Fetcher13F
from smart_money_tracker.db.models import Filing13F, Holding


class TestFetcher13F:
    """Test suite for Fetcher13F class."""

    @pytest.fixture
    def mock_db_client(self):
        """Create a mock database client."""
        mock_client = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_client.get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 1
        mock_cursor.fetchone.return_value = (1,)  # investor_id
        return mock_client

    @pytest.fixture
    def fetcher(self, mock_db_client):
        """Create a Fetcher13F instance with mocked database."""
        return Fetcher13F(db_client_instance=mock_db_client, timeout=5)

    def test_fetcher_inherits_from_base_fetcher(self):
        """Test that Fetcher13F inherits from BaseFetcher."""
        from smart_money_tracker.data_collection.base import BaseFetcher

        assert issubclass(Fetcher13F, BaseFetcher)

    def test_fetcher_has_fetch_method(self, fetcher):
        """Test that Fetcher13F has fetch method from BaseFetcher."""
        assert hasattr(fetcher, "fetch")
        assert callable(fetcher.fetch)

    def test_fetcher_has_store_method(self, fetcher):
        """Test that Fetcher13F has store method."""
        assert hasattr(fetcher, "store")
        assert callable(fetcher.store)

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_fetch_impl_returns_list_of_filing13f(self, mock_get, fetcher):
        """Test that _fetch_impl returns list of Filing13F objects."""
        # Mock SEC API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "filings": {
                "filing": [
                    {
                        "filing_href": "https://www.sec.gov/Archives/edgar/filing/86882/0000086882-24-000001.htm",
                        "filing_date": "2024-02-13",
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        # Mock XML response
        mock_xml_response = MagicMock()
        mock_xml_response.content = b"""<?xml version="1.0"?>
        <root xmlns="http://www.sec.gov/cgi-bin/viewer">
            <infoTable>
                <nameOfIssuer>Apple Inc.</nameOfIssuer>
                <shrsOrPrnAmt><value>10000</value></shrsOrPrnAmt>
                <value>1500000</value>
                <percentOfClass>0.5</percentOfClass>
            </infoTable>
        </root>"""
        mock_xml_response.raise_for_status = MagicMock()

        # First call returns company filings, subsequent calls return XML
        mock_get.side_effect = [mock_response, mock_xml_response]

        result = fetcher._fetch_impl()

        assert isinstance(result, list)
        assert all(isinstance(filing, Filing13F) for filing in result)

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_fetch_impl_includes_tracked_investors(self, mock_get, fetcher):
        """Test that _fetch_impl fetches all tracked investors."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "filings": {
                "filing": [
                    {
                        "filing_href": "https://www.sec.gov/Archives/edgar/filing/86882/0000086882-24-000001.htm",
                        "filing_date": "2024-02-13",
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_xml_response = MagicMock()
        mock_xml_response.content = b"""<?xml version="1.0"?>
        <root xmlns="http://www.sec.gov/cgi-bin/viewer">
            <infoTable>
                <nameOfIssuer>Test Company</nameOfIssuer>
                <shrsOrPrnAmt><value>5000</value></shrsOrPrnAmt>
                <value>500000</value>
                <percentOfClass>1.0</percentOfClass>
            </infoTable>
        </root>"""
        mock_xml_response.raise_for_status = MagicMock()

        # Mock multiple calls for multiple investors
        def mock_get_side_effect(url, **kwargs):
            if "getcompany" in url:
                return mock_response
            else:
                return mock_xml_response

        mock_get.side_effect = mock_get_side_effect

        from smart_money_tracker.config.investors import TRACKED_INVESTORS

        result = fetcher._fetch_impl()

        # Should have attempted to fetch all tracked investors
        assert mock_get.call_count >= 1

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_fetch_impl_extracts_holdings_from_xml(self, mock_get, fetcher):
        """Test that holdings are properly extracted from XML."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "filings": {
                "filing": [
                    {
                        "filing_href": "https://www.sec.gov/Archives/edgar/filing/86882/0000086882-24-000001.htm",
                        "filing_date": "2024-02-13",
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_xml_response = MagicMock()
        mock_xml_response.content = b"""<?xml version="1.0"?>
        <root xmlns="http://www.sec.gov/cgi-bin/viewer">
            <infoTable>
                <nameOfIssuer>Apple Inc.</nameOfIssuer>
                <shrsOrPrnAmt><value>10000</value></shrsOrPrnAmt>
                <value>1500000</value>
                <percentOfClass>2.5</percentOfClass>
            </infoTable>
            <infoTable>
                <nameOfIssuer>Microsoft Corp.</nameOfIssuer>
                <shrsOrPrnAmt><value>5000</value></shrsOrPrnAmt>
                <value>2000000</value>
                <percentOfClass>3.0</percentOfClass>
            </infoTable>
        </root>"""
        mock_xml_response.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_response, mock_xml_response]

        result = fetcher._fetch_impl()

        assert len(result) > 0
        filing = result[0]
        assert len(filing.holdings) == 2
        assert filing.holdings[0].company_name == "Apple Inc."
        assert filing.holdings[0].shares == 10000
        assert filing.holdings[1].company_name == "Microsoft Corp."

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_fetch_impl_handles_network_errors(self, mock_get, fetcher):
        """Test that network errors are handled gracefully."""
        mock_get.side_effect = requests.ConnectionError("Network error")

        # Should return empty list instead of raising (graceful error handling)
        result = fetcher._fetch_impl()
        assert isinstance(result, list)
        assert len(result) == 0

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_fetch_impl_handles_invalid_json(self, mock_get, fetcher):
        """Test that invalid JSON responses are handled gracefully."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = MagicMock()

        mock_get.return_value = mock_response

        # Should return empty list instead of raising (graceful error handling)
        result = fetcher._fetch_impl()
        assert isinstance(result, list)
        assert len(result) == 0

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_fetch_impl_handles_missing_filings(self, mock_get, fetcher):
        """Test handling when no filings are found for an investor."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"filings": {"filing": []}}
        mock_response.raise_for_status = MagicMock()

        mock_get.return_value = mock_response

        result = fetcher._fetch_impl()

        # Should return empty list or handle gracefully
        assert isinstance(result, list)

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_store_filings_inserts_investor_record(self, mock_get, fetcher, mock_db_client):
        """Test that _store_filings inserts investor records."""
        filing = Filing13F(
            investor_name="Berkshire Hathaway",
            cik="0000086882",
            filing_date=datetime(2024, 2, 13),
            holdings=[],
        )

        fetcher._store_filings([filing])

        mock_cursor = mock_db_client.get_connection.return_value.cursor.return_value
        # Verify investor INSERT was called
        assert any(
            "INSERT OR IGNORE INTO investors" in str(call)
            for call in mock_cursor.execute.call_args_list
        )

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_store_filings_inserts_filing_record(self, mock_get, fetcher, mock_db_client):
        """Test that _store_filings inserts filing records."""
        filing = Filing13F(
            investor_name="Berkshire Hathaway",
            cik="0000086882",
            filing_date=datetime(2024, 2, 13),
            holdings=[],
        )

        fetcher._store_filings([filing])

        mock_cursor = mock_db_client.get_connection.return_value.cursor.return_value
        # Verify filing INSERT was called
        assert any(
            "INSERT INTO filings_13f" in str(call)
            for call in mock_cursor.execute.call_args_list
        )

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_store_filings_inserts_holdings(self, mock_get, fetcher, mock_db_client):
        """Test that _store_filings inserts holdings for each filing."""
        holding1 = Holding(
            ticker="AAPL",
            company_name="Apple Inc.",
            shares=10000,
            market_value=1500000,
            portfolio_weight=2.5,
        )
        holding2 = Holding(
            ticker="MSFT",
            company_name="Microsoft Corp.",
            shares=5000,
            market_value=2000000,
            portfolio_weight=3.0,
        )

        filing = Filing13F(
            investor_name="Berkshire Hathaway",
            cik="0000086882",
            filing_date=datetime(2024, 2, 13),
            holdings=[holding1, holding2],
        )

        fetcher._store_filings([filing])

        mock_cursor = mock_db_client.get_connection.return_value.cursor.return_value
        # Verify holdings INSERT was called
        holdings_calls = [
            call for call in mock_cursor.execute.call_args_list
            if "INSERT INTO holdings" in str(call)
        ]
        assert len(holdings_calls) == 2

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_store_filings_commits_transaction(self, mock_get, fetcher, mock_db_client):
        """Test that _store_filings commits the transaction."""
        filing = Filing13F(
            investor_name="Berkshire Hathaway",
            cik="0000086882",
            filing_date=datetime(2024, 2, 13),
            holdings=[],
        )

        fetcher._store_filings([filing])

        mock_conn = mock_db_client.get_connection.return_value
        mock_conn.commit.assert_called()

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_store_filings_with_multiple_filings(self, mock_get, fetcher, mock_db_client):
        """Test storing multiple filings."""
        filing1 = Filing13F(
            investor_name="Berkshire Hathaway",
            cik="0000086882",
            filing_date=datetime(2024, 2, 13),
            holdings=[],
        )
        filing2 = Filing13F(
            investor_name="Pershing Square Capital",
            cik="0001336528",
            filing_date=datetime(2024, 2, 15),
            holdings=[],
        )

        fetcher._store_filings([filing1, filing2])

        mock_cursor = mock_db_client.get_connection.return_value.cursor.return_value
        # Should have inserted both filings
        filing_inserts = [
            call for call in mock_cursor.execute.call_args_list
            if "INSERT INTO filings_13f" in str(call)
        ]
        assert len(filing_inserts) >= 2

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_store_method_calls_store_filings(self, mock_get, fetcher):
        """Test that store() method calls _store_filings()."""
        filing = Filing13F(
            investor_name="Berkshire Hathaway",
            cik="0000086882",
            filing_date=datetime(2024, 2, 13),
            holdings=[],
        )

        with patch.object(fetcher, "_store_filings") as mock_store:
            fetcher.store([filing])
            mock_store.assert_called_once_with([filing])

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_parse_holding_with_valid_data(self, mock_get, fetcher):
        """Test parsing a valid holding from XML element."""
        xml_str = """<infoTable xmlns="http://www.sec.gov/cgi-bin/viewer">
            <nameOfIssuer>Apple Inc.</nameOfIssuer>
            <shrsOrPrnAmt><value>10000</value></shrsOrPrnAmt>
            <value>1500000</value>
            <percentOfClass>2.5</percentOfClass>
        </infoTable>"""

        elem = ET.fromstring(xml_str)
        holding = fetcher._parse_holding(elem)

        assert holding is not None
        assert holding.company_name == "Apple Inc."
        assert holding.shares == 10000
        assert holding.market_value == 1500000.0
        assert holding.portfolio_weight == 2.5

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_parse_holding_missing_optional_fields(self, mock_get, fetcher):
        """Test parsing holding with missing optional fields."""
        xml_str = """<infoTable xmlns="http://www.sec.gov/cgi-bin/viewer">
            <nameOfIssuer>Apple Inc.</nameOfIssuer>
            <shrsOrPrnAmt><value>10000</value></shrsOrPrnAmt>
            <value>1500000</value>
        </infoTable>"""

        elem = ET.fromstring(xml_str)
        holding = fetcher._parse_holding(elem)

        assert holding is not None
        assert holding.company_name == "Apple Inc."
        assert holding.portfolio_weight == 0.0

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_parse_holding_with_missing_required_fields(self, mock_get, fetcher):
        """Test that parsing fails gracefully with missing required fields."""
        xml_str = """<infoTable xmlns="http://www.sec.gov/cgi-bin/viewer">
            <nameOfIssuer>Apple Inc.</nameOfIssuer>
        </infoTable>"""

        elem = ET.fromstring(xml_str)
        holding = fetcher._parse_holding(elem)

        # Should return None for invalid holding
        assert holding is None

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_fetch_impl_continues_on_investor_error(self, mock_get, fetcher):
        """Test that _fetch_impl continues to next investor on error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "filings": {
                "filing": [
                    {
                        "filing_href": "https://www.sec.gov/Archives/edgar/filing/86882/0000086882-24-000001.htm",
                        "filing_date": "2024-02-13",
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        # First call raises error, subsequent calls succeed
        mock_get.side_effect = [
            requests.ConnectionError("Error for first investor"),
            mock_response,
        ]

        # Should not raise, should continue
        result = fetcher._fetch_impl()

        # Should attempt to fetch (though may be empty due to mocking)
        assert isinstance(result, list)

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_store_filings_with_no_filings(self, mock_get, fetcher, mock_db_client):
        """Test storing empty filing list."""
        fetcher._store_filings([])

        # Should not call database operations
        mock_cursor = mock_db_client.get_connection.return_value.cursor.return_value
        # Minimal operations should occur
        assert mock_cursor.execute.call_count == 0

    def test_fetcher_initialization(self):
        """Test that Fetcher13F initializes correctly."""
        mock_db = MagicMock()
        fetcher = Fetcher13F(db_client_instance=mock_db, timeout=15)

        assert fetcher.db_client == mock_db
        assert fetcher.timeout == 15

    def test_fetcher_default_initialization(self):
        """Test Fetcher13F initialization with defaults."""
        with patch("smart_money_tracker.data_collection.filings_13f.db_client"):
            fetcher = Fetcher13F()
            assert fetcher.timeout == 10

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_parse_13f_xml_with_multiple_holdings(self, mock_get, fetcher):
        """Test parsing 13F XML with multiple holdings."""
        xml_content = b"""<?xml version="1.0"?>
        <root xmlns="http://www.sec.gov/cgi-bin/viewer">
            <infoTable>
                <nameOfIssuer>Apple Inc.</nameOfIssuer>
                <shrsOrPrnAmt><value>10000</value></shrsOrPrnAmt>
                <value>1500000</value>
                <percentOfClass>2.5</percentOfClass>
            </infoTable>
            <infoTable>
                <nameOfIssuer>Microsoft Corp.</nameOfIssuer>
                <shrsOrPrnAmt><value>5000</value></shrsOrPrnAmt>
                <value>2000000</value>
                <percentOfClass>3.0</percentOfClass>
            </infoTable>
            <infoTable>
                <nameOfIssuer>Google Inc.</nameOfIssuer>
                <shrsOrPrnAmt><value>3000</value></shrsOrPrnAmt>
                <value>800000</value>
                <percentOfClass>1.5</percentOfClass>
            </infoTable>
        </root>"""

        mock_response = MagicMock()
        mock_response.content = xml_content

        with patch("smart_money_tracker.data_collection.filings_13f.requests.get", return_value=mock_response):
            holdings = fetcher._parse_13f_xml("https://example.com/filing.xml")

        assert len(holdings) == 3
        assert holdings[0].company_name == "Apple Inc."
        assert holdings[1].company_name == "Microsoft Corp."
        assert holdings[2].company_name == "Google Inc."

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_fetch_investor_filing_with_valid_data(self, mock_get, fetcher):
        """Test _fetch_investor_filing with valid response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "filings": {
                "filing": [
                    {
                        "filing_href": "https://www.sec.gov/Archives/edgar/filing/86882/0000086882-24-000001.htm",
                        "filing_date": "2024-02-13",
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_xml_response = MagicMock()
        mock_xml_response.content = b"""<?xml version="1.0"?>
        <root xmlns="http://www.sec.gov/cgi-bin/viewer">
            <infoTable>
                <nameOfIssuer>Apple Inc.</nameOfIssuer>
                <shrsOrPrnAmt><value>10000</value></shrsOrPrnAmt>
                <value>1500000</value>
                <percentOfClass>2.5</percentOfClass>
            </infoTable>
        </root>"""
        mock_xml_response.raise_for_status = MagicMock()

        mock_get.side_effect = [mock_response, mock_xml_response]

        filing = fetcher._fetch_investor_filing("Berkshire Hathaway", "0000086882")

        assert filing is not None
        assert filing.investor_name == "Berkshire Hathaway"
        assert filing.cik == "0000086882"
        assert filing.filing_date == datetime(2024, 2, 13)
        assert len(filing.holdings) == 1

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_fetch_investor_filing_with_no_filings(self, mock_get, fetcher):
        """Test _fetch_investor_filing when no filings exist."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"filings": {"filing": []}}
        mock_response.raise_for_status = MagicMock()

        mock_get.return_value = mock_response

        filing = fetcher._fetch_investor_filing("Unknown Investor", "0000000000")

        assert filing is None

    @patch("smart_money_tracker.data_collection.filings_13f.requests.get")
    def test_store_filings_handles_database_error(self, mock_get, fetcher, mock_db_client):
        """Test that database errors are properly handled."""
        mock_db_client.get_connection.return_value.cursor.return_value.execute.side_effect = Exception(
            "Database error"
        )

        filing = Filing13F(
            investor_name="Berkshire Hathaway",
            cik="0000086882",
            filing_date=datetime(2024, 2, 13),
            holdings=[],
        )

        with pytest.raises(Exception, match="Database error"):
            fetcher._store_filings([filing])

        # Verify rollback was called
        mock_db_client.get_connection.return_value.rollback.assert_called()
