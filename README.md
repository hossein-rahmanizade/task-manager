# Project: CLI Task Manager (JSON version)

## requirement:

  - [x] Get the user task and show them 
  - [x] Add task to a file
  - [x] View tasks
  - [x] Mark done
  - [x] Delete task
  - [ ] Edit task
  - [x] Store in `tasks.json`
  - [x] Each task:
        {
          "id": 1,
          "title": "...",
          "done: False,
          "priority": 1-5
          "due": "2026-05-04"
          "date_added: "2026-05-03"
        }

## Code cleanup:

- [x] Need to add timestamp to user's input
- [x] Handle errors in the parse_task_input() for edge case inputs
- [x] Add main and while to keep getting user's input unless user stops it
- [x] Add args for faster task taking from terminal, add flags like {"-a":"add task","-d":"delete","-v":"view tasks",...}, so to handle this, I need to have 2 general state for my program, one is like main-command-line mode and the other one interactive mode, I will do this on a new branch just to practice git branches. 
- [x] Handle the "id" in json file
- [x] Add descriptive prints at the begining of the code for user to choose.
- [x] Add a function for file_exist()
- [x] I also need to figure out how List the task for user, cause the json format is not clean enough here.
- [x] Add simple docstring to the functions
- [ ] Work on a better way to enter the due, cause it's a bit annoying to type all the date date and time manually every single time.
- [x] Handle errors when the items of a task are missing like when there is no prioriy or due in user's input.

## Next steps & featuresfa

- [ ] Add 2 more ways to delete tasks, based on priority and based on time like a week old task.
- [ ] Work on efficient ways to find and delete tasks. (better algorithm)
- [ ] Maybe a function to show finished tasks and pending tasks.