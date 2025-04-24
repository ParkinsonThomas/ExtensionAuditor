import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys

# Ensure tool directory is on the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import Extension_Scraper as scraper

class TestExtensionScraper(unittest.TestCase):

    @patch("requests.get")
    def test_download_extension_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"testdata"
        mock_get.return_value = mock_response

        with patch("builtins.open", mock_open()) as m:
            path = scraper.download_extension("abcd1234", "downloads")
            self.assertTrue(path.endswith("abcd1234.crx"))
            m.assert_called_once()

    @patch("zipfile.ZipFile")
    def test_extract_extension(self, mock_zipfile):
        mock_zip = MagicMock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip

        path = scraper.extract_extension("test.crx", "extracted")
        self.assertTrue(path.startswith("extracted"))
        mock_zip.extractall.assert_called_once()

    @patch("builtins.open", new_callable=mock_open, read_data='{"name": "My Extension", "version": "1.0"}')
    def test_parse_manifest(self, mock_file):
        manifest = scraper.parse_manifest("manifest.json")
        self.assertEqual(manifest["name"], "My Extension")
        self.assertEqual(manifest["version"], "1.0")

    def test_extract_author(self):
        from bs4 import BeautifulSoup
        html = "<div class='Fm8Cnb'>DevName</div>"
        soup = BeautifulSoup(html, "html.parser")
        author = scraper.extract_author(soup)
        self.assertEqual(author, "DevName")

    def test_extract_last_updated(self):
        from bs4 import BeautifulSoup
        html = """
        <li class='ZbWJPd uBIrad'>
          <div></div>
          <div>January 1, 2024</div>
        </li>"""
        soup = BeautifulSoup(html, "html.parser")
        date = scraper.extract_last_updated(soup)
        self.assertEqual(date, "2024-01-01")

    @patch("Extension_Scraper.extension_exists", return_value=True)
    def test_run_scraper_skips_existing(self, mock_exists):
        conn = MagicMock()
        scraper.run_scraper(conn, "abcd1234", "downloads", "extract")
        mock_exists.assert_called_once()

    @patch("requests.get")
    def test_download_extension_failure(self, mock_get):
        mock_get.return_value.status_code = 404
        path = scraper.download_extension("invalid", "downloads")
        self.assertIsNone(path)

    @patch("zipfile.ZipFile")
    def test_extract_extension_zip_failure(self, mock_zipfile):
        mock_zipfile.side_effect = Exception("zip error")
        with self.assertRaises(Exception):
            scraper.extract_extension("corrupt.crx", "output")

    def test_scrape_extension_data_missing_fields(self):
        from bs4 import BeautifulSoup
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = str(soup)
            result = scraper.scrape_extension_data("abcd1234")
            self.assertEqual(result["name"], "Unknown")
            self.assertEqual(result["author"], "Unknown")

    def test_insert_extension_data(self):
        conn = MagicMock()
        manifest = {
            "name": "TestExt",
            "version": "1.0",
            "author": "Dev",
            "homepage_url": "https://example.com",
            "last_updated": "2024-01-01"
        }
        scraper.insert_extension_data(conn, "guid123", manifest, "/path")
        conn.cursor().execute.assert_called()

if __name__ == '__main__':
    unittest.main()