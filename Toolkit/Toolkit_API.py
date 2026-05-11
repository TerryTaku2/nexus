# toolkit.py
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
import sqlite3
from math import ceil

app = FastAPI(title="NeXus Toolkit API")


# ============ Database Helper ============
def get_db():
    conn = sqlite3.connect("Nexus.db")
    conn.row_factory = sqlite3.Row
    return conn


# ============ Pydantic Models ============

# Inventory Models
class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1)
    category: Optional[str] = None
    unit: Optional[str] = None
    current_stock: float = 0
    reorder_level: float = 0
    cost_price: float = 0
    selling_price: float = 0


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    current_stock: Optional[float] = None
    reorder_level: Optional[float] = None
    cost_price: Optional[float] = None
    selling_price: Optional[float] = None


# Loan Models
class LoanCreate(BaseModel):
    lender_name: str = Field(..., min_length=1)
    loan_type: str = Field(..., pattern="^(business|personal|microfinance|p2p)$")
    principal: float = Field(..., gt=0)
    interest_rate: float = Field(..., ge=0)
    term_months: int = Field(..., gt=0)
    start_date: str
    notes: Optional[str] = None


class LoanUpdate(BaseModel):
    interest_rate: Optional[float] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class PaymentCreate(BaseModel):
    amount: float = Field(..., gt=0)
    payment_date: str
    reference: Optional[str] = None


# Sales Models
class SaleCreate(BaseModel):
    product_name: str = Field(..., min_length=1)
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    unit_cost: float = Field(..., ge=0)
    date: str


# Expense Models
class ExpenseCreate(BaseModel):
    category: str = Field(..., pattern="^(Rent|Utilities|Salaries|Transport|Marketing|Inventory|Other)$")
    description: Optional[str] = None
    amount: float = Field(..., gt=0)
    date: str


# Capital Models
class CapitalCreate(BaseModel):
    amount: float = Field(..., gt=0)
    date: str
    notes: Optional[str] = None


# Bookkeeping Models
class BookkeepingEntry(BaseModel):
    description: Optional[str] = None
    amount: float = Field(..., gt=0)
    date: str
    category: Optional[str] = None
    supplier: Optional[str] = None


# Calculator Models
class LoanCalculatorRequest(BaseModel):
    principal: float = Field(..., gt=0)
    rate: float = Field(..., ge=0)
    term_months: int = Field(..., gt=0)


# ============ INVENTORY MANAGEMENT ============

@app.get("/api/inventory/summary")
async def inventory_summary(user_id: int = Query(...)):
    conn = get_db()
    try:
        products = conn.execute(
            "SELECT current_stock, cost_price, selling_price FROM Inventory WHERE user_id = ?",
            (user_id,)
        ).fetchall()

        item_count = len(products)
        stock_value = sum(p["current_stock"] * p["cost_price"] for p in products)
        potential_value = sum(p["current_stock"] * p["selling_price"] for p in products)

        return {
            "itemCount": item_count,
            "stockValue": round(stock_value, 2),
            "potentialValue": round(potential_value, 2)
        }
    finally:
        conn.close()


@app.get("/api/inventory/products")
async def list_products(user_id: int = Query(...)):
    conn = get_db()
    try:
        products = conn.execute(
            "SELECT * FROM Inventory WHERE user_id = ? ORDER BY name",
            (user_id,)
        ).fetchall()
        return [dict(p) for p in products]
    finally:
        conn.close()


