
from fastapi import FastAPI, Query
import sqlite3

app = FastAPI(title="Search API")


def get_db():
    conn = sqlite3.connect("Nexus.db")
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/api/search")
async def search(q: str = Query(..., min_length=1), user_id: int = Query(...)):
    conn = get_db()
    results = []

    try:
        search_term = f"%{q}%"

        # Search Inventory Products
        products = conn.execute(
            "SELECT id, name, category, current_stock, selling_price FROM Inventory WHERE user_id = ? AND (name LIKE ? OR category LIKE ?)",
            (user_id, search_term, search_term)
        ).fetchall()

        for p in products:
            results.append({
                "type": "product",
                "title": p["name"],
                "subtitle": f"Inventory - {p['category'] or 'Uncategorized'} | Stock: {p['current_stock']} | Price: ${p['selling_price']:.2f}",
                "section": "inventory",
                "id": p["id"]
            })

        # Search Loans
        loans = conn.execute(
            "SELECT id, lender_name, loan_type, principal, status FROM Loans WHERE user_id = ? AND (lender_name LIKE ? OR loan_type LIKE ?)",
            (user_id, search_term, search_term)
        ).fetchall()

        for l in loans:
            results.append({
                "type": "loan",
                "title": f"{l['lender_name']} - {l['loan_type'].capitalize()} Loan",
                "subtitle": f"Principal: ${l['principal']:.2f} | Status: {l['status']}",
                "section": "loans",
                "id": l["id"]
            })

        # Search Sales
        sales = conn.execute(
            "SELECT id, product_name, date FROM Sales WHERE user_id = ? AND product_name LIKE ?",
            (user_id, search_term)
        ).fetchall()

        for s in sales:
            results.append({
                "type": "sale",
                "title": s["product_name"],
                "subtitle": f"Sale recorded on {s['date']}",
                "section": "sales",
                "id": s["id"]
            })

        # Search Bookkeeping Entries
        entries = conn.execute(
            "SELECT id, type, description, amount, date FROM Bookkeeping WHERE user_id = ? AND (description LIKE ? OR type LIKE ?)",
            (user_id, search_term, search_term)
        ).fetchall()

        for e in entries:
            results.append({
                "type": "bookkeeping",
                "title": e["description"] or f"{e['type'].capitalize()} Entry",
                "subtitle": f"{e['type'].capitalize()} | ${e['amount']:.2f} | {e['date']}",
                "section": "bookkeeping",
                "id": e["id"]
            })

        # Search Suppliers/Wholesalers (hardcoded directory)
        suppliers = [
            {"name": "ABC Wholesalers", "category": "Groceries", "contact": "abc@example.com"},
            {"name": "Tech Distributors Zimbabwe", "category": "Electronics", "contact": "tech@example.com"},
            {"name": "Fashion Hub Wholesale", "category": "Clothing", "contact": "fashion@example.com"},
            {"name": "BuildBase Materials", "category": "Construction", "contact": "build@example.com"},
            {"name": "Fresh Foods Supply Co", "category": "Food & Beverage", "contact": "fresh@example.com"},
            {"name": "Office Essentials Ltd", "category": "Stationery", "contact": "office@example.com"},
            {"name": "Auto Parts Direct", "category": "Automotive", "contact": "auto@example.com"},
            {"name": "Pharma Wholesale ZW", "category": "Pharmaceuticals", "contact": "pharma@example.com"},
            {"name": "Farm Equipment Suppliers", "category": "Agriculture", "contact": "farm@example.com"},
            {"name": "Global Trade Imports", "category": "General Merchandise", "contact": "global@example.com"},
        ]

        for supplier in suppliers:
            if q.lower() in supplier["name"].lower() or q.lower() in supplier["category"].lower():
                results.append({
                    "type": "supplier",
                    "title": supplier["name"],
                    "subtitle": f"Category: {supplier['category']} | Contact: {supplier['contact']}",
                    "section": "commerce",
                    "id": None
                })

        # Search Guides/Help (hardcoded)
        guides = [
            {"title": "How to Apply for a Business Loan", "section": "loans",
             "keywords": "loan,borrow,finance,funding"},
            {"title": "Registering Your Business in Zimbabwe", "section": "gov",
             "keywords": "register,business,company,registration"},
            {"title": "Understanding Import Duties", "section": "gov", "keywords": "import,duty,customs,tax,SA,China"},
            {"title": "Tax Filing Guide for SMEs", "section": "gov", "keywords": "tax,ZIMRA,filing,returns"},
            {"title": "How to Export Products", "section": "commerce", "keywords": "export,sell,international,buyer"},
            {"title": "Inventory Management Tips", "section": "inventory",
             "keywords": "stock,inventory,manage,reorder"},
            {"title": "P2P Lending Explained", "section": "finance", "keywords": "p2p,lending,borrow,lend,peer"},
        ]

        for guide in guides:
            if q.lower() in guide["title"].lower() or q.lower() in guide["keywords"]:
                results.append({
                    "type": "guide",
                    "title": guide["title"],
                    "subtitle": f"Navigate to {guide['section'].capitalize()} section to learn more",
                    "section": guide["section"],
                    "id": None
                })

        return {"query": q, "results": results}

    finally:
        conn.close()


