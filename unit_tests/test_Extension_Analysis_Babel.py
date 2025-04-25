import unittest
from unittest.mock import patch, MagicMock
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import Extension_Analysis_Babel as babel

class TestBabelAnalysis(unittest.TestCase):

    @patch("subprocess.run")
    def test_analyse_js_file_returns_result(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"eval": 2, "document.write": 1}'
        result = babel.analyse_js_file("dummy.js")
        self.assertEqual(result, {"eval": 2, "document.write": 1})

    @patch("subprocess.run")
    def test_analyse_js_file_returns_none_on_failure(self, mock_run):
        mock_run.return_value.returncode = 1
        result = babel.analyse_js_file("dummy.js")
        self.assertIsNone(result)

    @patch("os.walk")
    def test_collect_js_files_finds_all_js(self, mock_walk):
        mock_walk.return_value = [
            ("/some/path", [], ["a.js", "b.txt", "c.js"]),
            ("/some/path/inner", [], ["d.js"])
        ]
        result = babel.collect_js_files("/some/path")
        self.assertEqual(set(result), {
            "/some/path/a.js",
            "/some/path/c.js",
            "/some/path/inner/d.js"
        })

    @patch("os.path.isdir", return_value=True)
    @patch("Extension_Analysis_Babel.collect_js_files")
    @patch("Extension_Analysis_Babel.analyse_js_file")
    def test_analyse_extensions_runs_analysis(self, mock_analyse, mock_collect, mock_isdir):
        # arrange
        mock_collect.return_value = ["a.js", "b.js"]
        mock_analyse.side_effect = [
            {"eval": 2},
            {"document.write": 1, "eval": 1}
        ]
        conn = MagicMock()
        extensions = [(1, "ext-guid")]

        # act
        with patch("os.path.join", side_effect=lambda *parts: "/".join(parts)):
            babel.analyse_extensions(conn, "/extracted", extensions)

        # assert
        self.assertEqual(mock_analyse.call_count, 2)

    def test_get_extensions_to_analyse_returns_expected(self):
        conn = MagicMock()
        # simulate cursor.execute + fetchall
        curs = conn.cursor.return_value
        curs.fetchall.return_value = [(1, "abc"), (2, "xyz")]

        result = babel.get_extensions_to_analyse(conn)
        self.assertEqual(result, [(1, "abc"), (2, "xyz")])

if __name__ == '__main__':
    unittest.main()