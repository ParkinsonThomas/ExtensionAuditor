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

    @patch("API_Auditor.insert_url_entry")
    @patch("API_Auditor.insert_api_entry")
    @patch("API_Auditor.get_api_entry", return_value=None)
    @patch("API_Auditor.get_url_entry", return_value=False)
    @patch("API_Auditor.client.chat.completions.create")
    def test_audit_api_links_valid_response(self, mock_llm, mock_url_check, mock_api_check, mock_insert_api, mock_insert_url):
        mock_conn = MagicMock()
        mock_llm.return_value.choices[0].message.content = json.dumps(["https://api.valid.com"])

        usage = [("https://api.valid.com", "file.js", 10), ("https://api.fake.com", "file.js", 12)]
        mock_url_check.side_effect = [False, False]
        mock_api_check.side_effect = [None, None]

        result = auditor.audit_api_links(usage, mock_conn)

        self.assertIn("https://api.valid.com", result)
        self.assertNotIn("https://api.fake.com", result)
        self.assertTrue(mock_insert_api.called or mock_insert_url.called)

    @patch("API_Auditor.client.chat.completions.create")
    def test_audit_api_links_invalid_json(self, mock_llm):
        mock_llm.return_value.choices[0].message.content = "not valid json"

        usage = [("https://broken.com", "file.js", 8)]
        mock_conn = MagicMock()

        with patch("API_Auditor.get_url_entry", return_value=False), \
             patch("API_Auditor.get_api_entry", return_value=None), \
             patch("API_Auditor.insert_url_entry"), \
             patch("API_Auditor.insert_api_entry"):
            result = auditor.audit_api_links(usage, mock_conn)
            self.assertEqual(result, [])

    @patch("API_Auditor.find_api_usage")
    @patch("API_Auditor.audit_api_links")
    @patch("API_Auditor.insert_extension_api")
    @patch("API_Auditor.get_api_entry", return_value=None)
    @patch("API_Auditor.insert_api_entry")
    def test_analyse_extension_executes_pipeline(self, mock_insert_api, mock_get_api, mock_insert_link, mock_audit, mock_find):
        mock_conn = MagicMock()
        mock_find.side_effect = [[("https://api.valid.com", "f.js", 2)], []]
        mock_audit.return_value = ["https://api.valid.com"]

        with patch("os.walk") as mock_walk:
            mock_walk.return_value = [
                ("/x", [], ["a.js", "b.js"])
            ]
            auditor.analyse_extension(1, "/x", mock_conn)

        mock_find.assert_called()
        mock_audit.assert_called_once()
        mock_insert_api.assert_called()
        mock_insert_link.assert_called()

    @patch("API_Auditor.analyse_extension")
    @patch("API_Auditor.get_extensions_to_analyse")
    @patch("API_Auditor.init_db_connection")
    def test_main_executes_end_to_end(self, mock_db, mock_get_exts, mock_analyse):
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn
        mock_get_exts.return_value = [(1, "abc"), (2, "missing")]
        config = {
            "database": {"db": ":memory:"},
            "storage": {"extract_path": "/mock"}
        }

        with patch("os.path.exists", side_effect=lambda path: "abc" in path):
            auditor.main(config)

        mock_analyse.assert_called_once_with(1, "/mock/abc", mock_conn)

if __name__ == '__main__':
    unittest.main()