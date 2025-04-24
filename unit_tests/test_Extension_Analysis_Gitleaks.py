import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import subprocess

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import Extension_Analysis_Gitleaks as gitleaks

class TestGitleaksAnalysis(unittest.TestCase):

    def test_insert_data_executes_insert(self):
        conn = MagicMock()
        gitleaks.insert_data(conn, 1, "SECRET", "rule123", 5.5, "file.js", 42)
        conn.cursor().execute.assert_called_once()
        conn.commit.assert_called_once()

    @patch("os.path.join", return_value="/mocked/path")
    @patch("subprocess.run")
    def test_analyse_files_runs_gitleaks(self, mock_run, mock_path):
        mock_result = MagicMock()
        mock_result.stdout = """
        Secret: TESTKEY123
        RuleID: aws-secret
        File: file.js
        Entropy: 5.8
        Line: 23
        """
        mock_run.return_value = mock_result

        conn = MagicMock()
        gitleaks.analyse_files(conn, "/extract", "guid123", 1, 5.0)

        conn.cursor().execute.assert_called()
        conn.commit.assert_called()

    @patch("subprocess.run")
    def test_analyse_files_no_findings(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        conn = MagicMock()
        findings = gitleaks.analyse_files(conn, "/path", "guid", 1, 3.5)
        self.assertEqual(findings, [])

    @patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "gitleaks"))
    def test_analyse_files_gitleaks_crash(self, mock_run):
        conn = MagicMock()
        findings = gitleaks.analyse_files(conn, "/path", "guid", 1, 3.5)
        self.assertEqual(findings, [])

    @patch("time.time", side_effect=[100.0, 105.5])
    @patch("Extension_Analysis_Gitleaks.analyse_files")
    def test_analyse_extensions_timing_and_loop(self, mock_analyse, mock_time):
        conn = MagicMock()
        extensions = [(1, "guid1"), (2, "guid2")]
        mock_analyse.side_effect = [[], []]

        gitleaks.analyse_extensions(conn, "/mocked", extensions, 4.0)
        self.assertEqual(mock_analyse.call_count, 2)

if __name__ == '__main__':
    unittest.main()