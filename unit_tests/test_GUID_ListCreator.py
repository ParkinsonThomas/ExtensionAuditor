import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import GUID_ListCreator as guid_creator

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestGUIDListCreator(unittest.TestCase):

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", return_value=False)
    def test_save_to_file_creates_new_file(self, mock_exists, mock_file):
        guids = ["abc123", "def456"]
        guid_creator.save_to_file(guids, "https://test.url")
        mock_file().write.assert_any_call("abc123\n")
        mock_file().write.assert_any_call("def456\n")
        mock_file.assert_called_once_with("GUID_List.txt", "w")

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", return_value=True)
    def test_save_to_file_appends_if_exists(self, mock_exists, mock_file):
        guids = ["xyz789"]
        guid_creator.save_to_file(guids, "https://test.url")
        mock_file.assert_called_once_with("GUID_List.txt", "a")
        mock_file().write.assert_called_once_with("xyz789\n")

    @patch("GUID_ListCreator.webdriver.Chrome")
    @patch("GUID_ListCreator.ChromeDriverManager.install", return_value="/mocked/path")
    @patch("GUID_ListCreator.WebDriverWait")
    def test_get_extension_guids_successful(self, mock_wait, mock_install, mock_chrome):
        mock_driver = MagicMock()
        mock_driver.page_source = """
        <div data-item-id="ext1"></div>
        <div data-item-id="ext2"></div>
        """
        mock_chrome.return_value = mock_driver

        mock_wait().until.side_effect = Exception("Timeout")  # simulate no load-more click

        guids = guid_creator.get_extension_guids("http://test-url")
        self.assertEqual(set(guids), {"ext1", "ext2"})
        mock_driver.quit.assert_called_once()

    @patch("GUID_ListCreator.webdriver.Chrome", side_effect=Exception("browser crash"))
    def test_get_extension_guids_handles_exception(self, mock_browser):
        result = guid_creator.get_extension_guids("http://invalid-url")
        self.assertEqual(result, [])

    @patch("GUID_ListCreator.get_extension_guids", return_value=["id1", "id2"])
    @patch("GUID_ListCreator.save_to_file")
    def test_main_processes_all_categories(self, mock_save, mock_get):
        mock_config = {}
        guid_creator.main(mock_config)
        self.assertTrue(mock_get.call_count > 1)
        mock_save.assert_called()

    @patch("GUID_ListCreator.get_extension_guids", return_value=[])
    @patch("GUID_ListCreator.save_to_file")
    def test_main_handles_empty_guids(self, mock_save, mock_get):
        mock_config = {}
        guid_creator.main(mock_config)
        mock_save.assert_not_called()


if __name__ == '__main__':
    unittest.main()