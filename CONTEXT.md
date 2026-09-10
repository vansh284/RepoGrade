# Domain Glossary — RepoGrade

## Course
A teaching course (e.g. "CS201 Fall 2026"). Top-level container. Reusable across semesters.

## Assignment
A graded piece of work within a Course. Each Assignment has a single GitHub repo name shared by all students (differentiated by username).

## Student
A person enrolled in a Course. Has: name, student ID, email, GitHub username. Imported via CSV.

## Submission
A Student's GitHub repository for a given Assignment. Identified by `github.com/{username}/{repo-name}`.

## Check
A Python script that runs against a cloned Submission. Receives the repo path as input. Outputs structured JSON: `{ "passed": bool, "message": string, "details": string }`. Multiple Checks can be defined per Assignment.

## Check Result
The outcome of running a Check against a Submission. Stores pass/fail status, message, and hidden details (e.g. raw stderr).

## Peer Assignment
A mapping of a Student to other Students' Submissions for peer evaluation. Count is configurable per Assignment. Mutual assignments are permitted.

## Peer Evaluation
A score-per-component plus written feedback submitted by a peer-assigned Student for another Student's Submission.

## Evaluator Grade
A score-per-component entered by the instructor/evaluator for a Submission.

## Grading Component
A named, weighted dimension of grading (e.g. "Code Quality", "Functionality"). Configurable per Assignment. Both peers and evaluators score each component.

## Penalty
A freeform per-student deduction on a Submission. Has: reason (text) and amount (points or percentage). Entered via UI, not imported.

## Final Grade
Weighted consolidation of Evaluator Grades and Peer Evaluations across all Grading Components, minus Penalties. Exportable as CSV (Canvas-compatible: Student, ID, SIS Login ID columns where available, plus grade columns).

## Check Script
A `.py` file in a directory on disk associated with an Assignment. Named by filename (e.g. `check_build.py`). The app discovers all `.py` files in the configured directory. Each script is executed from inside the cloned repo directory with no arguments.

## Email Template
A reusable message template scoped per Assignment. Contains placeholders: `{student_name}`, `{student_id}`, `{student_email}`, `{github_username}`, `{repo_url}`, `{assignment_name}`, `{course_name}`, `{check_name}`, `{check_message}`, `{check_details}`. Sent via SMTP through outlook.office365.com. Two categories: problem-type templates (for check failures) and peer assignment templates (composed ad-hoc with dynamic repo URL variables).

## Environment Variable
Context passed to Check Scripts before execution. Set by the app per invocation. Includes: `STUDENT_USERNAME`, `ASSIGNMENT_NAME`, and any custom variables configured per Assignment via the UI. Scripts receive no CLI arguments — all context comes through env vars.
