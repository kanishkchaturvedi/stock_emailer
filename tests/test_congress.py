"""Tests for congressional trades fetcher."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch
import json

import pytest

from smart_money_tracker.data_collection.congress import FetcherCongress
from smart_money_tracker.db.models import CongressionalTrade


class TestFetcherCongressInitialization:
    """Test suite for FetcherCongress initialization."""

    def test_fetcher_congress_initializes_with_default_db_client(self):
        """Test that FetcherCongress initializes with default db_client."""
        fetcher = FetcherCongress()
        assert fetcher.db_client is not None
        assert fetcher.timeout == 10

    def test_fetcher_congress_initializes_with_custom_db_client(self):
        """Test that FetcherCongress initializes with custom db_client."""
        mock_db = MagicMock()
        fetcher = FetcherCongress(db_client_instance=mock_db)
        assert fetcher.db_client is mock_db
        assert fetcher.timeout == 10

    def test_fetcher_congress_initializes_with_custom_timeout(self):
        """Test that FetcherCongress initializes with custom timeout."""
        mock_db = MagicMock()
        fetcher = FetcherCongress(db_client_instance=mock_db, timeout=20)
        assert fetcher.db_client is mock_db
        assert fetcher.timeout == 20

    def test_fetcher_congress_inherits_from_base_fetcher(self):
        """Test that FetcherCongress inherits from BaseFetcher."""
        from smart_money_tracker.data_collection.base import BaseFetcher

        fetcher = FetcherCongress()
        assert isinstance(fetcher, BaseFetcher)

    def test_fetcher_congress_has_fetch_method(self):
        """Test that FetcherCongress has fetch method."""
        fetcher = FetcherCongress()
        assert hasattr(fetcher, 'fetch')
        assert callable(fetcher.fetch)


class TestFetcherCongressDataParsing:
    """Test suite for data parsing in FetcherCongress."""

    def test_parse_trade_with_all_fields(self):
        """Test parsing trade with all required fields."""
        fetcher = FetcherCongress()
        trade_data = {
            'politician_name': 'John Smith',
            'ticker': 'AAPL',
            'transaction_type': 'buy',
            'disclosure_date': '2023-06-15',
            'estimated_amount': 50000.0,
        }

        result = fetcher._parse_trade(trade_data)

        assert result is not None
        assert result.politician == 'John Smith'
        assert result.ticker == 'AAPL'
        assert result.buy_or_sell == 'buy'
        assert result.disclosure_date == datetime(2023, 6, 15)
        assert result.estimated_amount == 50000.0

    def test_parse_trade_with_alternative_field_names(self):
        """Test parsing trade with alternative field names."""
        fetcher = FetcherCongress()
        trade_data = {
            'politician': 'Jane Doe',
            'symbol': 'MSFT',
            'buy_or_sell': 'sell',
            'date': '06/15/2023',
            'amount': 100000.0,
        }

        result = fetcher._parse_trade(trade_data)

        assert result is not None
        assert result.politician == 'Jane Doe'
        assert result.ticker == 'MSFT'
        assert result.buy_or_sell == 'sell'
        assert result.estimated_amount == 100000.0

    def test_parse_trade_normalizes_ticker_to_uppercase(self):
        """Test that ticker symbols are normalized to uppercase."""
        fetcher = FetcherCongress()
        trade_data = {
            'politician_name': 'John Smith',
            'ticker': 'aapl',
            'transaction_type': 'buy',
            'disclosure_date': '2023-06-15',
            'estimated_amount': 50000.0,
        }

        result = fetcher._parse_trade(trade_data)

        assert result.ticker == 'AAPL'

    def test_parse_trade_normalizes_transaction_type(self):
        """Test that transaction types are normalized to lowercase."""
        fetcher = FetcherCongress()

        # Test buy
        trade_data_buy = {
            'politician_name': 'John Smith',
            'ticker': 'AAPL',
            'transaction_type': 'BUY',
            'disclosure_date': '2023-06-15',
            'estimated_amount': 50000.0,
        }
        result_buy = fetcher._parse_trade(trade_data_buy)
        assert result_buy.buy_or_sell == 'buy'

        # Test sell
        trade_data_sell = {
            'politician_name': 'John Smith',
            'ticker': 'AAPL',
            'transaction_type': 'SELL',
            'disclosure_date': '2023-06-15',
            'estimated_amount': 50000.0,
        }
        result_sell = fetcher._parse_trade(trade_data_sell)
        assert result_sell.buy_or_sell == 'sell'

    def test_parse_trade_handles_whitespace_in_names(self):
        """Test that whitespace in politician names is trimmed."""
        fetcher = FetcherCongress()
        trade_data = {
            'politician_name': '  John Smith  ',
            'ticker': 'AAPL',
            'transaction_type': 'buy',
            'disclosure_date': '2023-06-15',
            'estimated_amount': 50000.0,
        }

        result = fetcher._parse_trade(trade_data)

        assert result.politician == 'John Smith'

    def test_parse_trade_returns_none_for_missing_politician(self):
        """Test that parsing fails gracefully for missing politician."""
        fetcher = FetcherCongress()
        trade_data = {
            'ticker': 'AAPL',
            'transaction_type': 'buy',
            'disclosure_date': '2023-06-15',
            'estimated_amount': 50000.0,
        }

        result = fetcher._parse_trade(trade_data)

        assert result is None

    def test_parse_trade_returns_none_for_missing_ticker(self):
        """Test that parsing fails gracefully for missing ticker."""
        fetcher = FetcherCongress()
        trade_data = {
            'politician_name': 'John Smith',
            'transaction_type': 'buy',
            'disclosure_date': '2023-06-15',
            'estimated_amount': 50000.0,
        }

        result = fetcher._parse_trade(trade_data)

        assert result is None

    def test_parse_trade_returns_none_for_invalid_transaction_type(self):
        """Test that parsing fails for invalid transaction type."""
        fetcher = FetcherCongress()
        trade_data = {
            'politician_name': 'John Smith',
            'ticker': 'AAPL',
            'transaction_type': 'unknown',
            'disclosure_date': '2023-06-15',
            'estimated_amount': 50000.0,
        }

        result = fetcher._parse_trade(trade_data)

        assert result is None

    def test_parse_trade_returns_none_for_missing_date(self):
        """Test that parsing fails gracefully for missing date."""
        fetcher = FetcherCongress()
        trade_data = {
            'politician_name': 'John Smith',
            'ticker': 'AAPL',
            'transaction_type': 'buy',
            'estimated_amount': 50000.0,
        }

        result = fetcher._parse_trade(trade_data)

        assert result is None

    def test_parse_trade_handles_various_date_formats(self):
        """Test that various date formats are parsed correctly."""
        fetcher = FetcherCongress()

        # Test ISO format
        trade_data_iso = {
            'politician_name': 'John Smith',
            'ticker': 'AAPL',
            'transaction_type': 'buy',
            'disclosure_date': '2023-06-15',
            'estimated_amount': 50000.0,
        }
        result = fetcher._parse_trade(trade_data_iso)
        assert result.disclosure_date == datetime(2023, 6, 15)

        # Test US format
        trade_data_us = {
            'politician_name': 'John Smith',
            'ticker': 'AAPL',
            'transaction_type': 'buy',
            'disclosure_date': '06/15/2023',
            'estimated_amount': 50000.0,
        }
        result = fetcher._parse_trade(trade_data_us)
        assert result.disclosure_date == datetime(2023, 6, 15)

    def test_parse_amount_with_string(self):
        """Test parsing amount from string."""
        fetcher = FetcherCongress()
        assert fetcher._parse_amount("50000") == 50000.0
        assert fetcher._parse_amount("50,000") == 50000.0
        assert fetcher._parse_amount("$50,000") == 50000.0

    def test_parse_amount_with_numeric_types(self):
        """Test parsing amount from numeric types."""
        fetcher = FetcherCongress()
        assert fetcher._parse_amount(50000) == 50000.0
        assert fetcher._parse_amount(50000.5) == 50000.5

    def test_parse_amount_with_range(self):
        """Test parsing amount from range format."""
        fetcher = FetcherCongress()
        # Range format should return midpoint
        amount = fetcher._parse_amount("1,000,000 - 5,000,000")
        assert amount == 3000000.0

    def test_parse_amount_with_invalid_input(self):
        """Test parsing amount with invalid input."""
        fetcher = FetcherCongress()
        assert fetcher._parse_amount("") == 0.0
        assert fetcher._parse_amount(None) == 0.0
        assert fetcher._parse_amount("invalid") == 0.0

    def test_parse_date_with_iso_format(self):
        """Test parsing date in ISO format."""
        fetcher = FetcherCongress()
        result = fetcher._parse_date("2023-06-15")
        assert result == datetime(2023, 6, 15)

    def test_parse_date_with_us_format(self):
        """Test parsing date in US format."""
        fetcher = FetcherCongress()
        result = fetcher._parse_date("06/15/2023")
        assert result == datetime(2023, 6, 15)

    def test_parse_date_with_invalid_format(self):
        """Test parsing date with invalid format."""
        fetcher = FetcherCongress()
        result = fetcher._parse_date("invalid-date")
        assert result is None

    def test_parse_date_with_empty_string(self):
        """Test parsing date with empty string."""
        fetcher = FetcherCongress()
        result = fetcher._parse_date("")
        assert result is None


class TestFetcherCongressAPIFetching:
    """Test suite for API fetching in FetcherCongress."""

    @patch('smart_money_tracker.data_collection.congress.requests.get')
    def test_fetch_impl_calls_senate_api(self, mock_get):
        """Test that _fetch_impl calls Senate API."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        fetcher = FetcherCongress(db_client_instance=MagicMock())
        result = fetcher._fetch_impl()

        assert result == []
        mock_get.assert_called()

    @patch('smart_money_tracker.data_collection.congress.requests.get')
    def test_fetch_impl_returns_list_of_congressional_trades(self, mock_get):
        """Test that _fetch_impl returns list of CongressionalTrade objects."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'politician_name': 'John Smith',
                'ticker': 'AAPL',
                'transaction_type': 'buy',
                'disclosure_date': '2023-06-15',
                'estimated_amount': 50000.0,
            },
            {
                'politician_name': 'Jane Doe',
                'ticker': 'MSFT',
                'transaction_type': 'sell',
                'disclosure_date': '2023-06-14',
                'estimated_amount': 100000.0,
            },
        ]
        mock_get.return_value = mock_response

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        fetcher = FetcherCongress(db_client_instance=mock_db)
        result = fetcher._fetch_impl()

        assert len(result) == 2
        assert all(isinstance(trade, CongressionalTrade) for trade in result)
        assert result[0].politician == 'John Smith'
        assert result[0].ticker == 'AAPL'
        assert result[1].politician == 'Jane Doe'
        assert result[1].ticker == 'MSFT'

    @patch('smart_money_tracker.data_collection.congress.requests.get')
    def test_fetch_from_senate_api_parses_multiple_trades(self, mock_get):
        """Test that Senate API parsing handles multiple trades."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'politician_name': 'John Smith',
                'ticker': 'AAPL',
                'transaction_type': 'buy',
                'disclosure_date': '2023-06-15',
                'estimated_amount': 50000.0,
            },
            {
                'politician_name': 'Jane Doe',
                'ticker': 'MSFT',
                'transaction_type': 'sell',
                'disclosure_date': '2023-06-14',
                'estimated_amount': 100000.0,
            },
        ]
        mock_get.return_value = mock_response

        fetcher = FetcherCongress()
        result = fetcher._fetch_from_senate_api()

        assert len(result) == 2

    @patch('smart_money_tracker.data_collection.congress.requests.get')
    def test_fetch_from_senate_api_handles_dict_response(self, mock_get):
        """Test that Senate API parsing handles dict response with trades key."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'trades': [
                {
                    'politician_name': 'John Smith',
                    'ticker': 'AAPL',
                    'transaction_type': 'buy',
                    'disclosure_date': '2023-06-15',
                    'estimated_amount': 50000.0,
                },
            ]
        }
        mock_get.return_value = mock_response

        fetcher = FetcherCongress()
        result = fetcher._fetch_from_senate_api()

        assert len(result) == 1

    @patch('smart_money_tracker.data_collection.congress.requests.get')
    def test_fetch_from_senate_api_skips_invalid_trades(self, mock_get):
        """Test that invalid trades are skipped during parsing."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'politician_name': 'John Smith',
                'ticker': 'AAPL',
                'transaction_type': 'buy',
                'disclosure_date': '2023-06-15',
                'estimated_amount': 50000.0,
            },
            {
                # Missing ticker - should be skipped
                'politician_name': 'Jane Doe',
                'transaction_type': 'sell',
                'disclosure_date': '2023-06-14',
                'estimated_amount': 100000.0,
            },
            {
                'politician_name': 'Bob Johnson',
                'ticker': 'MSFT',
                'transaction_type': 'buy',
                'disclosure_date': '2023-06-13',
                'estimated_amount': 75000.0,
            },
        ]
        mock_get.return_value = mock_response

        fetcher = FetcherCongress()
        result = fetcher._fetch_from_senate_api()

        # Should only have 2 valid trades
        assert len(result) == 2
        assert result[0].politician == 'John Smith'
        assert result[1].politician == 'Bob Johnson'

    @patch('smart_money_tracker.data_collection.congress.requests.get')
    def test_fetch_from_senate_api_handles_network_error(self, mock_get):
        """Test that network errors are handled properly."""
        mock_get.side_effect = Exception("Network error")

        fetcher = FetcherCongress()
        with pytest.raises(Exception):
            fetcher._fetch_from_senate_api()

    @patch('smart_money_tracker.data_collection.congress.requests.get')
    def test_fetch_impl_tries_house_api_if_senate_returns_empty(self, mock_get):
        """Test that House API is tried if Senate API returns empty."""
        # First call (Senate) returns empty, second call (House) returns data
        mock_response_senate = MagicMock()
        mock_response_senate.json.return_value = []

        mock_response_house = MagicMock()
        mock_response_house.json.return_value = [
            {
                'politician_name': 'John Smith',
                'ticker': 'AAPL',
                'transaction_type': 'buy',
                'disclosure_date': '2023-06-15',
                'estimated_amount': 50000.0,
            },
        ]

        mock_get.side_effect = [mock_response_senate, mock_response_house]

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        fetcher = FetcherCongress(db_client_instance=mock_db)
        result = fetcher._fetch_impl()

        assert len(result) == 1
        assert result[0].politician == 'John Smith'


