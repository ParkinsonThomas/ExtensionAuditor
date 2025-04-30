import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import API_Scraper as scraper


class TestAPIScraper(unittest.TestCase):

    @patch("API_Scraper.requests.get")
    def test_scrape_url_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'{"message": "OK"}'
        mock_get.return_value = mock_response

        with patch("API_Scraper.extract_documentation_url", return_value="https://docs.example.com"):
            result = scraper.scrape_url("https://api.example.com")

        self.assertIsInstance(result, tuple)
        self.assertEqual(result[1], 200)
        self.assertEqual(result[3], True)

    @patch("API_Scraper.requests.get", side_effect=Exception("fail"))
    def test_scrape_url_failure(self, mock_get):
        result = scraper.scrape_url("https://bad.api")
        self.assertIsNone(result)

    @patch("API_Scraper.requests.get")
    def test_extract_documentation_url_found(self, mock_get):
        html = '<html><body><a href="https://developer.example.com">Docs</a></body></html>'
        mock_get.return_value.text = html
        result = scraper.extract_documentation_url("https://api.example.com")
        self.assertIn("developer", result)

    @patch("API_Scraper.requests.get", side_effect=Exception("fail"))
    def test_extract_documentation_url_failure(self, mock_get):
        result = scraper.extract_documentation_url("https://api.example.com")
        self.assertIsNone(result)

    def test_update_api_entry_executes_sql(self):
        conn = MagicMock()
        scraper.update_api_entry(conn, "https://api.example.com", 200, 1234, True, "https://docs.example.com")
        conn.cursor().execute.assert_called()
        conn.commit.assert_called_once()

    def test_insert_data_processes_queue_items(self):
        q = MagicMock()
        q.get.side_effect = [
            ("https://api.example.com", 200, 500, True, "https://docs.example.com"),
            "FINISHED"
        ]

        with patch("API_Scraper.init_db_connection") as mock_conn_fn:
            mock_conn = MagicMock()
            mock_conn_fn.return_value = mock_conn
            scraper.insert_data("db.sqlite", q)

            self.assertTrue(mock_conn.cursor().execute.called)
            mock_conn.commit.assert_called()
            mock_conn.close.assert_called()

    def test_status_updater_prints_counts(self):
        import multiprocessing
        import time
        import threading

        counter_q = multiprocessing.Queue()
        for status in ["success", "fail", "success"]:
            counter_q.put(status)

        with patch("sys.stdout.write"):
            t = threading.Thread(target=scraper.status_updater, args=(counter_q, 3))
            t.start()
            t.join(timeout=2)
            self.assertFalse(t.is_alive())  # Should have exited

    @patch("API_Scraper.scrape_url", return_value=("https://api.example.com", 200, 123, True, "doc"))
    def test_scrape_api_success(self, mock_scrape):
        q = MagicMock()
        cq = MagicMock()
        scraper.scrape_api("https://api.example.com", q, cq)
        q.put.assert_called_once()
        cq.put.assert_called_once_with("success")

    @patch("API_Scraper.scrape_url", return_value=None)
    def test_scrape_api_failure(self, mock_scrape):
        q = MagicMock()
        cq = MagicMock()
        scraper.scrape_api("https://bad.api", q, cq)
        q.put.assert_not_called()
        cq.put.assert_called_once_with("fail")

    def test_init_db_connection_returns_conn(self):
        conn = scraper.init_db_connection(":memory:")
        import sqlite3
        self.assertIsInstance(conn, sqlite3.Connection)
        conn.close()


if __name__ == "__main__":
    unittest.main()