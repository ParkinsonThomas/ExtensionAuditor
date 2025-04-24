import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys

# Add the parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import GUID_ListCreator as guid_creator

class TestGUIDListCreator(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", return_value=False)
    def test_save_to_file_creates_file(self, mock_exists, mock_file):
        guids = ["abc123", "def456"]
        guid_creator.save_to_file(guids, "https://test.url")
        mock_file().write.assert_any_call("abc123\n")
        mock_file().write.assert_any_call("def456\n")

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", return_value=True)
    def test_save_to_file_appends(self, mock_exists, mock_file):
        guids = ["xyz789"]
        guid_creator.save_to_file(guids, "https://test.url")
        mock_file.assert_called_once_with("GUID_List.txt", "a")

    @patch("selenium.webdriver.Chrome")
    @patch("webdriver_manager.chrome.ChromeDriverManager.install")
    def test_get_extension_guids_mocked_browser(self, mock_install, mock_chrome):
        mock_driver = MagicMock()
        mock_driver.page_source = """
        <div data-item-id="ext1"></div>
        <div data-item-id="ext2"></div>
        """
        mock_chrome.return_value = mock_driver

        guids = guid_creator.get_extension_guids("http://test-url", 10)
        self.assertIn("ext1", guids)
        self.assertIn("ext2", guids)

    def test_get_extension_guids_returns_empty_on_failure(self):
        with patch("selenium.webdriver.Chrome", side_effect=Exception("browser crash")):
            guids = guid_creator.get_extension_guids("http://bad-url", 10)
            self.assertEqual(guids, [])

if __name__ == '__main__':
    unittest.main()