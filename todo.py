#!/usr/bin/env python3
"""
todo.py - Simple CLI To-Do List with JSON storage (Jupyter-safe) + Quote of the Day API.

Usage examples:
  python todo.py add "Buy milk" --due 2025-12-05 --tags shopping,groceries
  python todo.py list
  python todo.py edit 3 --title "Buy almond milk" --due 2025-12-06
  python todo.py done 3
  python todo.py delete 3
  python todo.py search milk
  python todo.py export backup.json
  python todo.py import backup.json
  python todo.py quote      # NEW: fetch quote from API and store as task
"""

import json
import argparse
import sys
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import List, Optional
import os
import urllib.request
import urllib.error

DEFAULT_DB = "todo_db.json"
DATE_FMT = "%Y-%m-%d"

# -------------------------
# Domain classes
# -------------------------
@dataclass
class Task:
    id: int
    title: str
    description: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    due: Optional[str] = None  # YYYY-MM-DD
    tags: List[str] = field(default_factory=list)
    done: bool = False

    def to_serializable(self):
        return asdict(self)

    @staticmethod
    def from_dict(d: dict):
        # Validate minimal expected keys
        try:
            return Task(
                id=int(d["id"]),
                title=str(d["title"]),
                description=str(d.get("description", "")),
                created_at=str(
                    d.get("created_at", datetime.now(timezone.utc).isoformat())
                ),
                due=d.get("due", None),
                tags=list(d.get("tags", [])),
                done=bool(d.get("done", False)),
            )
        except Exception as e:
            raise ValueError(f"Invalid task data: {e}")

