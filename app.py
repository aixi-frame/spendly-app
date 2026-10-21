from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from database.db import init_db, seed_db, create_user, get_user_by_email, get_db
import sqlite3
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = "spendly-dev-key-for-session-flashing"

with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Context Processors                                                     #
# ------------------------------------------------------------------ #

@app.context_processor
def inject_user_name():
    if session.get("user_id"):
        with get_db() as conn:
            user = conn.execute("SELECT name FROM users WHERE id = ?", (session["user_id"],)).fetchone()
            if user:
                return dict(current_user_name=user["name"])
    return dict(current_user_name=None)

# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Validation
        if not all([name, email, password, confirm_password]):
            flash("All fields are required.", "error")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        try:
            create_user(name, email, password)
            flash("Account created successfully! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already registered.", "error")
            return render_template("register.html")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = get_user_by_email(email)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash("Logged in successfully!", "success")
            return redirect(url_for("profile"))

        flash("Invalid email or password.", "error")
        return render_template("login.html")

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    # Hardcoded data for design validation (Step 4)
    user_data = {
        "name": "Amarjeet Kumar",
        "email": "amarjeet@example.com",
        "member_since": "October 2023",
        "initials": "AK"
    }

    summary_stats = {
        "total_spent": "₹12,450.00",
        "transaction_count": 24,
        "top_category": "Food & Dining"
    }

    transactions = [
        {"date": "2026-10-20", "description": "Starbucks Coffee", "category": "Food & Dining", "amount": "₹450.00"},
        {"date": "2026-10-19", "description": "Uber Ride", "category": "Transport", "amount": "₹220.00"},
        {"date": "2026-10-18", "description": "Amazon - Kindle Book", "category": "Entertainment", "amount": "₹899.00"},
        {"date": "2026-10-17", "description": "Grocery Store", "category": "Food & Dining", "amount": "₹1,200.00"},
    ]

    category_breakdown = [
        {"category": "Food & Dining", "amount": "₹4,500.00", "percentage": 36, "class": "bar-food"},
        {"category": "Transport", "amount": "₹2,100.00", "percentage": 17, "class": "bar-travel"},
        {"category": "Entertainment", "amount": "₹3,200.00", "percentage": 26, "class": "bar-bills"},
        {"category": "Bills", "amount": "₹2,650.00", "percentage": 21, "class": "bar-food"},
    ]

    return render_template(
        "profile.html",
        user=user_data,
        stats=summary_stats,
        transactions=transactions,
        breakdown=category_breakdown
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
