import unittest
from unittest.mock import patch, MagicMock
import subprocess
import multiprocessing
import os
import sys
import sqlite3
import queue
import Extension_Analysis_Babel as babel

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestBabelAnalysis(unittest.TestCase):

    @patch("subprocess.run")
    def test_analyse_js_file_returns_result(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"eval_usage": 2, "document_write": 1}'
        result = babel.analyse_js_file("dummy.js")
        self.assertEqual(result, {"eval_usage": 2, "document_write": 1})

    @patch("subprocess.run")
    def test_analyse_js_file_returns_none_on_failure(self, mock_run):
        mock_run.return_value.returncode = 1
        result = babel.analyse_js_file("dummy.js")
        self.assertIsNone(result)

    @patch("os.walk")
    @patch("os.path.getsize", return_value=250)
    def test_collect_js_files_finds_all_js(self, mock_size, mock_walk):
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

    @patch("Extension_Analysis_Babel.analyse_js_file")
    @patch("Extension_Analysis_Babel.collect_js_files")
    @patch("os.path.join", side_effect=lambda *args: "/".join(args))
    def test_analyse_extensions_sends_to_queues(self, mock_join, mock_collect, mock_analyse):
        mock_collect.return_value = ["file1.js", "file2.js"]
        mock_analyse.side_effect = [
            {"eval_usage": 1},
            {"document_write": 2}
        ]

        queue_mock = MagicMock()
        ext_counter_mock = MagicMock()
        file_counter_mock = MagicMock()

        rule_map = {
            "eval_usage": 1,
            "document_write": 2
        }

        babel.analyse_extensions("/mocked", 5, "guid", rule_map, queue_mock, ext_counter_mock, file_counter_mock)

        queue_mock.put.assert_called_once()
        ext_counter_mock.put.assert_called_once_with("success")
        self.assertEqual(file_counter_mock.put.call_count, 2)

    def test_insert_data_inserts_correctly(self):
        findings_queue = multiprocessing.Queue()
        findings_queue.put([
            (1, 101, "/path/file1.js", 3),
            (2, 102, "/path/file2.js", 5)
        ])
        findings_queue.put("FINISHED")

        mock_conn = MagicMock()
        mock_cursor = mock_conn.cursor.return_value

        with patch("Extension_Analysis_Babel.init_db_connection", return_value=mock_conn):
            babel.insert_data("mocked.db", findings_queue)

        expected_calls = [
            ((
                "INSERT INTO ExtensionAnalysisJS (extension_id, rule_id, file_name, count) VALUES (?, ?, ?, ?)",
                (1, 101, "/path/file1.js", 3)
            ),),
            ((
                "INSERT INTO ExtensionAnalysisJS (extension_id, rule_id, file_name, count) VALUES (?, ?, ?, ?)",
                (2, 102, "/path/file2.js", 5)
            ),)
        ]

        self.assertEqual(mock_cursor.execute.call_args_list, expected_calls)
        mock_conn.commit.assert_called()
        mock_conn.close.assert_called()

    def test_get_extensions_to_analyse_returns_expected(self):
        conn = MagicMock()
        conn.cursor.return_value.fetchall.return_value = [(1, "abc"), (2, "xyz")]
        result = babel.get_extensions_to_analyse(conn)
        self.assertEqual(result, [(1, "abc"), (2, "xyz")])

    @patch("sys.stdout.write")
    def test_status_updater_outputs_progress(self, mock_write):
        ext_q = multiprocessing.Queue()
        file_q = multiprocessing.Queue()

        ext_q.put("success")
        file_q.put("success")
        file_q.put("fail")

        # Run in a thread to avoid blocking main test thread
        updater = multiprocessing.Process(
            target=babel.status_updater,
            args=(ext_q, file_q, 1)
        )
        updater.start()
        updater.join(timeout=3)

        self.assertFalse(updater.exitcode)

    @patch("Extension_Analysis_Babel.analyse_extensions")
    @patch("Extension_Analysis_Babel.status_updater")
    @patch("Extension_Analysis_Babel.insert_data")
    @patch("Extension_Analysis_Babel.get_extensions_to_analyse")
    @patch("Extension_Analysis_Babel.init_analysis_rules")
    @patch("Extension_Analysis_Babel.init_db_connection")
    def test_main_runs_pipeline_successfully(
        self, mock_db_conn, mock_init_rules, mock_get_exts, mock_insert, mock_status, mock_analyse
    ):
        mock_conn = MagicMock()
        mock_cursor = mock_conn.cursor.return_value
        mock_cursor.fetchall.return_value = [(1, "eval_usage"), (2, "document_write")]
        mock_db_conn.return_value = mock_conn
        mock_get_exts.return_value = [(1, "abc123"), (2, "xyz456")]

        config = {
            "database": {"db": ":memory:"},
            "storage": {"extract_path": "/mock/path"},
        }

        babel.main(config)

        mock_init_rules.assert_called_once()
        mock_get_exts.assert_called_once()
        self.assertEqual(mock_analyse.call_count, 2)
        mock_insert.assert_called()
        mock_status.assert_called()

    def test_init_analysis_rules_inserts_missing_rules(self):
        mock_conn = MagicMock()
        mock_cursor = mock_conn.cursor.return_value
        # Simulate rule not found in DB
        mock_cursor.fetchone.side_effect = [None] * 8  # all 8 rules missing

        babel.init_analysis_rules(mock_conn)

        self.assertEqual(mock_cursor.execute.call_count, 16)  # 8 SELECT + 8 INSERT
        mock_conn.commit.assert_called_once()

    def test_insert_data_closes_connection_on_finish(self):
        queue = multiprocessing.Queue()
        queue.put("FINISHED")

        mock_conn = MagicMock()
        with patch("Extension_Analysis_Babel.init_db_connection", return_value=mock_conn):
            babel.insert_data("mock.db", queue)

        mock_conn.close.assert_called_once()

    @patch("sys.stdout.write")
    def test_status_updater_outputs_correctly(self, mock_write):
        ext_q = multiprocessing.Queue()
        file_q = multiprocessing.Queue()

        ext_q.put("success")
        file_q.put("success")
        file_q.put("fail")

        process = multiprocessing.Process(
            target=babel.status_updater,
            args=(ext_q, file_q, 1)
        )
        process.start()
        process.join(timeout=3)

        self.assertFalse(process.exitcode)

if __name__ == '__main__':
    unittest.main()