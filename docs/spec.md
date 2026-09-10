# RepoGrade — Spec

## Problem Statement

An instructor grading coding assignments must manually clone student repos, run validation scripts one by one, email students about problems, coordinate peer evaluations, collect grades from multiple sources, and consolidate everything into a final grade for Canvas. Each step is tedious, error-prone, and doesn't scale past a handful of students.

## Solution

RepoGrade is a locally-run web application that automates the entire post-submission grading workflow: batch-clone GitHub repos, run configurable check scripts in parallel, email students about failures via SMTP, manage peer evaluation assignments with round-robin distribution, collect and consolidate grades from evaluators and peers with configurable component weights, and export Canvas-compatible CSVs. The instructor interacts through a React UI backed by a FastAPI server with SQLite storage.

## User Stories

1. As an instructor, I want to create a Course (e.g. "CS201 Fall 2026"), so that I can organize students and assignments under one container.
2. As an instructor, I want to view a list of all my Courses, so that I can navigate between them.
3. As an instructor, I want to import a Student roster via CSV (name, student ID, email, GitHub username), so that I can onboard an entire class at once.
4. As an instructor, I want to manually add, edit, or remove individual Students, so that I can handle mid-semester roster changes without re-importing.
5. As an instructor, I want to export the Student roster as CSV, so that I have an offline copy.
6. As an instructor, I want to create multiple Assignments within a Course, so that each graded piece of work is tracked separately.
7. As an instructor, I want to configure a GitHub repo name per Assignment, so that each Student's Submission is identified as `github.com/{username}/{repo-name}`.
8. As an instructor, I want to define Grading Components per Assignment (name, max points, weight), so that grading is structured and configurable.
9. As an instructor, I want to configure the evaluator-vs-peer weight per Assignment, so that the Final Grade reflects the intended balance between instructor and peer scores.
10. As an instructor, I want to set a checks directory path per Assignment, so that the app auto-discovers all `.py` Check Scripts in that folder.
11. As an instructor, I want to configure custom Environment Variables per Assignment via a key-value table in the UI, so that Check Scripts can access assignment-specific context (e.g. deadlines).
12. As an instructor, I want to clone all Student repos for an Assignment in one batch action, so that I don't clone them manually.
13. As an instructor, I want repos stored persistently on disk at a predictable path, so that I can re-run checks or browse code later.
14. As an instructor, I want to see a progress bar while repos are being cloned, so that I know how far along the batch is.
15. As an instructor, I want each Student's row to show repo status (cloned / missing / error), so that I have full visibility.
16. As an instructor, I want missing repos automatically flagged with a zero grade and suggested for email notification, so that I can act on non-submissions quickly.
17. As an instructor, I want to run all Check Scripts against all cloned Submissions in parallel, so that results come back quickly for 200 students.
18. As an instructor, I want each Check Script executed from inside the cloned repo directory with `STUDENT_USERNAME`, `ASSIGNMENT_NAME`, and custom Environment Variables set, so that scripts have context without CLI arguments.
19. As an instructor, I want to see Check Results per Student in the assignment dashboard (pass/fail icon, message), so that I can identify problems at a glance.
20. As an instructor, I want to expand a Check Result to reveal hidden details (e.g. raw stderr), so that I can debug failures when needed.
21. As an instructor, I want to export all Check Results as CSV, so that I have an offline record.
22. As an instructor, I want to create Email Templates per problem type with placeholders (`{student_name}`, `{student_id}`, `{student_email}`, `{github_username}`, `{repo_url}`, `{assignment_name}`, `{course_name}`, `{check_name}`, `{check_message}`, `{check_details}`), so that I can send consistent notifications.
23. As an instructor, I want to select all Students with a specific failed Check and batch-send them the corresponding Email Template, so that I can notify everyone efficiently.
24. As an instructor, I want to preview rendered emails before sending, so that I can verify placeholders resolved correctly.
25. As an instructor, I want SMTP credentials stored in a `.env` file (not in the UI or codebase), so that secrets stay out of version control.
26. As an instructor, I want to generate Peer Assignments using a round-robin shuffle with a configurable number of repos per peer, so that every Student reviews and is reviewed an approximately equal number of times.
27. As an instructor, I want to view the Peer Assignment mapping before notifying students, so that I can verify the distribution.
28. As an instructor, I want to export Peer Assignments as CSV, so that I have an offline record.
29. As an instructor, I want to compose an ad-hoc email in the UI and batch-send it to all peer-assigned Students, with `{repo_url_1}`, `{repo_url_2}`, etc. dynamically replaced per recipient, so that each Student knows which repos to review.
30. As an instructor, I want to import Peer Evaluations from a CSV containing evaluator name, evaluee GitHub username, per-component scores, and feedback, so that I can collect peer grades from spreadsheets.
31. As an instructor, I want unrecognized evaluator names highlighted in a different color (not rejected as errors), so that minor mismatches don't block the import.
32. As an instructor, I want to export Peer Evaluations as CSV, so that I have an offline record.
33. As an instructor, I want to grade a Student's Submission in the UI with the GitHub repo link and Check Results visible alongside the grading form, so that I have context while scoring.
34. As an instructor, I want to score each Grading Component individually for a Submission, so that grades are granular.
35. As an instructor, I want to bulk-import Evaluator Grades via CSV, so that I can grade offline in a spreadsheet and upload results.
36. As an instructor, I want to export Evaluator Grades as CSV, so that I have an offline record.
37. As an instructor, I want to add freeform Penalties per Student per Assignment (reason text + deduction amount), so that I can handle issues like late submission or plagiarism.
38. As an instructor, I want to edit or remove Penalties, so that I can correct mistakes.
39. As an instructor, I want to see the Final Grade per Student computed from weighted Grading Components, evaluator-vs-peer balance, and Penalties, so that I have a complete picture.
40. As an instructor, I want to export Final Grades as a Canvas-compatible CSV per Assignment (`Student`, `ID`, `SIS Login ID`, one column per Grading Component, Final Grade column), so that I can import directly into Canvas LMS.
41. As an instructor, I want a backup button that copies the SQLite database to a configurable path (e.g. OneDrive folder), so that my data is backed up.
42. As an instructor, I want a restore button that loads the database from that backup path, so that I can recover from data loss.
43. As an instructor, I want the main navigation to follow Course list → Assignment list → Assignment dashboard, so that the hierarchy is intuitive.
44. As an instructor, I want the Assignment dashboard to show a sortable, filterable table of all Students with columns for name, GitHub username, repo status, check results, evaluator grade, peer grade, penalties, and final grade, so that I can quickly find what I need.

