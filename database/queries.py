import sqlite3
from datetime import datetime
from database.db import get_db

def get_user_by_id(user_id):
    """
    Retrieves user profile information.
    Returns a dict with name, email, and member_since formatted as 'Month YYYY'.
    """
    with get_db() as conn:
        user = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()

        if user:
            # Parse created_at (expects ISO format from SQLite DEFAULT CURRENT_TIMESTAMP)
            # SQLite CURRENT_TIMESTAMP is 'YYYY-MM-DD HH:MM:SS'
            try:
                date_obj = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S")
                member_since = date_obj.strftime("%B %Y")
            except (ValueError, TypeError):
                member_since = "Unknown"

            return {
                "name": user["name"],
                "email": user["email"],
                "member_since": member_since,
                "initials": f"{user['name'][0].upper()}" if user['name'] else "?"
            }
    return None

def _apply_date_filter(query, params, date_from, date_to):
    """
    Helper to append date filtering to a query and its parameters.
    """
    if date_from and date_to:
        query += " AND date BETWEEN ? AND ?"
        params.extend([date_from, date_to])
    return query, params

def get_summary_stats(user_id, date_from=None, date_to=None):
    """
    Calculates overall spending stats for a user.
    Returns total_spent, transaction_count, and top_category.
    """
    with get_db() as conn:
        # Build query based on date filters
        query = "SELECT SUM(amount) as total, COUNT(*) as count FROM expenses WHERE user_id = ?"
        params = [user_id]
        query, params = _apply_date_filter(query, params, date_from, date_to)

        stats = conn.execute(query, params).fetchone()

        total_spent = stats["total"] if stats["total"] is not None else 0.0
        transaction_count = stats["count"] if stats["count"] is not None else 0

        # Top category by spend
        top_cat_query = "SELECT category FROM expenses WHERE user_id = ?"
        top_cat_params = [user_id]
        top_cat_query, top_cat_params = _apply_date_filter(top_cat_query, top_cat_params, date_from, date_to)
        top_cat_query += " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1"

        top_cat_row = conn.execute(top_cat_query, top_cat_params).fetchone()

        top_category = top_cat_row["category"] if top_cat_row else "—"

        return {
            "total_spent": total_spent,
            "transaction_count": transaction_count,
            "top_category": top_category
        }

def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    """
    Fetches the most recent transactions for a user.
    """
    with get_db() as conn:
        query = "SELECT date, description, category, amount FROM expenses WHERE user_id = ?"
        params = [user_id]
        query, params = _apply_date_filter(query, params, date_from, date_to)

        query += " ORDER BY date DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()

        return [dict(row) for row in rows]

def get_category_breakdown(user_id, date_from=None, date_to=None):
    """
    Calculates spending per category and computes percentages that sum to 100.
    """
    with get_db() as conn:
        query = "SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ?"
        params = [user_id]
        query, params = _apply_date_filter(query, params, date_from, date_to)

        query += " GROUP BY category ORDER BY total DESC"
        rows = conn.execute(query, params).fetchall()

        if not rows:
            return []

        overall_total = sum(row["total"] for row in rows)
        if overall_total == 0:
            return [{"category": row["category"], "amount": 0, "pct": 0} for row in rows]

        breakdown = []
        current_pct_sum = 0

        for i, row in enumerate(rows):
            # Calculate rounded percentage
            pct = round((row["total"] / overall_total) * 100)
            breakdown.append({
                "category": row["category"],
                "amount": row["total"],
                "pct": pct
            })
            current_pct_sum += pct

        # Adjustment: Add/subtract remainder from the largest category to ensure sum is 100
        diff = 100 - current_pct_sum
        if diff != 0:
            breakdown[0]["pct"] += diff

        return breakdown
