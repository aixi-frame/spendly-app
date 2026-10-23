from flask import Flask, render_template, request, redirect, url_for, flash, abort, session
from database.db import init_db, seed_db, create_user, get_user_by_email, get_db
from database import queries
import sqlite3
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta


app = Flask(__name__)
app.secret_key = "spendly-dev-key-for-session-flashing"

with app.app_context():
    init_db()
    seed_db()

def get_date_filters(date_from, date_to):
    """
    Validates date filters and computes presets.
    Returns (error_msg, validated_from, validated_to, presets_dict)
    """
    validated_from = None
    validated_to = None

    if date_from and date_to:
        try:
            datetime.strptime(date_from, "%Y-%m-%d")
            datetime.strptime(date_to, "%Y-%m-%d")

            if date_from > date_to:
                return "Start date must be before end date.", None, None, {}

            validated_from = date_from
            validated_to = date_to
        except ValueError:
            return "Invalid date format provided. Please use YYYY-MM-DD.", None, None, {}

    today = datetime.now().date()
    presets = {
        "month": {
            "from": today.replace(day=1).isoformat(),
            "to": today.isoformat()
        },
        "3m": {
            "from": (today - timedelta(days=90)).isoformat(),
            "to": today.isoformat()
        },
        "6m": {
            "from": (today - timedelta(days=180)).isoformat(),
            "to": today.isoformat()
        }
    }

    return None, validated_from, validated_to, presets


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
            print(f"DEBUG: User logged in. ID: {user['id']}, Email: {email}")
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

    user_id = session["user_id"]
    user_data = queries.get_user_by_id(user_id)
    if not user_data:
        session.clear()
        flash("User account not found.", "error")
        return redirect(url_for("login"))

    # Date Filter Handling
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    error_msg, validated_from, validated_to, presets = get_date_filters(date_from, date_to)
    if error_msg:
        flash(error_msg, "error")

    # Summary Stats
    summary_stats = queries.get_summary_stats(user_id, validated_from, validated_to)
    summary_stats["total_spent"] = f"₹{summary_stats['total_spent']:,.2f}"

    # Fetch recent transactions from database
    recent_transactions = queries.get_recent_transactions(user_id, date_from=validated_from, date_to=validated_to)
    transactions = [
        {**t, "amount": f"₹{t['amount']:,.2f}"}
        for t in recent_transactions
    ]

    # Category breakdown logic
    raw_breakdown = queries.get_category_breakdown(user_id, validated_from, validated_to)

    category_class_map = {
        "Food": "bar-food",
        "Food & Dining": "bar-food",
        "Transport": "bar-travel",
        "Entertainment": "bar-entertainment",
        "Bills": "bar-bills",
        "Other": "bar-other"
    }

    category_breakdown = []
    for item in raw_breakdown:
        category = item["category"]
        category_breakdown.append({
            "category": category,
            "amount": f"₹{item['amount']:,.2f}",
            "percentage": item["pct"],
            "class": category_class_map.get(category, "bar-other")
        })

    return render_template(
        "profile.html",
        user=user_data,
        stats=summary_stats,
        transactions=transactions,
        breakdown=category_breakdown,
        active_from=validated_from,
        active_to=validated_to,
        presets=presets
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
