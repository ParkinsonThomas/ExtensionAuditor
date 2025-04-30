import unittest
from unittest.mock import patch, MagicMock, call
import subprocess
import multiprocessing
import queue
import sys
import os
import sqlite3
import Extension_Analysis_Gitleaks as gitleaks

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestGitleaksAnalysis(unittest.TestCase):

    @patch("os.path.join", return_value="/mocked/path/guid123")
    @patch("subprocess.run")
    def test_analyse_files_with_findings(self, mock_run, mock_path):
        mock_result = MagicMock()
        mock_result.stdout = (
            "Secret: TESTKEY123\n"
            "RuleID: aws-secret\n"
            "File: file.js\n"
            "Entropy: 5.8\n"
            "Line: 23\n"
        )
        mock_run.return_value = mock_result

        finding_queue = MagicMock()
        counter_queue = MagicMock()

        gitleaks.analyse_files(finding_queue, "/mocked/path", "guid123", 1, 5.0, counter_queue)

        finding_queue.put.assert_called_once_with([
            (1, "file.js", "23", "aws-secret", "TESTKEY123", 5.8)
        ])
        counter_queue.put.assert_called_once_with("success")

    @patch("os.path.join", return_value="/mocked/path/guid123")
    @patch("subprocess.run")
    def test_analyse_files_below_entropy(self, mock_run, mock_path):
        mock_result = MagicMock()
        mock_result.stdout = (
            "Secret: LOWENTROPYKEY\n"
            "RuleID: some-rule\n"
            "File: file.js\n"
            "Entropy: 2.1\n"
            "Line: 10\n"
        )
        mock_run.return_value = mock_result

        finding_queue = MagicMock()
        counter_queue = MagicMock()

        gitleaks.analyse_files(finding_queue, "/mocked/path", "guid123", 1, 4.0, counter_queue)

        finding_queue.put.assert_called_once_with([])
        counter_queue.put.assert_called_once_with("success")

    @patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "gitleaks"))
    def test_analyse_files_gitleaks_crash(self, mock_run):
        finding_queue = MagicMock()
        counter_queue = MagicMock()

        gitleaks.analyse_files(finding_queue, "/mocked", "guid", 1, 3.5, counter_queue)
        finding_queue.put.assert_not_called()
        counter_queue.put.assert_called_once_with("fail")

    def test_insert_data_processes_findings(self):
        db_mock = MagicMock()
        db_path = ":memory:"
        findings_queue = multiprocessing.Queue()

        findings_queue.put([
            (1, "file.js", "23", "rule123", "SECRET", 5.5)
        ])
        findings_queue.put("FINISHED")

        with patch("Extension_Analysis_Gitleaks.init_db_connection", return_value=db_mock):
            gitleaks.insert_data(db_path, findings_queue)

        db_mock.cursor().execute.assert_called_once()
        db_mock.commit.assert_called()
        db_mock.close.assert_called()

    def test_init_db_connection_creates_sqlite_connection(self):
        conn = gitleaks.init_db_connection(":memory:")
        self.assertIsInstance(conn, sqlite3.Connection)
        conn.close()

    def test_get_extensions_to_analyse_returns_data(self):
        mock_conn = MagicMock()
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = [(1, "guid1"), (2, "guid2")]

        results = gitleaks.get_extensions_to_analyse(mock_conn)
        self.assertEqual(results, [(1, "guid1"), (2, "guid2")])
        mock_cursor.execute.assert_called_once_with("SELECT extension_id, extension_guid FROM Extension")

    def test_status_updater_outputs_correct_counts(self):
        status_q = multiprocessing.Queue()
        for status in ["success", "fail", "success"]:
            status_q.put(status)

        with patch("sys.stdout.write") as mock_write:
            gitleaks.status_updater(status_q, 3)

        calls = [call("\033[F\033[K" * 2),
                 call("Extensions analysed successfully:    1\n"),
                 call("Extensions analysed unsuccessfully:  0\n"),
                 call("\033[F\033[K" * 2),
                 call("Extensions analysed successfully:    1\n"),
                 call("Extensions analysed unsuccessfully:  1\n"),
                 call("\033[F\033[K" * 2),
                 call("Extensions analysed successfully:    2\n"),
                 call("Extensions analysed unsuccessfully:  1\n")]
        mock_write.assert_has_calls(calls, any_order=False)

    @patch("Extension_Analysis_Gitleaks.analyse_files")
    @patch("Extension_Analysis_Gitleaks.status_updater")
    @patch("Extension_Analysis_Gitleaks.insert_data")
    @patch("Extension_Analysis_Gitleaks.get_extensions_to_analyse")
    @patch("Extension_Analysis_Gitleaks.init_db_connection")
    def test_main_runs_with_mocked_dependencies(self, mock_db, mock_get_exts, mock_insert, mock_status, mock_analyse):
        # Simulate database returning two extensions
        mock_get_exts.return_value = [(1, "guid1"), (2, "guid2")]

        config = {
            "database": {"db": ":memory:"},
            "storage": {"extract_path": "/mock/extracted"},
            "entropy_filtering": {
                "enabled": True,
                "entropy_filter": 4.5
            }
        }

        gitleaks.main(config)

        mock_get_exts.assert_called_once()
        mock_insert.assert_called()
        mock_status.assert_called_once()
        self.assertEqual(mock_analyse.call_count, 2)
        
if __name__ == '__main__':
    unittest.main()