# -------------------------
# Persistence + Manager
# -------------------------
class TodoDB:
    def __init__(self, path: str = DEFAULT_DB):
        self.path = path
        self.tasks: List[Task] = []
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            self.tasks = []
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("DB file root must be a list")
            self.tasks = [Task.from_dict(item) for item in data]
        except (json.JSONDecodeError, ValueError) as e:
            print(
                f"Warning: failed to load DB ({e}). Starting with empty DB.",
                file=sys.stderr,
            )
            self.tasks = []
        except Exception as e:
            print(f"Error reading DB file: {e}", file=sys.stderr)
            self.tasks = []

    def _save(self):
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(
                    [t.to_serializable() for t in self.tasks],
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
            os.replace(tmp, self.path)
        except Exception as e:
            raise IOError(f"Failed to save DB: {e}")

    def _next_id(self) -> int:
        if not self.tasks:
            return 1
        return max(t.id for t in self.tasks) + 1

    def add(
        self,
        title: str,
        description: str = "",
        due: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Task:
        if due:
            self._validate_date(due)
        tags = tags or []
        task = Task(
            id=self._next_id(),
            title=title,
            description=description,
            due=due,
            tags=tags,
        )
        self.tasks.append(task)
        self._save()
        return task

    def list(self, show_all: bool = True) -> List[Task]:
        return list(self.tasks)

    def find_by_id(self, id: int) -> Task:
        for t in self.tasks:
            if t.id == id:
                return t
        raise LookupError(f"Task with id {id} not found")

    def delete(self, id: int) -> None:
        task = self.find_by_id(id)
        self.tasks.remove(task)
        self._save()

    def edit(
        self,
        id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        due: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Task:
        task = self.find_by_id(id)
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if due is not None:
            if due != "":
                self._validate_date(due)
                task.due = due
            else:
                task.due = None
        if tags is not None:
            task.tags = tags
        self._save()
        return task

    def toggle_done(self, id: int) -> Task:
        task = self.find_by_id(id)
        task.done = not task.done
        self._save()
        return task

    def search(self, query: str) -> List[Task]:
        q = query.lower()
        return [
            t
            for t in self.tasks
            if q in t.title.lower()
            or q in t.description.lower()
            or q in " ".join(t.tags).lower()
        ]

    def export(self, export_path: str) -> None:
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(
                    [t.to_serializable() for t in self.tasks],
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            raise IOError(f"Failed to export DB: {e}")

    def import_file(self, import_path: str, merge: bool = True) -> None:
        try:
            with open(import_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("Import file must be a JSON list of tasks")
            new_tasks = [Task.from_dict(item) for item in data]
            if merge:
                # when merging, assign new IDs to avoid collisions
                base_id = self._next_id()
                for i, t in enumerate(new_tasks):
                    t.id = base_id + i
                    self.tasks.append(t)
            else:
                # replace
                self.tasks = new_tasks
            self._save()
        except Exception as e:
            raise IOError(f"Failed to import DB: {e}")

    @staticmethod
    def _validate_date(d: str):
        try:
            datetime.strptime(d, DATE_FMT)
        except ValueError:
            raise ValueError(f"Date must be in YYYY-MM-DD format, got '{d}'")

# -------------------------
# API Integration: Quote of the Day
# -------------------------
def fetch_quote_of_the_day() -> tuple[str, str]:
    """
    Fetch a random quote from an online API (quotable.io).
    Returns (content, author).
    Raises IOError for network issues, ValueError for JSON/format issues.
    """
    url = "http://api.quotable.io/random"
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            # HTTP status check (Python 3.9+ has resp.status)
            status = getattr(resp, "status", None)
            if status is not None and status != 200:
                raise IOError(f"Quote API returned status {status}")
            data_bytes = resp.read()
    except urllib.error.URLError as e:
        raise IOError(f"Network error while calling quote API: {e}") from e

    try:
        text = data_bytes.decode("utf-8")
        data = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to parse quote JSON: {e}") from e

    content = data.get("content")
    author = data.get("author", "Unknown")

    if not content or not isinstance(content, str):
        raise ValueError("Quote JSON missing valid 'content' field")

    if not isinstance(author, str):
        author = "Unknown"

    return content.strip(), author.strip()

# -------------------------
# CLI
# -------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="todo.py", description="Simple To-Do List with JSON DB + Quote API"
    )
    parser.add_argument("--db", "-d", default=DEFAULT_DB, help="path to JSON DB file")

    # Do not set required=True; we handle missing command ourselves
    sub = parser.add_subparsers(dest="cmd")

    p_add = sub.add_parser("add", help="Add a new task")
    p_add.add_argument("title", help="task title")
    p_add.add_argument("--description", "-m", default="", help="task description")
    p_add.add_argument("--due", help="due date YYYY-MM-DD")
    p_add.add_argument("--tags", help="comma-separated tags")

    p_list = sub.add_parser("list", help="List tasks")
    p_list.add_argument("--all", action="store_true", help="show all tasks (default)")

    p_edit = sub.add_parser("edit", help="Edit a task")
    p_edit.add_argument("id", type=int)
    p_edit.add_argument("--title")
    p_edit.add_argument("--description")
    p_edit.add_argument("--due", help="YYYY-MM-DD (use empty string to clear)")
    p_edit.add_argument("--tags", help="comma-separated tags (use empty to clear)")

    p_done = sub.add_parser("done", help="Toggle done/undone a task")
    p_done.add_argument("id", type=int)

    p_delete = sub.add_parser("delete", help="Delete a task")
    p_delete.add_argument("id", type=int)

    p_search = sub.add_parser("search", help="Search tasks by text")
    p_search.add_argument("query")

    p_export = sub.add_parser("export", help="Export DB to JSON file")
    p_export.add_argument("path")

    p_import = sub.add_parser("import", help="Import tasks from JSON file")
    p_import.add_argument("path")
    p_import.add_argument(
        "--replace", action="store_true", help="replace DB instead of merging"
    )

    # NEW: quote subcommand
    p_quote = sub.add_parser(
        "quote",
        help="Fetch a Quote of the Day from API and store it as a new task",
    )

    return parser

def parse_args_safe(argv):
    """
    Use parse_known_args to ignore unknown args (Jupyter injects kernel args like --f kernel-xxxx.json).
    Returns (parser, args, unknown_list).
    """
    parser = build_parser()
    args, unknown = parser.parse_known_args(argv)
    return parser, args, unknown

def print_task(t: Task):
    status = "[x]" if t.done else "[ ]"
    due = f" due:{t.due}" if t.due else ""
    tags = f" tags:{','.join(t.tags)}" if t.tags else ""
    print(f"{t.id:3d}. {status} {t.title}{due}{tags}")
    if t.description:
        print(f"     {t.description}")

def main(argv):
    parser, args, unknown = parse_args_safe(argv)

    if unknown:
        # Common Jupyter kernel arg pattern contains 'kernel' or '--f' etc.
        # We ignore them but inform the user.
        print(f"[info] Ignored unknown args: {unknown}", file=sys.stderr)

    # If no subcommand provided, show help (instead of crashing).
    if not args.cmd:
        parser.print_help()
        return

    try:
        db = TodoDB(args.db)
    except Exception as e:
        print(f"Failed to initialize DB: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        if args.cmd == "add":
            tags = args.tags.split(",") if args.tags else []
            task = db.add(args.title, args.description, args.due, tags)
            print("Added:")
            print_task(task)

        elif args.cmd == "list":
            tasks = db.list()
            if not tasks:
                print("No tasks.")
            else:
                for t in tasks:
                    print_task(t)

        elif args.cmd == "edit":
            tags = None
            if args.tags is not None:
                tags = args.tags.split(",") if args.tags else []
            task = db.edit(
                args.id,
                title=args.title,
                description=args.description,
                due=args.due,
                tags=tags,
            )
            print("Updated:")
            print_task(task)

        elif args.cmd == "done":
            task = db.toggle_done(args.id)
            print("Toggled:")
            print_task(task)

        elif args.cmd == "delete":
            db.delete(args.id)
            print(f"Deleted task {args.id}")

        elif args.cmd == "search":
            results = db.search(args.query)
            if not results:
                print("No matches.")
            else:
                for t in results:
                    print_task(t)

        elif args.cmd == "export":
            db.export(args.path)
            print(f"Exported to {args.path}")

        elif args.cmd == "import":
            db.import_file(args.path, merge=not args.replace)
            print(f"Imported from {args.path}")

        elif args.cmd == "quote":
            # NEW: use API to fetch a quote, then save as task
            content, author = fetch_quote_of_the_day()
            title = f'"{content}" — {author}'
            description = "Quote of the day from quotable.io"
            task = db.add(title, description, tags=["quote", "motivation"])
            print("Added quote as task:")
            print_task(task)

        else:
            print("Unknown command", file=sys.stderr)
            sys.exit(2)

    except LookupError as e:
        print(f"Not found: {e}", file=sys.stderr)
        sys.exit(3)
    except ValueError as e:
        print(f"Invalid input: {e}", file=sys.stderr)
        sys.exit(4)
    except IOError as e:
        print(f"I/O error: {e}", file=sys.stderr)
        sys.exit(5)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(99)

if __name__ == "__main__":
    # Run with only the args intended for the script (everything after the script name).
    main(sys.argv[1:])
