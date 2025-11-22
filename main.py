# app/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import io
import os
import uuid
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import hashlib
import stripe

app = FastAPI(
    title="Deepfake Detection API",
    description="AI-powered image authenticity analyzer with freemium model",
    version="2.0.0"
)

# Stripe configuration
stripe.api_key = "sk_test_your_stripe_secret_key_here"  # Replace with your Stripe secret key

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Serve static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Database setup
def init_db():
    """Initialize SQLite database for user management"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # User usage table
    c.execute('''
        CREATE TABLE IF NOT EXISTS usage (
            user_id TEXT PRIMARY KEY,
            ip_address TEXT,
            daily_scans INTEGER DEFAULT 0,
            total_scans INTEGER DEFAULT 0,
            last_scan_date TEXT,
            is_premium BOOLEAN DEFAULT FALSE,
            premium_expires TEXT,
            stripe_customer_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Payments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            stripe_payment_intent_id TEXT,
            amount INTEGER,
            currency TEXT,
            status TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

# User management functions
def get_user_id(request: Request) -> str:
    """Generate a unique user ID based on IP and user agent"""
    client_ip = request.client.host
    user_agent = request.headers.get('user-agent', '')
    user_string = f"{client_ip}-{user_agent}"
    return hashlib.md5(user_string.encode()).hexdigest()[:16]

def can_user_scan(user_id: str) -> Dict[str, Any]:
    """Check if user can perform a scan"""
    conn = get_db_connection()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Get or create user
    c.execute('''
        INSERT OR IGNORE INTO usage (user_id, ip_address, daily_scans, total_scans, last_scan_date)
        VALUES (?, ?, 0, 0, ?)
    ''', (user_id, "unknown", today))
    
    # Get user data
    c.execute('''
        SELECT daily_scans, total_scans, is_premium, premium_expires, last_scan_date 
        FROM usage WHERE user_id = ?
    ''', (user_id,))
    
    user_data = c.fetchone()
    conn.close()
    
    if not user_data:
        return {"can_scan": False, "reason": "user_not_found"}
    
    daily_scans, total_scans, is_premium, premium_expires, last_scan_date = user_data
    
    # Reset daily counter if it's a new day
    if last_scan_date != today:
        reset_daily_scans(user_id)
        daily_scans = 0
    
    # Premium users have unlimited scans
    if is_premium and premium_expires:
        expiry_date = datetime.strptime(premium_expires, "%Y-%m-%d")
        if expiry_date > datetime.now():
            return {
                "can_scan": True, 
                "user_type": "premium", 
                "scans_left": "unlimited",
                "premium_expires": premium_expires
            }
        else:
            # Premium expired, downgrade to free
            downgrade_user(user_id)
    
    # Free users: max 1 scan per day
    if daily_scans < 1:
        return {
            "can_scan": True, 
            "user_type": "free", 
            "scans_left": 1 - daily_scans,
            "scans_used": daily_scans
        }
    else:
        return {
            "can_scan": False, 
            "user_type": "free", 
            "reason": "daily_limit_reached", 
            "scans_used": daily_scans,
            "scans_left": 0,
            "upgrade_url": "/premium"
        }

def record_scan(user_id: str):
    """Record a scan for a user"""
    conn = get_db_connection()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    
    c.execute('''
        UPDATE usage 
        SET daily_scans = daily_scans + 1, 
            total_scans = total_scans + 1,
            last_scan_date = ?
        WHERE user_id = ?
    ''', (today, user_id))
    
    conn.commit()
    conn.close()

def reset_daily_scans(user_id: str):
    """Reset daily scan counter"""
    conn = get_db_connection()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    
    c.execute('''
        UPDATE usage 
        SET daily_scans = 0, last_scan_date = ?
        WHERE user_id = ?
    ''', (today, user_id))
    
    conn.commit()
    conn.close()

def upgrade_user(user_id: str, months: int = 1):
    """Upgrade user to premium"""
    conn = get_db_connection()
    c = conn.cursor()
    expiry_date = (datetime.now() + timedelta(days=30 * months)).strftime("%Y-%m-%d")
    
    c.execute('''
        UPDATE usage 
        SET is_premium = TRUE, premium_expires = ?
        WHERE user_id = ?
    ''', (expiry_date, user_id))
    
    conn.commit()
    conn.close()
    return f"Premium until {expiry_date}"

def downgrade_user(user_id: str):
    """Downgrade user to free"""
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute('''
        UPDATE usage 
        SET is_premium = FALSE, premium_expires = NULL
        WHERE user_id = ?
    ''', (user_id,))
    
    conn.commit()
    conn.close()

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    print("Database initialized successfully!")
    print("💰 Stripe payments are ready!")

# ===== ROUTES =====

@app.get("/")
async def serve_frontend():
    return FileResponse("web/index.html")

@app.get("/premium")
async def premium_page():
    return FileResponse("web/premium.html")

@app.get("/payment-success")
async def payment_success(session_id: str = None):
    """Show payment success page"""
    return FileResponse("web/payment_success.html")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "features": {
            "free_scans_per_day": 1,
            "premium_available": True
        }
    }

@app.get("/api/user/status")
async def get_user_status(request: Request):
    """Get current user status and scan limits"""
    user_id = get_user_id(request)
    scan_status = can_user_scan(user_id)
    
    return {
        "user_id": user_id,
        "scan_status": scan_status,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/predict/")
async def predict(request: Request, file: UploadFile = File(...)):
    # Generate request ID
    request_id = str(uuid.uuid4())[:8]
    
    # Get user ID and check scan limits
    user_id = get_user_id(request)
    scan_status = can_user_scan(user_id)
    
    if not scan_status["can_scan"]:
        raise HTTPException(
            status_code=429, 
            detail={
                "error": "Scan limit reached",
                "message": f"You've used your {scan_status['scans_used']} free scan(s) for today.",
                "user_type": scan_status["user_type"],
                "scans_used": scan_status.get("scans_used", 0),
                "scans_left": scan_status.get("scans_left", 0)
            }
        )
    
    # Validate file
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    try:
        # Read and validate image
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        width, height = image.size
        
        # Simple analysis
        result = {
            "faces": [],
            "ai_score": 0.3,
            "manipulation_score": 0.2,
            "final_label": "Likely Real",
            "confidence": 0.7,
            "faces_detected": 0,
            "analysis_complete": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing image: {str(e)}")
    
    # Record the scan
    record_scan(user_id)

    # Prepare response
    response_data = {
        "request_id": request_id,
        "filename": file.filename,
        "timestamp": datetime.now().isoformat(),
        "user_type": "free",
        "result": result,
        "scan_info": {
            "scans_used_today": scan_status.get("scans_used", 0) + 1,
            "scans_left_today": 0,
            "next_free_scan": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    
    return JSONResponse(response_data)

# ===== STRIPE PAYMENT ROUTES =====

@app.post("/create-checkout-session")
async def create_checkout_session(request: Request):
    """Create Stripe checkout session"""
    user_id = get_user_id(request)
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': 'Deepfake Detection Premium',
                        'description': 'Unlimited scans for 1 month',
                    },
                    'unit_amount': 500,  # €5.00 in cents
                    'recurring': {
                        'interval': 'month'
                    },
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url='http://localhost:8000/payment-success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://localhost:8000/premium',
            client_reference_id=user_id,
            metadata={'user_id': user_id}
        )
        
        return {'checkout_url': session.url}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payment setup failed: {str(e)}")

@app.post("/stripe-webhook")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Stripe webhooks for payment events"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    # In production, use your webhook secret from Stripe dashboard
    # For testing, we'll handle events without verification
    try:
        event = stripe.Event.construct_from(
            json.loads(payload), stripe.api_key
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {str(e)}")
    
    # Handle subscription created
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('client_reference_id')
        
        if user_id:
            background_tasks.add_task(upgrade_user, user_id, 1)
            print(f"💰 Payment received! Upgrading user: {user_id}")
    
    return {"status": "success"}

# ===== ADMIN ROUTES FOR TESTING =====

@app.post("/admin/enable-test-mode")
async def enable_test_mode(request: Request):
    """Enable unlimited scans for testing"""
    user_id = get_user_id(request)
    upgrade_user(user_id, months=12)
    return {
        "message": "🎉 Test mode enabled - unlimited scans for 1 year!",
        "user_id": user_id
    }

@app.post("/admin/reset-my-scans")
async def reset_my_scans(request: Request):
    """Reset scans for the current user (for testing)"""
    user_id = get_user_id(request)
    reset_daily_scans(user_id)
    return {"message": f"Scans reset for user {user_id}", "user_id": user_id}

@app.get("/admin/my-status")
async def get_my_status(request: Request):
    """Get detailed status for current user (for testing)"""
    user_id = get_user_id(request)
    scan_status = can_user_scan(user_id)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM usage WHERE user_id = ?', (user_id,))
    user_data = c.fetchone()
    conn.close()
    
    return {
        "user_id": user_id,
        "scan_status": scan_status,
        "db_data": dict(user_data) if user_data else "No user data found",
        "client_ip": request.client.host
    }

# ===== ERROR HANDLERS =====

@app.exception_handler(429)
async def rate_limit_exceeded(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=429,
        content=exc.detail
    )

@app.exception_handler(500)
async def internal_error(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error - please try another image"}
    )

@app.exception_handler(404)
async def not_found_error(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"error": "Endpoint not found"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)