@app.post("/api/inventory/products")
async def create_product(product: ProductCreate, user_id: int = Query(...)):
    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO Inventory (user_id, name, category, unit, current_stock, 
               reorder_level, cost_price, selling_price)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, product.name, product.category, product.unit,
             product.current_stock, product.reorder_level, product.cost_price, product.selling_price)
        )
        conn.commit()

        new_product = conn.execute(
            "SELECT * FROM Inventory WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()

        return dict(new_product)
    finally:
        conn.close()


@app.put("/api/inventory/products/{product_id}")
async def update_product(product_id: int, updates: ProductUpdate):
    conn = get_db()
    try:
        existing = conn.execute("SELECT * FROM Inventory WHERE id = ?", (product_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Product not found")

        update_fields = {}
        for field, value in updates.dict(exclude_unset=True).items():
            update_fields[field] = value

        if update_fields:
            set_clause = ", ".join(f"{k} = ?" for k in update_fields.keys())
            values = list(update_fields.values()) + [product_id]
            conn.execute(f"UPDATE Inventory SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", values)
            conn.commit()

        updated = conn.execute("SELECT * FROM Inventory WHERE id = ?", (product_id,)).fetchone()
        return dict(updated)
    finally:
        conn.close()


@app.delete("/api/inventory/products/{product_id}")
async def delete_product(product_id: int):
    conn = get_db()
    try:
        conn.execute("DELETE FROM Inventory WHERE id = ?", (product_id,))
        conn.commit()
        return {"message": "Product deleted"}
    finally:
        conn.close()


@app.get("/api/inventory/alerts")
async def inventory_alerts(user_id: int = Query(...)):
    conn = get_db()
    try:
        alerts = conn.execute(
            "SELECT id, name, current_stock, reorder_level FROM Inventory WHERE user_id = ? AND current_stock <= reorder_level",
            (user_id,)
        ).fetchall()
        return [dict(a) for a in alerts]
    finally:
        conn.close()


# ============ LOAN TRACKER ============

@app.get("/api/loans/summary")
async def loans_summary(user_id: int = Query(...)):
    conn = get_db()
    try:
        loans = conn.execute(
            "SELECT principal, amount_paid, status FROM Loans WHERE user_id = ?",
            (user_id,)
        ).fetchall()

        outstanding = sum(l["principal"] - l["amount_paid"] for l in loans if l["status"] == 'active')
        paid = sum(l["amount_paid"] for l in loans)

        return {"outstanding": round(outstanding, 2), "paid": round(paid, 2)}
    finally:
        conn.close()


@app.get("/api/loans")
async def list_loans(user_id: int = Query(...)):
    conn = get_db()
    try:
        loans = conn.execute(
            "SELECT * FROM Loans WHERE user_id = ? ORDER BY start_date DESC",
            (user_id,)
        ).fetchall()
        return [dict(l) for l in loans]
    finally:
        conn.close()


@app.get("/api/loans/{loan_id}")
async def get_loan(loan_id: int):
    conn = get_db()
    try:
        loan = conn.execute("SELECT * FROM Loans WHERE id = ?", (loan_id,)).fetchone()
        if not loan:
            raise HTTPException(status_code=404, detail="Loan not found")

        # Calculate payment schedule
        monthly_rate = loan["interest_rate"] / 100 / 12
        n = loan["term_months"]

        if monthly_rate > 0:
            monthly_payment = loan["principal"] * (monthly_rate * (1 + monthly_rate) ** n) / (
                        (1 + monthly_rate) ** n - 1)
        else:
            monthly_payment = loan["principal"] / n

        schedule = []
        remaining = loan["principal"]
        for month in range(1, n + 1):
            interest = remaining * monthly_rate
            principal_payment = monthly_payment - interest
            remaining -= principal_payment
            schedule.append({
                "month": month,
                "payment": round(monthly_payment, 2),
                "interest": round(interest, 2),
                "principal": round(principal_payment, 2),
                "remainingBalance": round(max(0, remaining), 2)
            })

        payments = conn.execute(
            "SELECT * FROM Loan_Payments WHERE loan_id = ? ORDER BY payment_date",
            (loan_id,)
        ).fetchall()

        result = dict(loan)
        result["paymentSchedule"] = schedule
        result["payments"] = [dict(p) for p in payments]

        return result
    finally:
        conn.close()


@app.post("/api/loans")
async def create_loan(loan: LoanCreate, user_id: int = Query(...)):
    conn = get_db()
    try:
        cursor = conn.execute(
            """INSERT INTO Loans (user_id, lender_name, loan_type, principal, interest_rate, 
               term_months, start_date, notes, next_due_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, loan.lender_name, loan.loan_type, loan.principal, loan.interest_rate,
             loan.term_months, loan.start_date, loan.notes,
             (datetime.strptime(loan.start_date, "%Y-%m-%d") + timedelta(days=30)).strftime("%Y-%m-%d"))
        )
        conn.commit()

        new_loan = conn.execute("SELECT * FROM Loans WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(new_loan)
    finally:
        conn.close()


@app.post("/api/loans/{loan_id}/payments")
async def record_payment(loan_id: int, payment: PaymentCreate):
    conn = get_db()
    try:
        loan = conn.execute("SELECT * FROM Loans WHERE id = ?", (loan_id,)).fetchone()
        if not loan:
            raise HTTPException(status_code=404, detail="Loan not found")

        conn.execute(
            "INSERT INTO Loan_Payments (loan_id, amount, payment_date, reference) VALUES (?, ?, ?, ?)",
            (loan_id, payment.amount, payment.payment_date, payment.reference)
        )

        new_amount_paid = loan["amount_paid"] + payment.amount

        # Auto-complete if fully paid
        status = loan["status"]
        if new_amount_paid >= loan["principal"]:
            status = "completed"

        # Update next due date
        next_due = (datetime.strptime(payment.payment_date, "%Y-%m-%d") + timedelta(days=30)).strftime("%Y-%m-%d")

        conn.execute(
            "UPDATE Loans SET amount_paid = ?, status = ?, next_due_date = ? WHERE id = ?",
            (new_amount_paid, status, next_due, loan_id)
        )
        conn.commit()

        updated_loan = conn.execute("SELECT * FROM Loans WHERE id = ?", (loan_id,)).fetchone()
        return dict(updated_loan)
    finally:
        conn.close()


@app.get("/api/loans/overdue")
async def overdue_loans(user_id: int = Query(...)):
    conn = get_db()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        loans = conn.execute(
            "SELECT * FROM Loans WHERE user_id = ? AND status = 'active' AND next_due_date < ?",
            (user_id, today)
        ).fetchall()

        overdue_list = []
        for loan in loans:
            days_overdue = (datetime.now() - datetime.strptime(loan["next_due_date"], "%Y-%m-%d")).days
            overdue_list.append({
                "id": loan["id"],
                "lenderName": loan["lender_name"],
                "overdueAmount": round(loan["principal"] - loan["amount_paid"], 2),
                "daysOverdue": days_overdue
            })

        return overdue_list
    finally:
        conn.close()


@app.put("/api/loans/{loan_id}")
async def update_loan(loan_id: int, updates: LoanUpdate):
    conn = get_db()
    try:
        existing = conn.execute("SELECT * FROM Loans WHERE id = ?", (loan_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Loan not found")

        update_fields = {}
        for field, value in updates.dict(exclude_unset=True).items():
            update_fields[field] = value

        if update_fields:
            set_clause = ", ".join(f"{k} = ?" for k in update_fields.keys())
            values = list(update_fields.values()) + [loan_id]
            conn.execute(f"UPDATE Loans SET {set_clause} WHERE id = ?", values)
            conn.commit()

        updated = conn.execute("SELECT * FROM Loans WHERE id = ?", (loan_id,)).fetchone()
        return dict(updated)
    finally:
        conn.close()


@app.delete("/api/loans/{loan_id}")
async def delete_loan(loan_id: int):
    conn = get_db()
    try:
        conn.execute("DELETE FROM Loans WHERE id = ?", (loan_id,))
        conn.commit()
        return {"message": "Loan deleted"}
    finally:
        conn.close()


# ============ FINANCE TRACK ============

@app.get("/api/finance/dashboard")
async def finance_dashboard(user_id: int = Query(...)):
    conn = get_db()
    try:
        sales = conn.execute(
            "SELECT quantity, unit_price, unit_cost FROM Sales WHERE user_id = ?",
            (user_id,)
        ).fetchall()

        expenses = conn.execute(
            "SELECT amount FROM Expenses WHERE user_id = ?",
            (user_id,)
        ).fetchall()

        total_revenue = sum(s["quantity"] * s["unit_price"] for s in sales)
        total_cost = sum(s["quantity"] * s["unit_cost"] for s in sales)
        total_expenses = sum(e["amount"] for e in expenses)

        gross_profit = total_revenue - total_cost
        net_profit = gross_profit - total_expenses
        margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0

        return {
            "revenue": round(total_revenue, 2),
            "expenses": round(total_expenses, 2),
            "netProfit": round(net_profit, 2),
            "grossProfit": round(gross_profit, 2),
            "margin": round(margin, 1)
        }
    finally:
        conn.close()


@app.get("/api/finance/sales")
async def list_sales(user_id: int = Query(...)):
    conn = get_db()
    try:
        sales = conn.execute(
            """SELECT *, (quantity * unit_price) as total_revenue,
               (quantity * unit_cost) as total_cost,
               (quantity * (unit_price - unit_cost)) as profit
               FROM Sales WHERE user_id = ? ORDER BY date DESC""",
            (user_id,)
        ).fetchall()
        return [dict(s) for s in sales]
    finally:
        conn.close()


@app.post("/api/finance/sales")
async def record_sale(sale: SaleCreate, user_id: int = Query(...)):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO Sales (user_id, product_name, quantity, unit_price, unit_cost, date) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, sale.product_name, sale.quantity, sale.unit_price, sale.unit_cost, sale.date)
        )
        conn.commit()

        new_sale = conn.execute("SELECT * FROM Sales WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(new_sale)
    finally:
        conn.close()


@app.get("/api/finance/expenses")
async def list_expenses(user_id: int = Query(...)):
    conn = get_db()
    try:
        expenses = conn.execute(
            "SELECT * FROM Expenses WHERE user_id = ? ORDER BY date DESC",
            (user_id,)
        ).fetchall()
        return [dict(e) for e in expenses]
    finally:
        conn.close()


@app.post("/api/finance/expenses")
async def record_expense(expense: ExpenseCreate, user_id: int = Query(...)):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO Expenses (user_id, category, description, amount, date) VALUES (?, ?, ?, ?, ?)",
            (user_id, expense.category, expense.description, expense.amount, expense.date)
        )
        conn.commit()

        new_expense = conn.execute("SELECT * FROM Expenses WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(new_expense)
    finally:
        conn.close()


@app.get("/api/finance/capital")
async def list_capital(user_id: int = Query(...)):
    conn = get_db()
    try:
        capital = conn.execute(
            "SELECT * FROM Capital WHERE user_id = ? ORDER BY date DESC",
            (user_id,)
        ).fetchall()
        return [dict(c) for c in capital]
    finally:
        conn.close()


@app.post("/api/finance/capital")
async def add_capital(capital: CapitalCreate, user_id: int = Query(...)):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO Capital (user_id, amount, date, notes) VALUES (?, ?, ?, ?)",
            (user_id, capital.amount, capital.date, capital.notes)
        )
        conn.commit()

        new_capital = conn.execute("SELECT * FROM Capital WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(new_capital)
    finally:
        conn.close()


@app.get("/api/finance/insights")
async def finance_insights(user_id: int = Query(...)):
    conn = get_db()
    try:
        # Get current month sales
        current_month = datetime.now().strftime("%Y-%m")
        sales = conn.execute(
            "SELECT * FROM Sales WHERE user_id = ? AND date LIKE ?",
            (user_id, f"{current_month}%")
        ).fetchall()

        messages = []

        if len(sales) == 0:
            messages.append("No sales recorded this month. Start logging your sales to get insights!")
        else:
            total_revenue = sum(s["quantity"] * s["unit_price"] for s in sales)
            messages.append(f"You've made ${total_revenue:,.2f} in sales this month.")

        # Check inventory alerts
        alerts = conn.execute(
            "SELECT name, current_stock, reorder_level FROM Inventory WHERE user_id = ? AND current_stock <= reorder_level",
            (user_id,)
        ).fetchall()

        for alert in alerts:
            messages.append(
                f"⚠️ {alert['name']} is low on stock ({alert['current_stock']} units, reorder at {alert['reorder_level']})")

        if not alerts:
            messages.append("Inventory levels are healthy.")

        # Check overdue loans
        today = datetime.now().strftime("%Y-%m-%d")
        overdue = conn.execute(
            "SELECT * FROM Loans WHERE user_id = ? AND status = 'active' AND next_due_date < ?",
            (user_id, today)
        ).fetchall()

        if overdue:
            messages.append(f"⚠️ You have {len(overdue)} overdue loan payment(s). Review your loans section.")
        else:
            messages.append("All loan payments are up to date.")

        return {"messages": messages}
    finally:
        conn.close()


@app.get("/api/finance/report")
async def finance_report(user_id: int = Query(...), period: str = Query("month")):
    conn = get_db()
    try:
        if period == "month":
            date_filter = datetime.now().strftime("%Y-%m")
        elif period == "year":
            date_filter = datetime.now().strftime("%Y")
        else:
            date_filter = datetime.now().strftime("%Y-%m")

        sales = conn.execute(
            "SELECT * FROM Sales WHERE user_id = ? AND date LIKE ?",
            (user_id, f"{date_filter}%")
        ).fetchall()

        expenses = conn.execute(
            "SELECT * FROM Expenses WHERE user_id = ? AND date LIKE ?",
            (user_id, f"{date_filter}%")
        ).fetchall()

        revenue = sum(s["quantity"] * s["unit_price"] for s in sales)
        total_expenses = sum(e["amount"] for e in expenses)
        net_profit = revenue - total_expenses

        # Chart data grouped by day
        chart_data = {}
        for s in sales:
            day = s["date"]
            if day not in chart_data:
                chart_data[day] = {"revenue": 0, "expenses": 0}
            chart_data[day]["revenue"] += s["quantity"] * s["unit_price"]

        for e in expenses:
            day = e["date"]
            if day not in chart_data:
                chart_data[day] = {"revenue": 0, "expenses": 0}
            chart_data[day]["expenses"] += e["amount"]

        return {
            "period": period,
            "revenue": round(revenue, 2),
            "expenses": round(total_expenses, 2),
            "netProfit": round(net_profit, 2),
            "chartData": {k: v for k, v in sorted(chart_data.items())}
        }
    finally:
        conn.close()


# ============ BOOKKEEPING ============

@app.get("/api/bookkeeping/summary")
async def bookkeeping_summary(user_id: int = Query(...)):
    conn = get_db()
    try:
        entries = conn.execute(
            "SELECT type, amount FROM Bookkeeping WHERE user_id = ?",
            (user_id,)
        ).fetchall()

        total_sales = sum(e["amount"] for e in entries if e["type"] == "sale")
        total_purchases = sum(e["amount"] for e in entries if e["type"] == "purchase")
        total_expenses = sum(e["amount"] for e in entries if e["type"] == "expense")

        return {
            "totalSales": round(total_sales, 2),
            "totalPurchases": round(total_purchases, 2),
            "totalExpenses": round(total_expenses, 2)
        }
    finally:
        conn.close()


@app.get("/api/bookkeeping/entries")
async def list_bookkeeping_entries(user_id: int = Query(...), type: Optional[str] = Query(None)):
    conn = get_db()
    try:
        if type:
            entries = conn.execute(
                "SELECT * FROM Bookkeeping WHERE user_id = ? AND type = ? ORDER BY date DESC",
                (user_id, type)
            ).fetchall()
        else:
            entries = conn.execute(
                "SELECT * FROM Bookkeeping WHERE user_id = ? ORDER BY date DESC",
                (user_id,)
            ).fetchall()
        return [dict(e) for e in entries]
    finally:
        conn.close()


@app.post("/api/bookkeeping/entries/sale")
async def bookkeeping_sale(entry: BookkeepingEntry, user_id: int = Query(...)):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO Bookkeeping (user_id, type, description, amount, date, category) VALUES (?, 'sale', ?, ?, ?, ?)",
            (user_id, entry.description, entry.amount, entry.date, entry.category)
        )
        conn.commit()

        new_entry = conn.execute("SELECT * FROM Bookkeeping WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(new_entry)
    finally:
        conn.close()


@app.post("/api/bookkeeping/entries/purchase")
async def bookkeeping_purchase(entry: BookkeepingEntry, user_id: int = Query(...)):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO Bookkeeping (user_id, type, description, amount, date, supplier) VALUES (?, 'purchase', ?, ?, ?, ?)",
            (user_id, entry.description, entry.amount, entry.date, entry.supplier)
        )
        conn.commit()

        new_entry = conn.execute("SELECT * FROM Bookkeeping WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(new_entry)
    finally:
        conn.close()


@app.post("/api/bookkeeping/entries/expense")
async def bookkeeping_expense(entry: BookkeepingEntry, user_id: int = Query(...)):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO Bookkeeping (user_id, type, description, amount, date, category) VALUES (?, 'expense', ?, ?, ?, ?)",
            (user_id, entry.description, entry.amount, entry.date, entry.category)
        )
        conn.commit()

        new_entry = conn.execute("SELECT * FROM Bookkeeping WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return dict(new_entry)
    finally:
        conn.close()


@app.delete("/api/bookkeeping/entries/{entry_id}")
async def delete_bookkeeping_entry(entry_id: int):
    conn = get_db()
    try:
        conn.execute("DELETE FROM Bookkeeping WHERE id = ?", (entry_id,))
        conn.commit()
        return {"message": "Entry deleted"}
    finally:
        conn.close()


@app.get("/api/bookkeeping/profit")
async def bookkeeping_profit(user_id: int = Query(...)):
    conn = get_db()
    try:
        entries = conn.execute(
            "SELECT type, amount FROM Bookkeeping WHERE user_id = ?",
            (user_id,)
        ).fetchall()

        sales = sum(e["amount"] for e in entries if e["type"] == "sale")
        purchases = sum(e["amount"] for e in entries if e["type"] == "purchase")
        expenses = sum(e["amount"] for e in entries if e["type"] == "expense")

        profit = sales - purchases - expenses
        margin = (profit / sales * 100) if sales > 0 else 0

        return {"profit": round(profit, 2), "margin": round(margin, 1)}
    finally:
        conn.close()


# ============ LOAN CALCULATOR ============

@app.post("/api/calculator/loan")
async def calculate_loan(request: LoanCalculatorRequest):
    monthly_rate = request.rate / 100 / 12
    n = request.term_months

    if monthly_rate > 0:
        monthly_payment = request.principal * (monthly_rate * (1 + monthly_rate) ** n) / ((1 + monthly_rate) ** n - 1)
    else:
        monthly_payment = request.principal / n

    total_payment = monthly_payment * n
    total_interest = total_payment - request.principal

    schedule = []
    remaining = request.principal
    for month in range(1, n + 1):
        interest = remaining * monthly_rate
        principal_payment = monthly_payment - interest
        remaining -= principal_payment
        schedule.append({
            "month": month,
            "payment": round(monthly_payment, 2),
            "interest": round(interest, 2),
            "principal": round(principal_payment, 2),
            "remainingBalance": round(max(0, remaining), 2)
        })

    return {
        "monthlyPayment": round(monthly_payment, 2),
        "totalInterest": round(total_interest, 2),
        "totalPayment": round(total_payment, 2),
        "schedule": schedule
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)