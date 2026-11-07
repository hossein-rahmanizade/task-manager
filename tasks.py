import argparse
from datetime import datetime
import os
import re
import sys
import sqlite3


# ANSI escape codes for terminal output. Terminals interpret these as styling
# instructions, not as visible characters. RESET must follow any styled segment,
# otherwise the style bleeds into subsequent output.
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"


# Tests can set this to a temp file path to avoid touching the real DB.
# Production code leaves it as None, and get_db_path() uses the real XDG path.
_DB_PATH_OVERRIDE: str | None = None


cmd_parser = argparse.ArgumentParser()
cmd_parser.add_argument("-a", "--add", help="Add task: \"title, priority, due\".")
cmd_parser.add_argument("-v", "--view", action="store_true", help="View tasks")
cmd_parser.add_argument("-d", "--delete", type=int, help="Task id to delete.")
cmd_parser.add_argument("-x", "--complete", type=int, help="Task id to complete.")


def task_options_prints():
    """Render the interactive menu."""
    print(f"""
{CYAN}{BOLD}{'=' * 32}
        CLI TASK MANAGER
{'=' * 32}{RESET}
        [1] Add new task
        [2] Delete task
        [3] View all tasks
        [4] Complete task
        [5] Exit
{CYAN}{'=' * 32}{RESET}""")


