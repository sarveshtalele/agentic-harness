# Business Requirements Document: Team Task Tracker

Version 1.0, 2026-11-14. Owner: QE platform sample (used by the greenfield live test).

## 1. Purpose

A small web application where a team records tasks, sees open work and marks tasks done. It replaces a shared
spreadsheet. It has a REST API and one web page.

## 2. Users

- **Team member**: creates, lists, completes and deletes tasks.

There is no sign-in in version 1.0; the application runs on a private network.

## 3. Functional requirements

### 3.1 Create a task

- BR-1: A team member creates a task with a title and an optional due date.
- BR-2: The title is required, is trimmed of leading and trailing spaces, and must be 1 to 120 characters after trimming.
  A title outside this range is rejected with HTTP 422 and the message "title must be 1 to 120 characters".
- BR-3: The due date, when given, uses the format YYYY-MM-DD. Any other format is rejected with HTTP 422 and the message
  "due_date must be YYYY-MM-DD".
- BR-4: A new task has the status "open" and a unique integer id assigned by the system. The API answers HTTP 201 with the
  task.

### 3.2 List tasks

- BR-5: A team member lists all tasks, newest first.
- BR-6: The list can be filtered by status with `?status=open` or `?status=done`. Any other status value is rejected with
  HTTP 422 and the message "status must be open or done".

### 3.3 Complete a task

- BR-7: A team member marks an open task as done. The API answers HTTP 200 with the task, now with the status "done".
- BR-8: Completing a task that is already done answers HTTP 409 with the message "task is already done".
- BR-9: Completing or deleting a task id that does not exist answers HTTP 404 with the message "task not found".

### 3.4 Delete a task

- BR-10: A team member deletes a task. The API answers HTTP 204 with no body, and the task no longer appears in the list.

### 3.5 Web page

- BR-11: The page shows the list of tasks with their title, due date and status, and a form to add a task.
- BR-12: Each open task has a "Done" button that completes it, and each task has a "Delete" button.
- BR-13: When the API rejects a new task, the page shows the API's message next to the form and keeps what was typed.

## 4. Non-functional requirements

- NFR-1: The API answers `GET /health` with HTTP 200 and `{"status": "ok"}`.
- NFR-2: Tasks are kept in memory in version 1.0; a restart clears them.

## 5. Out of scope

Users and sign-in, task assignment, comments, attachments, notifications.
