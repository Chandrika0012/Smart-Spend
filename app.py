from flask import Flask, render_template, request
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

app = Flask(__name__)

BASE = Path(__file__).resolve().parent
CUSTOMERS_FILE = BASE / "customers.csv"
TRANSACTIONS_FILE = BASE / "transactions.csv"

# Default budget allocation. These percentages total 100%.
BUDGET_RULES = {
    "Rent": 30,
    "Food": 15,
    "Travel": 10,
    "Bills": 10,
    "Shopping": 10,
    "Healthcare": 5,
    "Entertainment": 5,
    "Savings": 15,
}

def load_data():
    customers = pd.read_csv(CUSTOMERS_FILE)
    transactions = pd.read_csv(TRANSACTIONS_FILE, parse_dates=["date"])
    return customers, transactions

def money(value):
    return round(float(value), 2)

def budget_allocation(income):
    return {category: money(income * pct / 100) for category, pct in BUDGET_RULES.items()}

def category_summary(tx):
    if tx.empty:
        return pd.DataFrame(columns=["category", "spent"])
    out = tx.groupby("category", as_index=False)["amount"].sum()
    out = out.rename(columns={"amount": "spent"})
    return out.sort_values("spent", ascending=False)

@app.route("/", methods=["GET", "POST"])
def dashboard():
    customers, transactions = load_data()
