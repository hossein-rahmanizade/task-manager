# task-manager

A small CLI task manager backed by SQLite. Add, list, complete, and delete tasks via flags or an interactive menu.

## Requirements

- Python 3.10+ (uses `dict | None` union syntax)
- SQLite (bundled with Python's standard library, no separate install)

No third-party dependencies.

## Install

```
git clone https://github.com/<your-username>/task-manager.git
cd task-manager
```

No `pip install` step needed — only stdlib imports.

## Usage

### CLI flags

```
python3 tasks.py -a "buy milk, 1, 2026-11-10"
python3 tasks.py -v
python3 tasks.py -x 1        # complete task #1
python3 tasks.py -d 1        # delete task #1
```

| Flag | Long form     | Argument            | Action          |
|------|---------------|---------------------|-----------------|
| `-a` | `--add`       | `"title, priority, due"` | Add a task |
| `-v` | `--view`      | (none)              | List all tasks  |
| `-x` | `--complete`  | task id (int)       | Mark done       |
| `-d` | `--delete`    | task id (int)       | Delete task     |

Task input format: `"title, priority, due"` in double quotes, comma-separated.
- `priority`: integer 1–5
- `due`: `YYYY-MM-DD` or `YYYY-MM-DD HH:MM`

### Interactive mode

Run with no flags:

```
python3 tasks.py
```

Renders a menu:

```
================================
        CLI TASK MANAGER
================================
        [1] Add new task
        [2] Delete task
        [3] View all tasks
        [4] Complete task
        [5] Exit
================================
Choose option 1-5:
```

## Database location

Following the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/):

```
~/.local/share/taskmanager/tasks.db
```

The directory and the database file are created automatically on first use. The location is determined by `get_db_path()` in `tasks.py`.

## Schema

```sql
CREATE TABLE tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT    NOT NULL,
    priority   INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 5),
    due        TEXT    NOT NULL,
    created_at TEXT    NOT NULL,
    done       INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1))
);
```

- `id`: monotonic; gaps appear after deletes (see Known Limitations).
- `priority`: integer with a CHECK constraint enforcing range at the database level.
- `due`: ISO 8601 text (`YYYY-MM-DD` or `YYYY-MM-DD HH:MM`). Sortable lexicographically.
- `created_at`: ISO 8601 text, set at task creation.
- `done`: integer 0/1. SQLite has no native BOOLEAN type.

Inspect the database directly:

```
sqlite3 ~/.local/share/taskmanager/tasks.db
sqlite> .schema
sqlite> SELECT * FROM tasks;
```

## Testing

```
python3 -m unittest test_tasks
```

Verbose:

```
python3 -m unittest test_tasks -v
```

Tests use a temp file DB per test case (not `:memory:`) because each storage function opens its own connection; an in-memory DB would be lost between calls within a single test. See `test_tasks.py`'s module docstring for the rationale.

## Project structure

Single-file application:

- `tasks.py` — the application
  - Argument parser (CLI flags)
  - ANSI color constants
  - `parse_task_input` — input validation, returns `dict | None`
  - `get_db_path`, `init_db` — DB location and schema setup
  - `add_task`, `delete_task`, `complete_task`, `list_tasks` — storage layer (pure data; no printing)
  - `_print_tasks` — presentation helper
  - `interactive_mode`, `main` — CLI handlers (own all user-facing messages)
- `test_tasks.py` — unit tests

## Design

**Separation of concerns.** Storage functions return data or raise. Presentation functions format. CLI handlers own user-facing messages. No storage function prints.

**Parameterized SQL.** All queries use `?` placeholders. User input is never interpolated into SQL strings. See [OWASP SQL Injection](https://owasp.org/www-community/attacks/SQL_Injection).

**Self-healing storage.** Each storage function calls `init_db()` before operating, so the database and table are created on first use without an explicit setup step.

## Known Limitations

- **`import-json` command dropped.** The original project spec required a one-time JSON import command. Inspection confirmed no real data existed at `/tmp/tasks.json` to migrate, so the command was dropped to avoid implementing dead code. Spec deviation documented here.
- **Monotonic ids with gaps.** `AUTOINCREMENT` ensures ids are never reused after deletion, so gaps appear in the id sequence. By design — reusing ids could cause stale references to point to new tasks.
- **Color codes are emitted even when stdout is piped.** No `sys.stdout.isatty()` check. Piping `tasks.py -v | less` will show raw ANSI escape codes. Fix is to check `isatty()` before applying color; deferred.
- **No handling for database corruption or permission errors.** If the DB file becomes corrupt, or if `~/.local/share/taskmanager/` is not writable, the program will raise an unhandled `sqlite3` exception. No recovery or user-friendly message.
- **Completing an already-completed task reports success.** `complete_task` returns the task dict on both first-completion and re-completion. The caller cannot distinguish "newly completed" from "already complete." Distinct feedback would require either a separate sentinel return type or an exception.
- **Single-process; no concurrent-write handling.** SQLite uses file-level locking. Two terminals running `tasks.py -a ...` simultaneously may conflict at the lock level. SQLite will raise `sqlite3.OperationalError: database is locked` after a timeout. No retry logic.
- **No edit operation.** The original spec listed "Edit task" as out of scope; this remains the case.

## Later

Deliberately postponed features. Each is a reasonable enhancement but was kept out of scope to maintain the project's time budget.

- **Edit existing tasks.** Modify title, priority, or due date of a stored task.
- **Filter and search.** List tasks by priority, due-date range, or completion status.
- **Natural-language date input.** Accept "next Wednesday", "in two weeks", "Nov 11", etc. Probably via `python-dateutil` or `parsedatetime`. Adds an external dependency.
- **`completed_at` timestamp.** Currently `done` is a boolean 0/1. Replacing or supplementing with a `completed_at TIMESTAMP NULL` would record when a task was finished, not just whether.
- **argparse subcommands.** Replace flags (`-a`, `-v`, `-d`, `-x`) with subcommands (`add`, `list`, `complete`, `delete`). More idiomatic for CLIs with multiple operations.
- **`NO_COLOR` environment variable support.** Disable ANSI codes when the env var is set, per the [no-color spec](https://no-color.org/).
- **`isatty()` check.** Detect non-terminal stdout and skip color codes.
- **Pagination.** For task lists exceeding terminal height. Probably `less` integration or paged output.
- **Tag / category system.** Multi-table schema (tasks, tags, task_tags). Substantial scope expansion; would re-introduce the relational-design complexity this project deliberately avoided.
- **CLI handler tests.** Current tests cover storage and parser. CLI argument parsing and interactive mode are not tested.
- **Atomicity for `import-json` (if reintroduced).** If a JSON import command is ever added back, it should run inside a single transaction so partial failures don't leave a half-imported database.

## Project history

This project began as a JSON-backed CLI task manager written as a return-to-programming exercise after a long break. The JSON implementation is preserved at git tag `v0.1-json-final` and on the `main` branch.

The `sqlite` branch replaces JSON persistence with SQLite and refactors the storage layer for cleaner separation of concerns. See `git log` for the step-by-step refactor and migration commits.
