# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- Run App: `python app.py` (starts on port 5001)
- Install Dependencies: `pip install -r requirements.txt`
- Run Tests: `pytest`

## Architecture
This is a Flask-based Expense Tracker application.

### Structure
- `app.py`: Main entry point containing routes and application configuration.
- `database/`:
  - `db.py`: Database utility functions (connection management, initialization, and seeding).
- `static/`: Static assets including CSS and JavaScript.
- `templates/`: Jinja2 HTML templates for the frontend.
- `requirements.txt`: Project dependencies.

### Current Status
The project is in the early stages of development. Several routes in `app.py` (logout, profile, expense management) are currently placeholders for future implementation steps. The database layer in `database/db.py` is awaiting initial setup.