class TestFetcherCongressDatabaseStorage:
    """Test suite for database storage in FetcherCongress."""

    def test_store_trades_calls_database(self):
        """Test that _store_trades calls database insert."""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        fetcher = FetcherCongress(db_client_instance=mock_db)

        trades = [
            CongressionalTrade(
                politician='John Smith',
                ticker='AAPL',
                buy_or_sell='buy',
                disclosure_date=datetime(2023, 6, 15),
                estimated_amount=50000.0,
            ),
        ]

        fetcher._store_trades(trades)

        # Verify database was called
        mock_db.get_connection.assert_called_once()
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_store_trades_inserts_correct_fields(self):
        """Test that _store_trades inserts correct field values."""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        fetcher = FetcherCongress(db_client_instance=mock_db)

        trades = [
            CongressionalTrade(
                politician='John Smith',
                ticker='AAPL',
                buy_or_sell='buy',
                disclosure_date=datetime(2023, 6, 15),
                estimated_amount=50000.0,
            ),
        ]

        fetcher._store_trades(trades)

        # Get the SQL and parameters from the execute call
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        # Verify SQL contains expected columns
        assert 'politician' in sql
        assert 'ticker' in sql
        assert 'buy_or_sell' in sql
        assert 'disclosure_date' in sql
        assert 'estimated_amount' in sql

        # Verify parameters contain expected values
        assert 'John Smith' in params
        assert 'AAPL' in params
        assert 'buy' in params

    def test_store_trades_handles_empty_list(self):
        """Test that _store_trades handles empty trade list."""
        mock_db = MagicMock()
        fetcher = FetcherCongress(db_client_instance=mock_db)

        fetcher._store_trades([])

        # Database should not be called
        mock_db.get_connection.assert_not_called()

    def test_store_trades_commits_transaction(self):
        """Test that _store_trades commits the transaction."""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        fetcher = FetcherCongress(db_client_instance=mock_db)

        trades = [
            CongressionalTrade(
                politician='John Smith',
                ticker='AAPL',
                buy_or_sell='buy',
                disclosure_date=datetime(2023, 6, 15),
                estimated_amount=50000.0,
            ),
        ]

        fetcher._store_trades(trades)

        mock_conn.commit.assert_called_once()

    def test_store_trades_closes_connection(self):
        """Test that _store_trades closes the database connection."""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        fetcher = FetcherCongress(db_client_instance=mock_db)

        trades = [
            CongressionalTrade(
                politician='John Smith',
                ticker='AAPL',
                buy_or_sell='buy',
                disclosure_date=datetime(2023, 6, 15),
                estimated_amount=50000.0,
            ),
        ]

        fetcher._store_trades(trades)

        mock_conn.close.assert_called_once()

    def test_store_trades_rollback_on_error(self):
        """Test that _store_trades rolls back on database error."""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Database error")
        mock_conn.cursor.return_value = mock_cursor

        fetcher = FetcherCongress(db_client_instance=mock_db)

        trades = [
            CongressionalTrade(
                politician='John Smith',
                ticker='AAPL',
                buy_or_sell='buy',
                disclosure_date=datetime(2023, 6, 15),
                estimated_amount=50000.0,
            ),
        ]

        with pytest.raises(Exception):
            fetcher._store_trades(trades)

        mock_conn.rollback.assert_called_once()

    def test_store_method_calls_store_trades(self):
        """Test that store() method calls _store_trades()."""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        fetcher = FetcherCongress(db_client_instance=mock_db)

        trades = [
            CongressionalTrade(
                politician='John Smith',
                ticker='AAPL',
                buy_or_sell='buy',
                disclosure_date=datetime(2023, 6, 15),
                estimated_amount=50000.0,
            ),
        ]

        fetcher.store(trades)

        # Verify database was called
        mock_db.get_connection.assert_called_once()
        mock_cursor.execute.assert_called()


