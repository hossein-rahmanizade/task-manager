import argparse
from datetime import datetime
import json
import os
import re
import sys


# ANSI escape codes for terminal output. Terminals interpret these as styling
# instructions, not as visible characters. RESET must follow any styled segment,
# otherwise the style bleeds into subsequent output.
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"

json_path = "/tmp/tasks.json"
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

    Returns a dict with keys {title, priority, due, date_added, done} on success,
    or None on validation failure (with the error message printed).
    """
    date_added = datetime.now().strftime("%Y-%m-%d %H:%M")
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
    try:
        datetime.strptime(result["due"], "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            datetime.strptime(result["due"], "%Y-%m-%d")
        except ValueError:
            print(f"{RED}X Due date must be 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD'{RESET}")
            return None
    result["date_added"] = date_added
    result["done"] = False
    return result


def add_task_to_file(task: dict) -> int:
    """Persist a parsed task dict to the JSON store and return its assigned id.

    Args:
        task: Parsed task dict from parse_task_input. Must not have an 'id'
            key set; one will be assigned by this function based on existing
            tasks in the store.

    Returns:
        The integer id assigned to the newly stored task.

    Side effects:
        Writes to json_path. Creates the file if it does not exist.
    """
    if not os.path.exists(json_path):
        tasks = []
    else:
        if os.path.getsize(json_path) > 0:
            with open(json_path, 'r') as file:
                tasks = json.load(file)
        else:
            tasks = []

    next_id = max((t['id'] for t in tasks), default=0) + 1
    task["id"] = next_id
    tasks.append(task)

    with open(json_path, 'w') as file:
        json.dump(tasks, file, indent=4, sort_keys=True)

    return next_id


def delete_task(task_id: int) -> dict | None:
    """Delete the task with the given id. Return the deleted task dict, or None if not found."""
    if not os.path.exists(json_path):
        return None

    with open(json_path, 'r') as file:
        tasks = json.load(file)

    deleted = None
    for i in range(len(tasks) - 1, -1, -1):
        if tasks[i]["id"] == task_id:
            deleted = tasks.pop(i)
            break

    if deleted is None:
        return None

    with open(json_path, 'w') as file:
        json.dump(tasks, file, indent=4, sort_keys=True)

    return deleted


def complete_task(task_id: int) -> dict | None:
    """Mark the task with the given id as done. Return the updated task dict, or None if not found."""
    if not os.path.exists(json_path):
        return None

    with open(json_path, 'r') as file:
        tasks = json.load(file)

    completed = None
    for task in tasks:
        if task["id"] == task_id:
            task["done"] = True
            completed = task
            break

    if completed is None:
        return None

    with open(json_path, 'w') as file:
        json.dump(tasks, file, indent=4, sort_keys=True)

    return completed


def view_task():
    """Print all tasks currently in the store."""
    if not os.path.exists(json_path):
        print(f"{YELLOW}There are no tasks to view.{RESET}")
        return

    with open(json_path, 'r') as file:
        tasks = json.load(file)

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
            new_id = add_task_to_file(parsed)
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
            view_task()
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
        new_id = add_task_to_file(parsed)
        print(f"{GREEN}[+]{RESET} Added task #{new_id}: \"{parsed['title']}\" (priority: {parsed['priority']}, due: {parsed['due']})")
    if args.view:
        view_task()
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