@app.get("/api/market-prices")
async def market_prices():
    return {
        "updated": "2025-06-15",
        "disclaimer": "Demo data for prototype purposes only",
        "commodities": [
            {"name": "Maize", "unit": "ton", "price": 450.00, "trend": "up", "change": "+2.3%"},
            {"name": "Wheat", "unit": "ton", "price": 520.00, "trend": "stable", "change": "0%"},
            {"name": "Tomatoes", "unit": "kg", "price": 2.00, "trend": "down", "change": "-5.1%"},
            {"name": "Cooking Oil", "unit": "20L", "price": 35.00, "trend": "up", "change": "+1.8%"},
            {"name": "Sugar", "unit": "ton", "price": 680.00, "trend": "stable", "change": "0%"},
            {"name": "Beef", "unit": "kg", "price": 6.50, "trend": "up", "change": "+3.2%"},
            {"name": "Chicken", "unit": "kg", "price": 4.80, "trend": "down", "change": "-1.5%"},
            {"name": "Rice", "unit": "ton", "price": 550.00, "trend": "stable", "change": "0%"},
        ],
        "fuel": [
            {"name": "Diesel", "unit": "litre", "price": 1.75, "trend": "stable"},
            {"name": "Petrol", "unit": "litre", "price": 1.68, "trend": "up"},
        ],
        "forex": [
            {"name": "USD/ZWL", "rate": "1:6200", "trend": "volatile"},
            {"name": "ZAR/USD", "rate": "18.50", "trend": "stable"},
        ]
    }


@app.get("/api/trending-searches")
async def trending_searches():
    return {
        "topics": [
            {
                "query": "How to export to South Africa",
                "answer": "To export products to South Africa, you need: 1) Business registration certificate, 2) Export permit from the Ministry of Industry, 3) Customs clearance documents. Our Import from SA tool can help connect you with trade partners. Navigate to Commerce → Import from South Africa to get started.",
                "navigateTo": "commerce",
                "actionText": "Go to Import from SA"
            },
            {
                "query": "Cheapest business loans",
                "answer": "Based on current offerings: Microfinance institutions offer small loans ($200-$2,000) at 15-25% interest. Commercial banks offer larger amounts ($5,000-$100,000) at 10-18% interest. P2P lending can offer competitive rates depending on your business profile. Check the Finance → Loan Calculator to compare options.",
                "navigateTo": "loans",
                "actionText": "Calculate Loan Options"
            },
            {
                "query": "Register my small business",
                "answer": "To register your business in Zimbabwe, you need to: 1) Choose a business name, 2) Register with the Companies Registry, 3) Get a tax clearance certificate from ZIMRA. Navigate to Gov → Company Registrar to start the registration process.",
                "navigateTo": "gov",
                "actionText": "Register Business"
            },
        ]
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)