# ==========================================================
    # NEW CUSTOMER OPTION
    # ==========================================================

    is_new_customer = request.form.get("action") == "new_customer"

    if is_new_customer:

        # Get details entered by ma'am
        name = request.form.get("name", "").strip()
        age = int(request.form.get("age", 0))
        occupation = request.form.get("occupation", "").strip()
        income = float(request.form.get("income", 0))

        # Create temporary customer
        customer = {
            "customer_id": "NEW",
            "name": name,
            "age": age,
            "occupation": occupation,
            "income": income
        }

        selected_id = "NEW"

        # Use the existing dataset's transaction pattern
        # as a sample for the new customer.
        base_customer = customers.iloc[0]
        base_id = base_customer["customer_id"]
        base_income = float(base_customer["income"])

        tx = transactions[
            transactions["customer_id"] == base_id
        ].copy()

        # Scale transactions according to new income
        if not tx.empty and base_income > 0:
            scale = income / base_income
            tx["amount"] = tx["amount"] * scale

        tx["customer_id"] = "NEW"

    else:

        # ======================================================
        # EXISTING CUSTOMER CODE — KEEPING YOUR ORIGINAL LOGIC
        # ======================================================

        selected_id = request.form.get(
            "customer_id",
            request.args.get("customer_id", "1")
        )

        try:
            selected_id = int(selected_id)
        except ValueError:
            selected_id = 1

        customer_row = customers[
            customers["customer_id"] == selected_id
        ]

        if customer_row.empty:
            selected_id = int(customers.iloc[0]["customer_id"])
            customer_row = customers.iloc[[0]]

        customer = customer_row.iloc[0]
        income = float(customer["income"])

        # Existing customer's actual transactions
        tx = transactions[
            transactions["customer_id"] == selected_id
        ].copy()
    
    if request.method == "POST" and request.form.get("action") == "add_transaction":
        date_text = request.form.get("date", "")
        category = request.form.get("category", "Other")
        amount = float(request.form.get("amount", 0))

        if amount > 0 and date_text:
            new_row = pd.DataFrame([{
                "customer_id": selected_id,
                "date": pd.to_datetime(date_text),
                "category": category,
                "amount": amount
            }])
            tx = pd.concat([tx, new_row], ignore_index=True)

    total_spent = float(tx["amount"].sum()) if not tx.empty else 0
    remaining = income - total_spent

    # Budget allocation and category limits
    allocation = budget_allocation(income)
    summary = category_summary(tx)
    spent_by_category = dict(zip(summary["category"], summary["spent"])) if not summary.empty else {}

    category_cards = []
    for category, limit in allocation.items():
        spent = float(spent_by_category.get(category, 0))
        if category == "Savings":
            spent = 0
        remaining_category = limit - spent
        percentage_used = (spent / limit * 100) if limit > 0 else 0
        if percentage_used >= 100:
            status = "Exceeded"
        elif percentage_used >= 80:
            status = "Warning"
        else:
            status = "Within limit"
        category_cards.append({
            "category": category,
            "percentage": BUDGET_RULES[category],
            "limit": money(limit),
            "spent": money(spent),
            "remaining": money(remaining_category),
            "used": round(percentage_used, 1),
            "status": status
        })

    # Weekly and monthly historical summaries
    if not tx.empty:
        tx["week"] = tx["date"].dt.to_period("W").astype(str)
        tx["month"] = tx["date"].dt.to_period("M").astype(str)
        weekly = tx.groupby("week")["amount"].sum().reset_index()
        monthly = tx.groupby("month")["amount"].sum().reset_index()
        weekly_data = [{"label": r["week"], "spent": money(r["amount"])} for _, r in weekly.iterrows()]
        monthly_data = [{"label": r["month"], "spent": money(r["amount"])} for _, r in monthly.iterrows()]
    else:
        weekly_data, monthly_data = [], []

    # Personalized goal
    goal_amount = request.form.get("goal_amount", "")
    goal_months = request.form.get("goal_months", "")
    goal = None

    if goal_amount and goal_months:
        try:
            goal_amount = float(goal_amount)
            goal_months = int(goal_months)
            if goal_amount > 0 and goal_months > 0:
                planned_savings = income * BUDGET_RULES["Savings"] / 100
                existing_goal_savings = max(0, planned_savings)
                monthly_required = goal_amount / goal_months

                # Simulate each month dynamically:
                # each month's actual available saving reduces the remaining goal.
                # For the first month, use the current month's savings capacity.
                # Future months use the same budget capacity unless the goal is
                # already reached. The calculation can be changed to historical
                # monthly savings when more income data is available.
                remaining_goal = goal_amount
                schedule = []
                for month_no in range(1, goal_months + 1):
                    saving_capacity = planned_savings
                    amount_saved = min(saving_capacity, remaining_goal)
                    remaining_goal -= amount_saved
                    schedule.append({
                        "month": month_no,
                        "required": money(monthly_required),
                        "planned": money(saving_capacity),
                        "saved": money(amount_saved),
                        "remaining_goal": money(max(remaining_goal, 0))
                    })
                    if remaining_goal <= 0:
                        break

                achievable = remaining_goal <= 0
                if achievable:
                    goal_message = f"Your current savings allocation can reach the goal within {len(schedule)} month(s)."
                else:
                    extra_total = remaining_goal
                    extra_monthly = extra_total / goal_months
                    goal_message = (
                        f"Current planned savings are not enough. "
                        f"About ₹{money(extra_monthly)} additional saving per month is needed."
                    )

                goal = {
                    "amount": money(goal_amount),
                    "months": goal_months,
                    "monthly_required": money(monthly_required),
                    "planned_savings": money(planned_savings),
                    "achievable": achievable,
                    "message": goal_message,
                    "schedule": schedule,
                }
        except (ValueError, TypeError):
            goal = None

    warning = None
    if allocation["Savings"] > remaining:
        warning = "Your current spending has used more than the amount available after the planned savings allocation."
    elif total_spent >= income:
        warning = "Warning: your spending has reached or exceeded your income."

    return render_template(
        "dashboard.html",
        customers=customers.to_dict("records"),
        customer=customer if isinstance(customer, dict) else customer.to_dict(),
        income=money(income),
        total_spent=money(total_spent),
        remaining=money(remaining),
        spending_percentage=round((total_spent / income * 100) if income else 0, 1),
        allocation=allocation,
        category_cards=category_cards,
        weekly_data=weekly_data,
        monthly_data=monthly_data,
        transactions=tx.sort_values("date", ascending=False).to_dict("records"),
        goal=goal,
        warning=warning,
        categories=list(BUDGET_RULES.keys())[:-1] + ["Other"],
        selected_id=selected_id,
is_new_customer=is_new_customer
    )

if __name__ == "__main__":
    app.run(debug=True)
