from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(name = "Calculations API")


class DutyCalculationRequest(BaseModel):
    product_type: str = Field(..., min_length=1)
    value: float = Field(..., gt=0)


class DutyCalculationResponse(BaseModel):
    product_type: str
    value: float
    duty_rate: float
    duty_amount: float
    breakdown: str


class InstallmentCalculationRequest(BaseModel):
    item_price: float = Field(..., gt=0)
    term_months: int = Field(..., ge=6, le=24)


class InstallmentCalculationResponse(BaseModel):
    item_price: float
    term_months: int
    interest_rate: float
    total_interest: float
    total_cost: float
    monthly_payment: float
    breakdown: str


@app.post("/api/calculate-duty", response_model=DutyCalculationResponse)
async def calculate_import_duty(request: DutyCalculationRequest):
    duty_rates = {
        "electronics": 0.25,
        "clothing": 0.20,
        "machinery": 0.15,
        "raw materials": 0.10,
        "food": 0.18,
        "vehicles": 0.25,
        "furniture": 0.20,
        "chemicals": 0.15,
    }

    product_lower = request.product_type.lower().strip()
    duty_rate = 0.20  # default

    for category, rate in duty_rates.items():
        if category in product_lower or product_lower in category:
            duty_rate = rate
            break

    duty_amount = round(request.value * duty_rate, 2)

    return DutyCalculationResponse(
        product_type=request.product_type,
        value=request.value,
        duty_rate=duty_rate * 100,
        duty_amount=duty_amount,
        breakdown=f"Value: ${request.value:,.2f} × Duty Rate: {duty_rate * 100}% = Duty: ${duty_amount:,.2f}"
    )


@app.post("/api/calculate-installments", response_model=InstallmentCalculationResponse)
async def calculate_hire_purchase(request: InstallmentCalculationRequest):
    if request.term_months <= 6:
        interest_rate = 0.12
    elif request.term_months <= 12:
        interest_rate = 0.15
    else:
        interest_rate = 0.18

    total_interest = round(request.item_price * interest_rate, 2)
    total_cost = round(request.item_price + total_interest, 2)
    monthly_payment = round(total_cost / request.term_months, 2)

    return InstallmentCalculationResponse(
        item_price=request.item_price,
        term_months=request.term_months,
        interest_rate=interest_rate * 100,
        total_interest=total_interest,
        total_cost=total_cost,
        monthly_payment=monthly_payment,
        breakdown=(
            f"Item Price: ${request.item_price:,.2f}\n"
            f"Term: {request.term_months} months\n"
            f"Interest Rate: {interest_rate * 100}%\n"
            f"Total Interest: ${total_interest:,.2f}\n"
            f"Total Cost: ${total_cost:,.2f}\n"
            f"Monthly Payment: ${monthly_payment:,.2f}"
        )
    )