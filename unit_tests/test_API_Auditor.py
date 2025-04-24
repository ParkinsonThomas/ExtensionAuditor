import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import API_Auditor as auditor

class TestAPIAuditor(unittest.TestCase):

    def test_find_api_usage_basic_patterns(self):
        js_code = """
        chrome.runtime.sendMessage();
        fetch('https://api.example.com/data');
        new XMLHttpRequest();
        var link = 'https://not-an-api.com/info';
        """
        m = mock_open(read_data=js_code)
        with patch("builtins.open", m):
            result = auditor.find_api_usage("sample.js", conn=None)
        self.assertEqual(len(result), 5)

    def test_get_api_entry_exists(self):
        mock_conn = MagicMock()
        mock_conn.cursor().fetchone.return_value = (1,)
        self.assertEqual(auditor.get_api_entry(mock_conn, "https://api.example.com"), 1)

    def test_get_api_entry_not_exists(self):
        mock_conn = MagicMock()
        mock_conn.cursor().fetchone.return_value = None
        self.assertIsNone(auditor.get_api_entry(mock_conn, "https://notfound.com"))

    def test_get_url_entry_true(self):
        mock_conn = MagicMock()
        mock_conn.cursor().fetchone.return_value = (1,)
        self.assertTrue(auditor.get_url_entry(mock_conn, "https://some-url.com"))

    def test_get_url_entry_false(self):
        mock_conn = MagicMock()
        mock_conn.cursor().fetchone.return_value = None
        self.assertFalse(auditor.get_url_entry(mock_conn, "https://missing.com"))

    def test_insert_api_entry_google_author(self):
        conn = MagicMock()
        auditor.insert_api_entry(conn, "chrome.tabs.create")
        conn.cursor().execute.assert_called_with(
            "INSERT INTO API (api_url, author) VALUES (?, ?)", ("chrome.tabs.create", "Google")
        )

    def test_insert_api_entry_third_party(self):
        conn = MagicMock()
        auditor.insert_api_entry(conn, "https://api.thirdparty.com")
        conn.cursor().execute.assert_called_with(
            "INSERT INTO API (api_url, author) VALUES (?, ?)", ("https://api.thirdparty.com", "Third Party")
        )

    def test_insert_url_entry(self):
        conn = MagicMock()
        auditor.insert_url_entry(conn, "https://example.com")
        conn.cursor().execute.assert_called()
        conn.commit.assert_called()

    def test_insert_extension_api_inserts(self):
        conn = MagicMock()
        cursor = conn.cursor()
        cursor.fetchone.return_value = None

        auditor.insert_extension_api(conn, 1, 2, "file.js", 10)

        calls = [call[0][0] for call in cursor.execute.call_args_list]
        insert_found = any("INSERT INTO ExtensionAPIs" in sql for sql in calls)
        self.assertTrue(insert_found)

    def test_insert_extension_api_skips_if_exists(self):
        conn = MagicMock()
        cursor = conn.cursor()
        cursor.fetchone.return_value = (1,)

        auditor.insert_extension_api(conn, 1, 2, "file.js", 10)

        calls = [call[0][0] for call in cursor.execute.call_args_list]
        select_found = any("SELECT 1 FROM ExtensionAPIs" in sql for sql in calls)
        insert_found = any("INSERT INTO ExtensionAPIs" in sql for sql in calls)

        self.assertTrue(select_found)
        self.assertFalse(insert_found)

if __name__ == '__main__':
    unittest.main()