SMART SPEND - SIMPLE VERSION

Project structure:
Smart Spend/
  app.py
  customers.csv
  transactions.csv
  requirements.txt
  templates/
    dashboard.html

How to run:
1. Open this folder in Antigravity.
2. Open Terminal.
3. Run:
   python -m pip install -r requirements.txt
4. Run:
   python app.py
5. Open:
   http://127.0.0.1:5000

Features:
- Customer dataset with name, age, occupation and income.
- Customer selection.
- Percentage-based budget allocation.
- Transaction categorization.
- Category limit, spent, remaining and warning/exceeded status.
- Weekly and monthly spending charts.
- Personalized savings goal.
- Dynamic goal schedule.
- No login system.
- No database required for the starter version.

Important:
Transactions added through the browser are kept only for the current page/session in this starter version.
For a final college project, replace the CSV layer with SQLite and persist new transactions/goals.
