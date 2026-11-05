import argparse
from datetime import datetime
import json
import os
import re
import sys


json_path = "/tmp/tasks.json"
cmd_parser = argparse.ArgumentParser()
cmd_parser.add_argument("-a", "--add", help= "Add task in this format with dqoutes: \"title, priority, due\".")
cmd_parser.add_argument("-v", "--view", action = "store_true", help = "View Tasks")
cmd_parser.add_argument("-d", "--delete", help= "Enter the title of the task in dqoutes, view tasks first for checking you tasks first.")
cmd_parser.add_argument("-m", "--markdown", help= "Enter the title of the task in dqoutes, view tasks first for checking you tasks first.")

def task_options_prints(): # later I need to add edit task option to it too.
    """Show program's option to the user"""
    print("\n" + "="*32)
    print("        CLI TASK MANAGER")
    print("="*32)
    print("        [1] Add new task")
    print("        [2] Delete task")
    print("        [3] View all tasks")
    print("        [4] Complete task")
    print("        [5] Exit")
    print("="*32)


def file_exist(path):
    return os.path.exists(path)


def parse_task_input(user_task: str) -> dict | None:
    """Takes raw input string, returns parsed dict with keys {title, priority, due, date_added, done} or None on validation failure, with the error message printed."""
    date_added = datetime.now().strftime("%Y-%m-%d %H:%M")    
    user_task_split = re.split(r'\s*,\s*', user_task)
    if len(user_task_split) != 3:
        print("X You have to enter all three task requirement")
        return None 
    user_task_keys = ["title", "priority", "due"]
    result = dict(zip(user_task_keys, user_task_split))
    if not result['title'] or not result['title'].strip():
        print("X Title cannot be empty")
        return None
    if result['priority'] not in ["1","2","3","4","5"]:
        print("X You have to enter the prioriy in a numerical format (1-5)")
        return None
    try:
        datetime.strptime(result["due"], "%Y-%m-%d %H:%M")
    except ValueError:
        try:
            datetime.strptime(result["due"], "%Y-%m-%d")
        except ValueError:
            print("X Due date must be 'YYYY-MM-DD HH:MM' or 'YYYY-MM-DD'")
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
    if not file_exist(json_path):
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

def delete_task(title):
    """Get an argument from user's input and delete a task based on it."""
    if file_exist(json_path):
        with open(json_path, 'r') as file:
            data = json.load(file)
            print()
            found = False
            for i in range(len(data)-1, -1, -1):
                if data[i]["title"] == title:
                    data.pop(i)
                    found = True
                    with open(json_path, 'w') as file:
                        json.dump(data, file, indent=4, sort_keys=True)        
                        print(f"You're task '{title}' been successfully deleted.")
            if not found:
                print("There's no task here to delete.")


def view_task(): # later I add parameters to filter the output like show_all=True
    """view the list of existing tasks in the json file."""
    if file_exist(json_path):
        with open(json_path, 'r') as file:
            data = json.load(file)
        print()
        for i in range(len(data)):
            if not data[i]["done"]:
                print(f'[ ] {data[i]["id"]}. {data[i]["title"]} (due: {data[i]["due"]}) (priority: {data[i]["priority"]})')
            else:
                print(f'[x] {data[i]["id"]}. {data[i]["title"]} (due: {data[i]["due"]}) (priority: {data[i]["priority"]})')
    else:
        print("There's no task here to view.")


def mark_down_task(title):
    """Get a name from user input as argument and mark it down by changing the done item into True."""
    if file_exist(json_path):
        with open(json_path, 'r') as file:
            data = json.load(file)
            found = False
            for i in range(len(data)):
                if data[i]["title"] == title:
                    data[i]["done"] = True
                    found = True
            if not found:
                    print(f"There's no task with '{title}' title.")
        if found:
            with open(json_path, 'w') as file:
                json.dump(data, file, indent=4, sort_keys=True)        
            print(f"You're task '{title}' been successfully completed.")

    else:
        print("There's no task here to complete.")


def interactive_mode():
    while True:
        task_options_prints()
        choice = input("Choose option 1-5: ")

        if choice == "1":
            raw = input("Enter title, priority, due: ") # make it more detailed, it's not informative enough
            parsed = parse_task_input(raw)
            if parsed is None:
                print("Invalid format. Use: title, priority, due")
                continue
            new_id = add_task_to_file(parsed)
            print(f'[+] Added task #{new_id}: "{parsed["title"]}" (priority: {parsed["priority"]}, due: {parsed["due"]})')
        elif choice == "2":
            title = input("Enter task name to delete: ")
            delete_task(title)
        elif choice == "3":
            view_task()
        elif choice == "4":
            name = input("Enter task name to complete: ") # or id number
            mark_down_task(name)
        elif choice == "5":
            print("Goodbye")
            break
        else:
            print("invalid choice")


def main():
    
    args = cmd_parser.parse_args()
    if args.add:
        parsed = parse_task_input(args.add)
        if parsed is None:
            sys.exit(1)
        new_id = add_task_to_file(parsed)
        print(f'[+] Added task #{new_id}: "{parsed["title"]}" (priority: {parsed["priority"]}, due: {parsed["due"]})')
    if args.view:
        view_task()
    if args.delete:
        delete_task(args.delete)
    if args.markdown:
        mark_down_task(args.markdown)

    if not any([args.add, args.view, args.delete, args.markdown]):
        interactive_mode()


if __name__ == "__main__":
    main()