## Implementation Decisions

- **Tech stack**: FastAPI (Python) backend, Vite + React + TypeScript frontend. SQLAlchemy ORM over SQLite, enabling future migration to PostgreSQL.
- **Single command launch**: one terminal command starts both backend and frontend for local use.
- **Database**: SQLite file stored locally. No cloud sync of the live DB — explicit backup/restore to a user-configured path instead.
- **SMTP for email**: connects to `outlook.office365.com` via SMTP. Credentials read from a `.env` file (`SMTP_EMAIL`, `SMTP_PASSWORD`). No Microsoft Graph API.
- **Repo storage**: cloned to a local directory structure `{configurable_base}/{course}/{assignment}/{github_username}/`. Repos persist across sessions for re-running checks and browsing.
- **Check script discovery**: the app scans a user-configured directory per Assignment for `.py` files. Each file is one Check, named by its filename (minus extension).
- **Check script execution**: each script runs as a subprocess from inside the cloned repo directory (`cwd` set to repo root). No CLI arguments. Context provided via environment variables: `STUDENT_USERNAME`, `ASSIGNMENT_NAME`, plus custom key-value pairs configured per Assignment. Scripts output JSON to stdout: `{"passed": bool, "message": str, "details": str}`. The app also captures raw stderr.
- **Parallel check execution**: checks run with configurable concurrency (e.g. `asyncio.subprocess` with a semaphore). Scripts are independent — each operates on its own repo clone.
- **Email templates**: stored per Assignment in the database. Placeholders use Python `str.format_map` style. Two categories: problem-type templates (tied to check failures) and ad-hoc peer assignment emails (composed in UI at send time).
- **Peer assignment algorithm**: round-robin shuffle. Configurable count (default 2). Mutual assignments (A↔B) are permitted. Every Student receives approximately the same number of reviews.
- **Peer evaluation CSV format**: columns are `evaluator_name`, `evaluee_github`, one column per Grading Component (matching component names), `feedback`. Evaluator name is soft-matched against the Student roster — highlighted if unrecognized, not rejected.
- **Grading components**: defined per Assignment (not per Course). Each has a name, max points, and weight. Configurable scale per component.
- **Grade consolidation formula**: for each component, `consolidated_score = (evaluator_weight * evaluator_score) + (peer_weight * avg_peer_score)`. Final grade = sum of `(component_weight * consolidated_score)` across all components, minus penalties.
- **Penalties**: freeform, entered via UI only (not CSV-imported). Each has a reason string and a numeric deduction.
- **Canvas export format**: per-assignment CSV with columns `Student` (Last, First), `ID` (student ID), `SIS Login ID` (student email), one column per Grading Component (points), and a Final Grade column.
- **Navigation hierarchy**: three levels — Course list → Assignment list → Assignment dashboard (sortable/filterable student table).
- **No authentication**: single-user local app. No login required.

## Testing Decisions

- **Primary seam**: the REST API layer. All backend logic is tested by making HTTP requests to FastAPI endpoints and asserting JSON responses. This tests the full stack (routing → service logic → ORM → database) through one seam.
- **External boundary fakes**: SMTP sending, git clone operations, and subprocess execution (check scripts) are behind injectable interfaces (dependency injection via FastAPI's `Depends`). Tests swap these with in-memory fakes. No mocking libraries — plain Python fake classes.
- **Test database**: each test gets a fresh SQLite in-memory database via the ORM, so tests are isolated and fast.
- **What makes a good test**: tests assert on external behavior (HTTP status codes, response bodies, database state after a request), never on internal function calls or implementation details. A test should survive an internal refactor without changing.
- **Frontend**: not tested in the initial build. The API contract is the boundary; the frontend consumes it. Manual verification via the browser during development.

## Out of Scope

- Multi-user support / authentication / role-based access
- Real-time collaboration or concurrent access
- Docker or cloud deployment
- Plagiarism detection
- Git diff or code viewer embedded in the app
- Automated grading (the app facilitates manual grading, not auto-grading)
- Integration with Canvas API (export is CSV-based, not API-based)
- Grade audit trail or version history
- Pre-deadline / pre-submission workflows

## Further Notes

- The app documentation should clearly state that Check Scripts run from inside the repo directory and receive context via environment variables, not CLI arguments.
- The `.env` file should be git-ignored by default.
- The Student roster CSV is expected to have columns: `name`, `student_id`, `email`, `github_username`. Column order is flexible; matching is by header name.
- Canvas export uses `Student` in "Last, First" format. If the imported name doesn't follow this format, the app should attempt to parse and reformat it, or export as-is with a warning.
