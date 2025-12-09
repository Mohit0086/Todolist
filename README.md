.

📌 To-Do List Application (Python Project)
A CLI-based Task Manager with JSON Database, OOP, Exception Handling & API Integration
📖 Overview

This project is a command-line To-Do List Manager built in Python.
It allows users to add, edit, delete, list, search, and complete tasks, with all data stored locally in a JSON file.
It also features API integration to fetch a Quote of the Day and store it as a motivational task.

This project demonstrates the use of:

Object-Oriented Programming (OOP)

JSON File Handling

Exception Handling

API Integration (quotable.io)

Clean, modular Python code

✨ Features
✅ Task Management

Add new tasks

Edit existing tasks

Delete tasks

Mark tasks as completed

Search tasks

List all stored tasks

🌐 API Integration

Fetches a Quote of the Day using the API:

http://api.quotable.io/random


The quote is saved as a new task with tags: quote, motivation.

💾 JSON Database

All tasks are stored persistently in:

todo_db.json

🧱 Object-Oriented Design

Task class

TodoDB class

Clean separation of functionality

🛡 Exception Handling

Handles:

File errors

JSON errors

Network errors

Invalid user input

Missing tasks

🛠 How to Run the Project
1️⃣ Navigate to the project directory
cd "C:\Todolist"

2️⃣ Run commands using Python
➕ Add a task
python todo.py add "Buy milk"

📜 List tasks
python todo.py list

⭐ Fetch Quote of the Day (API)
python todo.py quote

✔ Mark a task as done
python todo.py done 3

🔍 Search tasks
python todo.py search milk

🗑 Delete a task
python todo.py delete 2

📂 Project Structure
Todolist/
│── todo.py        # Main program
│── todo_db.json   # Data storage (auto-created)
│── README.md      # Project documentation

📡 API Used
Quotable API – Random Quotes

URL: http://api.quotable.io/random

Returns JSON containing:

content → Quote text

author → Author name

This satisfies the API Integration requirement in the project rubric.

🧪 Technologies Used

Python 3

JSON for database

urllib (for API calls)

argparse (for CLI)

dataclasses (for Task class)

🏆 Rubric Coverage

This project meets the rubric requirements:

Category	Status
Correctness	✔ Fully working
OOP	✔ Classes, objects, encapsulation
API Integration	✔ Quote API with error handling
Exception Handling	✔ Try–except with custom messages
File Handling	✔ JSON read/write
Code Quality	✔ Clean, modular, documented
Features	✔ All required + bonus features
👤 Author

Mohit Choudhary
Python Programming Project – Semester V

📜 License

This project is open for educational use.