def parse_task_input(user_task: str) -> dict | None:
    """Parse a raw 'title, priority, due' string into a task dict.

    Returns a dict with keys {title, priority, due, created_at, done} on success,
    or None on validation failure (with the error message printed).
    """
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    user_task_split = re.split(r'\s*,\s*', user_task)
    if len(user_task_split) != 3:
        print(f"{RED}X You have to enter all three task requirements{RESET}")
        return None
    user_task_keys = ["title", "priority", "due"]
    result = dict(zip(user_task_keys, user_task_split))
    if not result['title'] or not result['title'].strip():
        print(f"{RED}X Title cannot be empty{RESET}")
        return None
    if result['priority'] not in ["1", "2", "3", "4", "5"]:
        print(f"{RED}X Priority must be a number 1-5{RESET}")
        return None
    result["priority"] = int(result["priority"])
    try:
        datetime.strptime(result["due"], "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            datetime.strptime(result["due"], "%Y-%m-%d")
        except ValueError:
            print(f"{RED}X Due date must be 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD'{RESET}")
            return None
    result["created_at"] = created_at
    result["done"] = 0
    return result


def get_db_path() -> str:
    """Return the absolute path to the SQLite database file.

    Returns _DB_PATH_OVERRIDE if set (used by tests); otherwise the XDG path.
    """
    if _DB_PATH_OVERRIDE is not None:
        return _DB_PATH_OVERRIDE
    return os.path.expanduser("~/.local/share/taskmanager/tasks.db")


def init_db() -> None:
    """Create the database directory and tasks table if they don't exist.

    Safe to call multiple times; uses CREATE TABLE IF NOT EXISTS.
    """
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                priority INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 5),
                due TEXT NOT NULL,
                created_at TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0 CHECK (done IN (0, 1))
            )
        """)


def add_task(task: dict) -> int:
    """Insert a parsed task dict into the database and return its assigned id.

    Args:
        task: Dict with keys {title, priority (int), due, created_at, done}.
            Must not include 'id'; one will be assigned by AUTOINCREMENT.

    Returns:
        The integer id assigned to the newly inserted task.
    """
    init_db()
    with sqlite3.connect(get_db_path()) as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, priority, due, created_at, done) "
            "VALUES (?, ?, ?, ?, ?)",
            (task["title"], task["priority"], task["due"], task["created_at"], task["done"])
        )
        return cur.lastrowid


def delete_task(task_id: int) -> dict | None:
    """Delete the task with the given id. Return the deleted task dict, or None if not found."""
    init_db()
    with sqlite3.connect(get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT id, title, priority, due, created_at, done FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return dict(row)


def complete_task(task_id: int) -> dict | None:
    """Mark the task with the given id as done. Return the updated task dict, or None if not found."""
    init_db()
    with sqlite3.connect(get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT id, title, priority, due, created_at, done FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        conn.execute("UPDATE tasks SET done = 1 WHERE id = ?", (task_id,))
        result = dict(row)
        result["done"] = 1
        return result


def list_tasks() -> list[dict]:
    """Return all tasks in the database, ordered by id."""
    init_db()
    with sqlite3.connect(get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, title, priority, due, created_at, done FROM tasks ORDER BY id").fetchall()
        return [dict(row) for row in rows]
    
def _print_tasks(tasks: list[dict]) -> None:
    """Render a list of task dicts to stdout. Empty list prints a 'no tasks' notice."""
    if not tasks:
        print(f"{YELLOW}There are no tasks to view.{RESET}")
        return
    print()
    for task in tasks:
        if task["done"]:
            status = f"{GREEN}[x]{RESET}"
        else:
            status = "[ ]"
        print(f"{status} #{task['id']:>3}. {task['title']} (due: {task['due']}) (priority: {task['priority']})")


def interactive_mode():
    """Run the interactive menu loop until the user chooses to exit."""
    while True:
        task_options_prints()
        choice = input("Choose option 1-5: ")

        if choice == "1":
            raw = input("Enter title, priority, due: ")
            parsed = parse_task_input(raw)
            if parsed is None:
                print(f"{YELLOW}Invalid format. Use: title, priority, due{RESET}")
                continue
            new_id = add_task(parsed)
            print(f"{GREEN}[+]{RESET} Added task #{new_id}: \"{parsed['title']}\" (priority: {parsed['priority']}, due: {parsed['due']})")
        elif choice == "2":
            raw = input("Enter task's id to delete: ")
            try:
                task_id = int(raw)
            except ValueError:
                print(f"{RED}Invalid task id: must be a number{RESET}")
                continue
            deleted = delete_task(task_id)
            if deleted:
                print(f"{GREEN}[-]{RESET} Deleted task #{task_id}: {deleted['title']}")
            else:
                print(f"{YELLOW}No task matched id #{task_id}{RESET}")
        elif choice == "3":
            _print_tasks(list_tasks())
        elif choice == "4":
            raw = input("Enter task's id to complete: ")
            try:
                task_id = int(raw)
            except ValueError:
                print(f"{RED}Invalid task id: must be a number{RESET}")
                continue
            completed = complete_task(task_id)
            if completed:
                print(f"{GREEN}[x]{RESET} Completed task #{task_id}: {completed['title']}")
            else:
                print(f"{YELLOW}No task matched id #{task_id}{RESET}")
        elif choice == "5":
            print("Goodbye")
            break
        else:
            print(f"{RED}Invalid choice{RESET}")


def main():
    """Parse CLI args and dispatch to the appropriate handler.

    With no flags, enters interactive mode. Otherwise executes the requested
    operation(s) and exits.
    """
    args = cmd_parser.parse_args()
    if args.add is not None:
        parsed = parse_task_input(args.add)
        if parsed is None:
            sys.exit(1)
        new_id = add_task(parsed)
        print(f"{GREEN}[+]{RESET} Added task #{new_id}: \"{parsed['title']}\" (priority: {parsed['priority']}, due: {parsed['due']})")
    if args.view:
        _print_tasks(list_tasks())
    if args.delete is not None:
        deleted = delete_task(args.delete)
        if deleted:
            print(f"{GREEN}[-]{RESET} Deleted task #{args.delete}: {deleted['title']}")
        else:
            print(f"{YELLOW}No task matched id #{args.delete}{RESET}")
    if args.complete is not None:
        completed = complete_task(args.complete)
        if completed:
            print(f"{GREEN}[x]{RESET} Completed task #{args.complete}: {completed['title']}")
        else:
            print(f"{YELLOW}No task matched id #{args.complete}{RESET}")

    if args.add is None and not args.view and args.delete is None and args.complete is None:
        interactive_mode()

if __name__ == "__main__":
    main()
