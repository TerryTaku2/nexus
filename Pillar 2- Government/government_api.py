"""
Gov API - mock backend
Run: uvicorn government_api:app --reload --port 8002
"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Government Pillar API")
app.mount("/static", StaticFiles(directory="."), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== REQUEST MODELS ====================

class CompanyVerifyRequest(BaseModel):
    company_name: str

class CompanyRegisterRequest(BaseModel):
    company_name: str
    registration_number: str
    owner_name: str
    sector: str

class CompanyUpdateRequest(BaseModel):
    company_name: str
    registration_number: str
    owner_name: str
    sector: str

class TaxReturnRequest(BaseModel):
    tax_period: str
    income_amount: float
    tax_paid: float

class DutyCalculatorRequest(BaseModel):
    product_type: str
    product_value: float

class CustomsStatusRequest(BaseModel):
    clearance_reference: str

class EServiceApplicationRequest(BaseModel):
    service_type: str
    applicant_name: str
    email: str
    details: Optional[str] = None

# ==================== ENDPOINTS ====================

@app.get("/")
async def root():
    return RedirectResponse(url="/static/government.html")

# ===== COMPANY REGISTRAR =====

@app.post("/verify-company")
async def verify_company(request: CompanyVerifyRequest):
    """Mock response: company verification"""
    return {
        "status": "success",
        "message": f"{request.company_name} is registered",
        "registration_status": "Active",
        "verified": True
    }

@app.post("/register-company")
async def register_company(request: CompanyRegisterRequest):
    """Mock response: company registration"""
    return {
        "status": "success",
        "message": "Company registered successfully",
        "registration_number": request.registration_number,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/update-company")
async def update_company(request: CompanyUpdateRequest):
    """Mock response: company update"""
    return {
        "status": "success",
        "message": "Company details updated successfully",
        "registration_number": request.registration_number
    }

# ===== TAX RETURNS =====

@app.post("/file-tax-return")
async def file_tax_return(request: TaxReturnRequest):
    """Mock response: tax return filing"""
    return {
        "status": "success",
        "message": "Tax return filed (demo)",
        "tax_period": request.tax_period,
        "reference_number": "TR-2026-001234"
    }

# ===== IMPORT DUTY CALCULATOR =====

@app.post("/calculate-duty")
async def calculate_duty(request: DutyCalculatorRequest):
    """Mock response: duty estimation (15-25% hardcoded formula)"""
    duty_rate = 0.20  # 20% average
    estimated_duty = request.product_value * duty_rate
    
    return {
        "status": "success",
        "product_type": request.product_type,
        "product_value": request.product_value,
        "duty_rate_percentage": duty_rate * 100,
        "estimated_duty": round(estimated_duty, 2),
        "message": f"Estimated duty: ${estimated_duty:.2f}"
    }

# ===== TAX COMPLIANCE CERTIFICATE =====

@app.post("/request-tcc")
async def request_tcc():
    """Mock response: TCC request"""
    return {
        "status": "success",
        "message": "Your request has been submitted. Processing takes 48 hours (demo)",
        "reference_number": "TCC-2026-005678"
    }

# ===== CUSTOMS CLEARANCE =====

@app.get("/customs-status/{clearance_reference}")
async def customs_status(clearance_reference: str):
    """Mock response: customs clearance status"""
    return {
        "status": "success",
        "clearance_reference": clearance_reference,
        "clearance_status": "In progress — customs check complete (demo)",
        "last_updated": datetime.now().isoformat()
    }

# ===== E-SERVICES =====

@app.post("/e-services/apply")
async def e_services_apply(request: EServiceApplicationRequest):
    """Mock response: e-services application"""
    return {
        "status": "success",
        "message": "Application submitted (demo reference: APP-12345)",
        "service_type": request.service_type,
        "reference_number": "APP-12345",
        "applicant": request.applicant_name
    }

# ===== STATIC DATA ENDPOINTS =====

@app.get("/zimra-status")
async def zimra_status():
    """Static ZIMRA tax status display"""
    return {
        "status": "Paid Up",
        "valid_until": "Dec 2025",
        "message": "Tax status is current"
    }

@app.get("/ministries")
async def get_ministries():
    """Static list of ministries"""
    return {
        "ministries": [
            {
                "name": "Ministry of Industry",
                "contact": "info@industry.gov",
                "services": "policy guidance, licensing, grants"
            },
            {
                "name": "Ministry of Finance",
                "contact": "info@finance.gov",
                "services": "policy guidance, licensing, grants"
            },
            {
                "name": "Ministry of SMEs",
                "contact": "info@smes.gov",
                "services": "policy guidance, licensing, grants"
            },
            {
                "name": "Ministry of ICT",
                "contact": "info@ict.gov",
                "services": "policy guidance, licensing, grants"
            }
        ]
    }

@app.get("/public-notices")
async def get_public_notices():
    """Static public notices"""
    return {
        "notices": [
            {
                "title": "New Business Registration Deadline",
                "content": "All new businesses must register by end of June 2026. Apply through the e-services portal.",
                "date": "2026-05-01"
            },
            {
                "title": "Import Duty Rate Update",
                "content": "Effective June 1, 2026, import duty rates have been updated. See the calculator for current rates.",
                "date": "2026-04-25"
            },
            {
                "title": "SME Tax Incentive Programme",
                "content": "Registered SMEs can now apply for tax incentives. Priority given to tech and manufacturing sectors.",
                "date": "2026-05-10"
            }
        ]
    }

@app.get("/sme-support")
async def get_sme_support():
    """Static SME support programmes"""
    return {
        "programmes": [
            {
                "title": "Export Development Fund",
                "description": "Grants and loans for SMEs looking to expand internationally",
                "eligibility": "Registered SMEs with 2+ years operation"
            },
            {
                "title": "Digital Transformation Grant",
                "description": "Up to 50% funding for technology adoption and digitalization",
                "eligibility": "Manufacturing and services SMEs"
            },
            {
                "title": "Skills Development Programme",
                "description": "Subsidized training for employees in critical areas",
                "eligibility": "All registered SMEs"
            }
        ]
    }