class TestFetcherCongressIntegration:
    """Integration tests for FetcherCongress."""

    @patch('smart_money_tracker.data_collection.congress.requests.get')
    def test_fetch_and_store_workflow(self, mock_get):
        """Test complete fetch and store workflow."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'politician_name': 'John Smith',
                'ticker': 'AAPL',
                'transaction_type': 'buy',
                'disclosure_date': '2023-06-15',
                'estimated_amount': 50000.0,
            },
            {
                'politician_name': 'Jane Doe',
                'ticker': 'MSFT',
                'transaction_type': 'sell',
                'disclosure_date': '2023-06-14',
                'estimated_amount': 100000.0,
            },
        ]
        mock_get.return_value = mock_response

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        fetcher = FetcherCongress(db_client_instance=mock_db)
        result = fetcher.fetch()

        assert len(result) == 2
        assert result[0].politician == 'John Smith'
        assert result[1].politician == 'Jane Doe'
        assert mock_cursor.execute.call_count == 2

    @patch('smart_money_tracker.data_collection.congress.requests.get')
    def test_both_buy_and_sell_transactions_included(self, mock_get):
        """Test that both buy and sell transactions are stored."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'politician_name': 'John Smith',
                'ticker': 'AAPL',
                'transaction_type': 'buy',
                'disclosure_date': '2023-06-15',
                'estimated_amount': 50000.0,
            },
            {
                'politician_name': 'John Smith',
                'ticker': 'MSFT',
                'transaction_type': 'sell',
                'disclosure_date': '2023-06-14',
                'estimated_amount': 100000.0,
            },
        ]
        mock_get.return_value = mock_response

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        fetcher = FetcherCongress(db_client_instance=mock_db)
        result = fetcher.fetch()

        assert len(result) == 2
        buy_trades = [t for t in result if t.buy_or_sell == 'buy']
        sell_trades = [t for t in result if t.buy_or_sell == 'sell']
        assert len(buy_trades) == 1
        assert len(sell_trades) == 1

    @patch('smart_money_tracker.data_collection.congress.requests.get')
    def test_fetch_with_various_politician_names(self, mock_get):
        """Test that various politician name formats are handled."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'politician_name': 'John Smith Jr.',
                'ticker': 'AAPL',
                'transaction_type': 'buy',
                'disclosure_date': '2023-06-15',
                'estimated_amount': 50000.0,
            },
            {
                'politician_name': 'Jane Doe-Smith',
                'ticker': 'MSFT',
                'transaction_type': 'buy',
                'disclosure_date': '2023-06-14',
                'estimated_amount': 100000.0,
            },
            {
                'politician_name': 'Bob O\'Brien',
                'ticker': 'GOOG',
                'transaction_type': 'sell',
                'disclosure_date': '2023-06-13',
                'estimated_amount': 75000.0,
            },
        ]
        mock_get.return_value = mock_response

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        fetcher = FetcherCongress(db_client_instance=mock_db)
        result = fetcher.fetch()

        assert len(result) == 3
        assert result[0].politician == 'John Smith Jr.'
        assert result[1].politician == 'Jane Doe-Smith'
        assert result[2].politician == 'Bob O\'Brien'

    @patch('smart_money_tracker.data_collection.congress.requests.get')
    def test_fetch_with_various_ticker_formats(self, mock_get):
        """Test that various ticker formats are normalized."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'politician_name': 'John Smith',
                'ticker': 'aapl',
                'transaction_type': 'buy',
                'disclosure_date': '2023-06-15',
                'estimated_amount': 50000.0,
            },
            {
                'politician_name': 'Jane Doe',
                'ticker': 'BRK.B',
                'transaction_type': 'buy',
                'disclosure_date': '2023-06-14',
                'estimated_amount': 100000.0,
            },
        ]
        mock_get.return_value = mock_response

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        fetcher = FetcherCongress(db_client_instance=mock_db)
        result = fetcher.fetch()

        assert result[0].ticker == 'AAPL'
        assert result[1].ticker == 'BRK.B'

    @patch('smart_money_tracker.data_collection.congress.requests.get')
    def test_fetch_handles_various_amount_formats(self, mock_get):
        """Test that various amount formats are parsed correctly."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'politician_name': 'John Smith',
                'ticker': 'AAPL',
                'transaction_type': 'buy',
                'disclosure_date': '2023-06-15',
                'estimated_amount': 50000.0,
            },
            {
                'politician_name': 'Jane Doe',
                'ticker': 'MSFT',
                'transaction_type': 'buy',
                'disclosure_date': '2023-06-14',
                'estimated_amount': '$100,000',
            },
            {
                'politician_name': 'Bob Johnson',
                'ticker': 'GOOG',
                'transaction_type': 'buy',
                'disclosure_date': '2023-06-13',
                'estimated_amount': '1,000,000 - 5,000,000',
            },
        ]
        mock_get.return_value = mock_response

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        fetcher = FetcherCongress(db_client_instance=mock_db)
        result = fetcher.fetch()

        assert len(result) == 3
        assert result[0].estimated_amount == 50000.0
        assert result[1].estimated_amount == 100000.0
        assert result[2].estimated_amount == 3000000.0

    @patch('smart_money_tracker.data_collection.congress.requests.get')
    def test_fetch_returns_trades_with_correct_types(self, mock_get):
        """Test that fetched trades have correct data types."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                'politician_name': 'John Smith',
                'ticker': 'AAPL',
                'transaction_type': 'buy',
                'disclosure_date': '2023-06-15',
                'estimated_amount': 50000.0,
            },
        ]
        mock_get.return_value = mock_response

        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_db.get_connection.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        fetcher = FetcherCongress(db_client_instance=mock_db)
        result = fetcher.fetch()

        trade = result[0]
        assert isinstance(trade.politician, str)
        assert isinstance(trade.ticker, str)
        assert isinstance(trade.buy_or_sell, str)
        assert isinstance(trade.disclosure_date, datetime)
        assert isinstance(trade.estimated_amount, float)

    @patch('smart_money_tracker.data_collection.congress.requests.get')
    def test_fetch_with_network_error_raises_exception(self, mock_get):
        """Test that network errors are propagated."""
        mock_get.side_effect = Exception("Network error")

        fetcher = FetcherCongress(db_client_instance=MagicMock())

        with pytest.raises(Exception):
            fetcher.fetch()

    @patch('smart_money_tracker.data_collection.congress.requests.get')
    def test_fetch_with_invalid_json_handles_gracefully(self, mock_get):
        """Test that invalid JSON responses are handled gracefully."""
        mock_response = MagicMock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_get.return_value = mock_response

        fetcher = FetcherCongress(db_client_instance=MagicMock())

        with pytest.raises(Exception):
            fetcher.fetch()
