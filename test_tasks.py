"""Tests for the task manager's storage layer and input parser.

Run with:  python3 -m unittest test_tasks

Or with verbose output:  python3 -m unittest test_tasks -v

Tests use a temp file DB (not :memory:) because the storage functions open a
new connection per operation. With :memory:, each connection would get a fresh
database and data wouldn't persist across calls within a single test. A temp
file persists across connections within the same test, then is deleted in
tearDown so tests don't accumulate state.
"""
import os
import sqlite3
import tempfile
import unittest

import tasks
from tasks import (
    add_task,
    complete_task,
    delete_task,
    list_tasks,
    parse_task_input,
)


class TestStorageLayer(unittest.TestCase):
    """Tests for the SQLite-backed storage functions.

    Each test runs against a fresh temp DB file. The _DB_PATH_OVERRIDE module
    attribute on tasks is the override hook; production code leaves it as None
    and uses the real XDG path.
    """

    def setUp(self):
        # Create a fresh temp file path. NamedTemporaryFile with delete=False
        # because we want to close it before SQLite opens it (some platforms
        # complain about concurrent access on an open file handle).
        self.tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.tmpfile.close()
        # Wipe any contents so each test starts from an empty file. If the
        # file already had a tasks table from a previous test run that didn't
        # clean up, init_db's IF NOT EXISTS would skip table creation and
        # we'd see stale data.
        os.unlink(self.tmpfile.name)
        tasks._DB_PATH_OVERRIDE = self.tmpfile.name

    def tearDown(self):
        tasks._DB_PATH_OVERRIDE = None
        if os.path.exists(self.tmpfile.name):
            os.unlink(self.tmpfile.name)

    @staticmethod
    def _make_task(title="test", priority=1, due="2026-01-01"):
        """Build a parsed-task dict directly, bypassing parse_task_input.

        Storage tests should isolate the storage layer from the parser. If a
        storage test used parse_task_input, a parser bug could mask a storage
        bug or vice versa.
        """
        return {
            "title": title,
            "priority": priority,
            "due": due,
            "created_at": "2026-01-01 12:00",
            "done": 0,
        }

    def test_add_task_returns_int_id(self):
        new_id = add_task(self._make_task())
        self.assertIsInstance(new_id, int)
        self.assertGreaterEqual(new_id, 1)

    def test_add_task_persists_row(self):
        new_id = add_task(self._make_task(title="persisted"))
        rows = list_tasks()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], new_id)
        self.assertEqual(rows[0]["title"], "persisted")

    def test_add_task_invalid_priority_raises_integrity_error(self):
        # The CHECK constraint at the DB level should reject priority=99.
        # This bypasses parse_task_input (which would also reject 99) so we
        # are testing the database constraint, not the parser.
        with self.assertRaises(sqlite3.IntegrityError):
            add_task(self._make_task(priority=99))

    def test_delete_task_existing_returns_dict_and_removes_row(self):
        new_id = add_task(self._make_task(title="to-delete"))
        deleted = delete_task(new_id)
        self.assertIsNotNone(deleted)
        self.assertEqual(deleted["title"], "to-delete")
        self.assertEqual(list_tasks(), [])

    def test_delete_task_nonexistent_returns_none(self):
        self.assertIsNone(delete_task(999))

    def test_complete_task_existing_returns_dict_with_done_1(self):
        new_id = add_task(self._make_task(title="to-complete"))
        completed = complete_task(new_id)
        self.assertIsNotNone(completed)
        self.assertEqual(completed["done"], 1)
        # Verify the change persisted (not just returned)
        rows = list_tasks()
        self.assertEqual(rows[0]["done"], 1)

    def test_complete_task_nonexistent_returns_none(self):
        self.assertIsNone(complete_task(999))

    def test_list_tasks_returns_ordered_by_id(self):
        id1 = add_task(self._make_task(title="first"))
        id2 = add_task(self._make_task(title="second"))
        id3 = add_task(self._make_task(title="third"))
        rows = list_tasks()
        self.assertEqual([r["id"] for r in rows], [id1, id2, id3])

    def test_list_tasks_empty_db_returns_empty_list(self):
        # init_db has never been called on this fresh temp file. list_tasks
        # calls init_db internally (self-healing), then queries. Should
        # return [] without raising.
        self.assertEqual(list_tasks(), [])


class TestParseTaskInput(unittest.TestCase):
    """Tests for parse_task_input. These don't touch the DB."""

    def test_valid_input_returns_dict_with_int_priority(self):
        result = parse_task_input("test task, 3, 2026-01-01")
        self.assertIsNotNone(result)
        self.assertEqual(result["title"], "test task")
        self.assertEqual(result["priority"], 3)
        self.assertIsInstance(result["priority"], int)
        self.assertEqual(result["due"], "2026-01-01")
        self.assertEqual(result["done"], 0)

    def test_valid_input_with_time(self):
        result = parse_task_input("test, 1, 2026-01-01 18:00")
        self.assertIsNotNone(result)
        self.assertEqual(result["due"], "2026-01-01 18:00")

    def test_too_few_fields_returns_none(self):
        self.assertIsNone(parse_task_input("only, two"))

    def test_too_many_fields_returns_none(self):
        self.assertIsNone(parse_task_input("a, b, c, d"))

    def test_empty_title_returns_none(self):
        self.assertIsNone(parse_task_input(" , 1, 2026-01-01"))

    def test_invalid_priority_returns_none(self):
        self.assertIsNone(parse_task_input("test, 6, 2026-01-01"))
        self.assertIsNone(parse_task_input("test, abc, 2026-01-01"))

    def test_invalid_due_returns_none(self):
        self.assertIsNone(parse_task_input("test, 1, not-a-date"))


if __name__ == "__main__":
    unittest.main()
