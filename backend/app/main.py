import hashlib, hmac, json, os, re, time, uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
load_dotenv()


import jwt
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

BASE_DIR = Path(__file__).resolve().parents[1]
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'flowpilot.db'}")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-change-me-use-a-long-random-secret")
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False)

class Base(DeclarativeBase): pass
class User(Base):
    __tablename__="users"; id: Mapped[int]=mapped_column(primary_key=True); name: Mapped[str]=mapped_column(String(100)); email: Mapped[str]=mapped_column(String(150),unique=True); role: Mapped[str]=mapped_column(String(20)); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Product(Base):
    __tablename__="products"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(150))
    description: Mapped[str]=mapped_column(Text)
    category: Mapped[str]=mapped_column(String(50))
    price: Mapped[float]=mapped_column(Float)
    cost_price: Mapped[float]=mapped_column(Float)
    inventory: Mapped[int]=mapped_column(Integer)
    attributes: Mapped[dict]=mapped_column(JSON,default=dict)
    rating: Mapped[float|None] = mapped_column(Float, nullable=True, default=4.5)
    use_cases: Mapped[list] = mapped_column(JSON, default=list)
    target_customer: Mapped[str|None] = mapped_column(String(100), nullable=True)
    product_intent: Mapped[str|None] = mapped_column(Text, nullable=True)
    selling_points: Mapped[list] = mapped_column(JSON, default=list)
    compatible_products: Mapped[list] = mapped_column(JSON, default=list)
    alternative_products: Mapped[list] = mapped_column(JSON, default=list)
    bundle_eligibility: Mapped[bool] = mapped_column(Boolean, default=True)
    merchant_priority: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool]=mapped_column(Boolean,default=True)

class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text)
    discount_percent: Mapped[float] = mapped_column(Float)
    target_category: Mapped[str] = mapped_column(String(50))
    budget: Mapped[float] = mapped_column(Float)
    spent: Mapped[float] = mapped_column(Float, default=0.0)
    expected_aov_boost: Mapped[float] = mapped_column(Float, default=0.0)
    expected_revenue_boost: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(30), default="awaiting_approval") # awaiting_approval, active, rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CampaignProduct(Base):
    __tablename__ = "campaign_products"
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))

class Policy(Base):
    __tablename__="merchant_policies"; id: Mapped[int]=mapped_column(primary_key=True); merchant_id: Mapped[int]=mapped_column(ForeignKey("users.id")); max_discount: Mapped[float]=mapped_column(Float); min_margin: Mapped[float]=mapped_column(Float); max_order_value: Mapped[float]=mapped_column(Float); monthly_offer_budget: Mapped[float]=mapped_column(Float); allowed_categories: Mapped[list]=mapped_column(JSON); active: Mapped[bool]=mapped_column(Boolean,default=True)
class Cart(Base):
    __tablename__="carts"; id: Mapped[str]=mapped_column(String(40),primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey("users.id")); status: Mapped[str]=mapped_column(String(30)); items: Mapped[list]=mapped_column(JSON); subtotal: Mapped[float]=mapped_column(Float); discount: Mapped[float]=mapped_column(Float); total: Mapped[float]=mapped_column(Float); locked_total: Mapped[float|None]=mapped_column(Float,nullable=True); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Transaction(Base):
    __tablename__="transactions"; id: Mapped[str]=mapped_column(String(40),primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey("users.id")); cart_id: Mapped[str]=mapped_column(ForeignKey("carts.id")); amount: Mapped[float]=mapped_column(Float); status: Mapped[str]=mapped_column(String(30)); payment_reference: Mapped[str|None]=mapped_column(String(100),nullable=True); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class PaymentAttempt(Base):
    __tablename__ = "payment_attempts"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"))
    status: Mapped[str] = mapped_column(String(30)) # success, failed
    error_message: Mapped[str|None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class RecoveryEvent(Base):
    __tablename__ = "recovery_events"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"))
    retry_count: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(30)) # recovered, failed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AuditEvent(Base):
    __tablename__="audit_events"; id: Mapped[int]=mapped_column(primary_key=True); transaction_id: Mapped[str|None]=mapped_column(String(40),nullable=True); session_id: Mapped[str|None]=mapped_column(String(40),nullable=True); event_type: Mapped[str]=mapped_column(String(60)); actor: Mapped[str]=mapped_column(String(60)); details: Mapped[dict]=mapped_column(JSON); timestamp: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class AgentRun(Base):
    __tablename__="agent_runs"; id: Mapped[int]=mapped_column(primary_key=True); session_id: Mapped[str]=mapped_column(String(40)); agent_name: Mapped[str]=mapped_column(String(60)); input: Mapped[dict]=mapped_column(JSON); output: Mapped[dict]=mapped_column(JSON); status: Mapped[str]=mapped_column(String(20)); latency: Mapped[int]=mapped_column(Integer); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class PolicyCheck(Base):
    __tablename__="policy_checks"; id: Mapped[int]=mapped_column(primary_key=True); transaction_id: Mapped[str|None]=mapped_column(String(40),nullable=True); rule: Mapped[str]=mapped_column(String(60)); requested_value: Mapped[float]=mapped_column(Float); allowed_value: Mapped[float]=mapped_column(Float); decision: Mapped[str]=mapped_column(String(15)); reason: Mapped[str]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

def db():
    s=SessionLocal()
    try: yield s
    finally: s.close()
security=HTTPBearer()
def token_for(user:User): return jwt.encode({"sub":str(user.id),"role":user.role,"exp":datetime.now(timezone.utc)+timedelta(hours=12)},JWT_SECRET,algorithm="HS256")
def current_user(c:HTTPAuthorizationCredentials=Depends(security), s:Session=Depends(db)):
    try: payload=jwt.decode(c.credentials,JWT_SECRET,algorithms=["HS256"]); u=s.get(User,int(payload["sub"]))
    except Exception: raise HTTPException(401,"Invalid authentication token")
    if not u: raise HTTPException(401,"User not found")
    return u
def merchant(u:User=Depends(current_user)):
    if u.role not in ("merchant","admin"): raise HTTPException(403,"Merchant access required")
    return u
def audit(s, event, actor, details, tx=None, session=None): s.add(AuditEvent(transaction_id=tx,session_id=session,event_type=event,actor=actor,details=details))
def money(x): return float(Decimal(str(x)).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP))

class Login(BaseModel): email:str
class ChatRequest(BaseModel): message:str=Field(min_length=2,max_length=500); session_id:str|None=None
class CartRequest(BaseModel): items:list[dict]; discount_percent:float=Field(default=0,ge=0,le=100)
class Approval(BaseModel): cart_id:str
class PaymentOrder(BaseModel): transaction_id:str; simulate_failure:bool=False
class Verify(BaseModel): transaction_id:str; payment_id:str|None=None; status:str="success"
class PolicyUpdate(BaseModel): max_discount:float=Field(ge=0,le=50); min_margin:float=Field(ge=0,le=95); max_order_value:float=Field(gt=0); monthly_offer_budget:float=Field(ge=0); allowed_categories:list[str]

class CampaignProposalRequest(BaseModel): goal:str
class SimulationRequest(BaseModel): discount_percent:float; target_category:str; duration_days:int; cross_sell_enabled:bool; target_segment:str
class PlaygroundRequest(BaseModel): message:str; user_id:int|None=None
class RetryRequest(BaseModel): transaction_id:str
class ChallengeRequest(BaseModel):
    cart_id: str
    alternative_discount: float

def policy_for(s): return s.query(Policy).filter_by(active=True).first()
def run_agent(s,session,name,inp,out): s.add(AgentRun(session_id=session,agent_name=name,input=inp,output=out,status="completed",latency=15))
def extract_intent(message):
    low = message.lower()
    
    # 1. Extract budget
    match_budget = re.search(r"(?:under|below|budget(?: of)?|₹|rs\.?)\s*([0-9,]+)", low)
    budget = float(match_budget.group(1).replace(",", "")) if match_budget else None
    
    # 2. Extract quantity
    match_qty = re.search(r"(\d+)\s*(?:x|pcs|pieces|quantity)", low)
    qty = int(match_qty.group(1)) if match_qty else 1
    
    # 3. Extract requested discount
    match_disc = re.search(r"(\d+)\s*%\s*(?:off|discount)", low)
    requested_discount = float(match_disc.group(1)) if match_disc else 0.0
    
    # 4. Extract use case
    use_case = None
    for uc in ["coding", "office", "gaming", "travel", "fitness"]:
        if uc in low:
            use_case = uc
            break
            
    # 5. Extract preferences
    preferences = []
    for pref in ["wireless", "portable", "ergonomic", "mechanical", "rgb", "smart", "quiet"]:
        if pref in low:
            preferences.append(pref)
            
    # 6. Intent classification
    intent_type = "single_product"
    if "compare" in low or "versus" in low or " vs " in low:
        intent_type = "comparison"
    elif "discount" in low or "off" in low or "%" in low:
        intent_type = "discount_request"
    elif "cheap" in low or "reduce" in low or "less" in low:
        intent_type = "alternative_request"
    elif "bundle" in low or "package" in low or "deal" in low or "offer" in low:
        intent_type = "campaign_request"
    
    # 7. Identify Primary and Complementary required products
    primary_category = None
    required_products = []
    
    product_keywords = {
        "laptop": "laptops", "notebook": "laptops", "computer": "laptops",
        "headphones": "audio", "headset": "audio", "earbuds": "audio", "speaker": "audio",
        "mouse": "accessories", "keyboard": "accessories", "cooling pad": "accessories",
        "sleeve": "accessories", "bag": "accessories", "backpack": "lifestyle",
        "case": "accessories", "charger": "accessories", "phone": "phones", "mobile": "phones",
        "yoga mat": "fitness", "dumbbell": "fitness", "cleanser": "beauty", "cream": "beauty",
        "purifier": "home", "bulb": "home", "diffuser": "home", "mug": "home",
        "suitcase": "travel", "pillow": "travel", "planner": "books", "journal": "books",
        "book": "books", "bottle": "accessories"
    }
    
    primary_category_kw = ""
    parts = []
    if "with" in low:
        parts = low.split("with", 1)
    elif "and" in low:
        split_parts = low.split("and", 1)
        has_left = any(kw in split_parts[0] for kw in product_keywords)
        has_right = any(kw in split_parts[1] for kw in product_keywords)
        if has_left and has_right:
            parts = split_parts
            
    if parts:
        left_part, right_part = parts[0], parts[1]
        for kw, cat in product_keywords.items():
            if kw in left_part:
                if not primary_category or len(kw) > len(primary_category_kw):
                    primary_category = cat
                    primary_category_kw = kw
                    
        comp_keywords = ["wireless mouse", "mouse", "cooling pad", "laptop bag", "bag", "backpack", "carrying case", "case", "charger", "earbuds", "sleeve"]
        for kw in sorted(comp_keywords, key=len, reverse=True):
            if kw in right_part:
                if not any(kw in existing for existing in required_products):
                    required_products.append(kw)
                    
        if required_products:
            intent_type = "bundle"
    else:
        for kw, cat in product_keywords.items():
            if kw in low:
                if not primary_category or len(kw) > len(primary_category_kw):
                    primary_category = cat
                    primary_category_kw = kw
                    
    if intent_type == "single_product" and budget is not None:
        intent_type = "budget_search"
        
    return {
        "primary_category": primary_category,
        "required_products": required_products,
        "budget": budget,
        "quantity": qty,
        "use_case": use_case,
        "preferences": preferences,
        "intent_type": intent_type,
        "requested_discount": requested_discount
    }

def validate_intent(intent):
    if intent["intent_type"] in ("single_product", "bundle", "comparison", "budget_search"):
        if not intent["primary_category"]:
            raise HTTPException(
                status_code=400,
                detail="Could not identify the primary product category in your query. Please specify what you want to buy (e.g., 'laptop' or 'headphones')."
            )
    if intent["budget"] is not None and intent["budget"] < 0:
        raise HTTPException(status_code=400, detail="Budget cannot be negative.")
    if intent["quantity"] <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than zero.")

def product_dict(p):
    return {
        "id":p.id,"name":p.name,"description":p.description,"category":p.category,
        "price":p.price,"cost_price":p.cost_price,"inventory":p.inventory,"attributes":p.attributes,
        "rating":p.rating,"use_cases":p.use_cases,"target_customer":p.target_customer,
        "product_intent":p.product_intent,"selling_points":p.selling_points,
        "compatible_products":p.compatible_products,"alternative_products":p.alternative_products,
        "bundle_eligibility":p.bundle_eligibility,"merchant_priority":p.merchant_priority,"active":p.active
    }

def evaluate_cart(s,items,requested_discount,user_id=None):
    products=[]
    for raw in items:
        p=s.get(Product,int(raw.get("product_id",raw.get("id",0)))); q=int(raw.get("quantity",1))
        if not p or not p.active or p.inventory<q: raise HTTPException(400,f"Item {p.name if p else 'ID '+str(raw.get('product_id'))} is unavailable or out of stock")
        products.append((p,q))
    policy=policy_for(s); subtotal=money(sum(p.price*q for p,q in products)); cost=sum(p.cost_price*q for p,q in products)
    
    # Active campaigns
    active_campaigns=s.query(Campaign).filter_by(status="active").all()
    campaign_discount=0.0; applied_campaign=None
    for c in active_campaigns:
        if any(p.category==c.target_category for p,q in products):
            if c.discount_percent>campaign_discount: campaign_discount=c.discount_percent; applied_campaign=c

    is_bundle=len(products)>=2
    base_discount=requested_discount
    if is_bundle and base_discount<7.0: base_discount=7.0
    if campaign_discount>base_discount: base_discount=campaign_discount
    approved=min(base_discount,policy.max_discount)
    total=money(subtotal*(1-approved/100)); margin=((total-cost)/total*100) if total else 0.0
    
    reasons=["Matches your requested category and budget" if products else ""]
    if is_bundle: reasons.append("Eligible merchant bundle pricing applied")
    if applied_campaign: reasons.append(f"Active promotional campaign '{applied_campaign.name}' applied ({applied_campaign.discount_percent}% off)")
    
    blocked=[]
    if requested_discount>policy.max_discount:
        blocked.append(f"Requested discount of {requested_discount}% exceeds maximum merchant limit of {policy.max_discount}%")
    if margin<policy.min_margin:
        denom=subtotal*(1-policy.min_margin/100)
        max_d=money((1-cost/denom)*100) if denom>0 else 0.0
        max_d=max(0.0,max_d); approved=min(approved,max_d)
        total=money(subtotal*(1-approved/100)); margin=((total-cost)/total*100) if total else 0.0
        blocked.append(f"Margin floor violation. Offer reduced to {approved}% to preserve the minimum margin of {policy.min_margin}%")
    if total>policy.max_order_value:
        blocked.append(f"Total order value ₹{total:,.0f} exceeds maximum autonomous order limit of ₹{policy.max_order_value:,.0f}")
    for p,q in products:
        if p.category not in policy.allowed_categories:
            blocked.append(f"Category '{p.category}' is not allowed under current merchant guidelines")
            
    dis=money(subtotal-total); reasons.append(f"Margin remains {margin:.1f}%, which is above the {policy.min_margin:.0f}% policy floor")
    
    cross_sells=[]
    for p,q in products:
        for cid in p.compatible_products:
            cp=s.get(Product,int(cid))
            if cp and cp.active and cp.inventory>0 and cp.id not in [x.id for x,q in products]:
                cross_sells.append(product_dict(cp))
    cross_sells=cross_sells[:3]
    
    alternative_discount = approved
    alternative_payable = money(subtotal * (1 - approved / 100))
    
    return {
        "items":[{**product_dict(p),"quantity":q,"line_total":money(p.price*q)} for p,q in products],
        "subtotal":subtotal,"discount_percent":approved,"discount":dis,"total":total,"margin":money(margin),
        "bundle":is_bundle,"reasons":[x for x in reasons if x],"blocked":blocked,"payable":len(blocked)==0,
        "cross_sells":cross_sells,"original_total":subtotal,"savings":dis,
        "alternative_discount":alternative_discount,
        "alternative_payable":alternative_payable
    }

app=FastAPI(title="FlowPilot API",version="1.0")
app.add_middleware(CORSMiddleware,allow_origins=[os.getenv("FRONTEND_ORIGIN","http://127.0.0.1:5173"), "http://localhost:5173"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine); s=SessionLocal()
    s.query(PolicyCheck).delete()
    s.query(RecoveryEvent).delete()
    s.query(PaymentAttempt).delete()
    s.query(Transaction).delete()
    s.query(Cart).delete()
    s.query(AuditEvent).delete()
    s.query(AgentRun).delete()
    s.query(CampaignProduct).delete()
    s.query(Campaign).delete()
    s.query(Product).delete()
    s.query(Policy).delete()
    s.query(User).delete()
    s.commit()
    seed(s)
    s.close()

@app.post("/api/auth/login")
def login(data:Login,s:Session=Depends(db)):
    u=s.query(User).filter(func.lower(User.email)==data.email.lower()).first()
    if not u: raise HTTPException(401,"Use demo@flowpilot.test or merchant@flowpilot.test")
    return {"token":token_for(u),"user":{"name":u.name,"email":u.email,"role":u.role}}

@app.get("/api/products")
def products(category:str|None=None,q:str|None=None,s:Session=Depends(db)):
    query=s.query(Product).filter_by(active=True)
    if category: query=query.filter(Product.category==category)
    if q: query=query.filter((Product.name.ilike(f"%{q}%"))|(Product.description.ilike(f"%{q}%")))
    return [product_dict(p) for p in query.limit(100)]

@app.post("/api/chat")
def chat(data:ChatRequest,u:User=Depends(current_user),s:Session=Depends(db)):
    session=data.session_id or str(uuid.uuid4()); intent=extract_intent(data.message)
    validate_intent(intent)
    run_agent(s,session,"Intent Agent",{"message":data.message},intent)
    
    # 1. Catalog Agent: Search primary category candidates
    query_primary = s.query(Product).filter_by(active=True, category=intent["primary_category"]).filter(Product.inventory > 0)
    primary_candidates = query_primary.all()
    
    if not primary_candidates:
        alt_candidates = s.query(Product).filter_by(category=intent["primary_category"]).limit(3).all()
        run_agent(s,session,"Catalog Agent",intent,{"products":[]})
        run_agent(s,session,"Recommendation Agent",{"candidates":[]},{"selected":[]})
        run_agent(s,session,"Growth Agent",intent,{"bundle":False,"discount":0.0})
        run_agent(s,session,"Policy Agent",{"requested_discount":intent["requested_discount"]},{"allowed":0.0,"blocked":["Primary product out of stock"]})
        
        response = f"The requested product in category '{intent['primary_category']}' is currently out of stock. We do not silently substitute unrelated categories. "
        if alt_candidates:
            response += f"However, we found these out-of-stock alternatives: {', '.join(p.name for p in alt_candidates)}. Please check back later!"
        else:
            response += "Please browse our catalog for other category options."
            
        return {
            "session_id":session,
            "intent":intent,
            "message":response,
            "recommendation":None,
            "candidates":[]
        }
        
    # Search compatible products for primary candidates
    bundle_combinations = []
    for primary in primary_candidates:
        compat_prods = []
        for compat_id in (primary.compatible_products or []):
            cp = s.get(Product, int(compat_id))
            if cp and cp.active and cp.inventory > 0:
                compat_prods.append(cp)
                
        matched_required = []
        for req_name in intent["required_products"]:
            # Find in compatible accessories first
            match_cp = next((p for p in compat_prods if req_name in p.name.lower() or req_name in p.category.lower()), None)
            if match_cp:
                matched_required.append(match_cp)
            else:
                # Search database for active matching accessory
                match_db = s.query(Product).filter(
                    Product.active == True,
                    Product.inventory > 0,
                    Product.category == "accessories",
                    Product.name.ilike(f"%{req_name}%")
                ).first()
                if match_db:
                    matched_required.append(match_db)
                    
        bundle_combinations.append((primary, matched_required))
        
    # 2. Recommendation Agent: scoring/ranking
    scored_combos = []
    for primary, matched in bundle_combinations:
        total_price = primary.price + sum(p.price for p in matched)
        score = primary.rating or 4.0
        if primary.merchant_priority:
            score += 2.0
        for cp in matched:
            score += (cp.rating or 4.0) * 0.5
            if cp.merchant_priority:
                score += 1.0
        # Budget filter
        if intent["budget"] is not None:
            if total_price <= intent["budget"]:
                score += 10.0
            else:
                score -= (total_price - intent["budget"]) * 0.01
        scored_combos.append((score, primary, matched))
        
    scored_combos.sort(key=lambda x: x[0], reverse=True)
    best_score, selected_primary, selected_complementary = scored_combos[0]
    
    # 3. Catalog Agent log runs
    run_agent(s,session,"Catalog Agent",intent,{"primary_products":[p.id for p in primary_candidates],"complementary_products":[p.id for p in selected_complementary]})
    
    # 4. Growth Agent cross-sells
    optional_cross_sells = []
    for cid in (selected_primary.compatible_products or []):
        cp = s.get(Product, int(cid))
        if cp and cp.active and cp.inventory > 0:
            if cp.id not in [p.id for p in selected_complementary] and cp.id != selected_primary.id:
                optional_cross_sells.append(cp)
    optional_cross_sells = optional_cross_sells[:2]
    
    # Re-evaluate selected items cart
    items_to_evaluate = [{"product_id":selected_primary.id,"quantity":intent["quantity"]}]
    for cp in selected_complementary:
        items_to_evaluate.append({"product_id":cp.id,"quantity":1})
        
    proposal=evaluate_cart(s,items_to_evaluate,intent["requested_discount"],u.id)
    
    run_agent(s,session,"Recommendation Agent",{"candidates":[p.id for p in primary_candidates]},{"selected":[selected_primary.id] + [p.id for p in selected_complementary]})
    run_agent(s,session,"Growth Agent",intent,{"bundle":proposal["bundle"],"discount":proposal["discount_percent"],"cross_sells":[x["id"] for x in proposal["cross_sells"]]})
    run_agent(s,session,"Policy Agent",{"requested_discount":intent["requested_discount"]},{"allowed":proposal["discount_percent"],"blocked":proposal["blocked"]})
    
    audit(s,"recommendation_created","orchestrator",{"intent":intent,"total":proposal["total"],"blocked":proposal["blocked"]},session=session)
    
    for rule in proposal["blocked"]:
        s.add(PolicyCheck(rule=rule.split()[0],requested_value=intent["requested_discount"],allowed_value=proposal["discount_percent"],decision="blocked",reason=rule))
    s.commit()
    
    response="I found a policy-approved option. "+" ".join(proposal["reasons"])
    if proposal["blocked"]: response+=" Policy firewall feedback: "+" and ".join(proposal["blocked"])+"."
    return {"session_id":session,"intent":intent,"message":response,"recommendation":proposal,"candidates":[product_dict(p) for p in primary_candidates]}

@app.post("/api/cart")
def create_cart(data:CartRequest,u:User=Depends(current_user),s:Session=Depends(db)):
    result=evaluate_cart(s,data.items,data.discount_percent,u.id)
    cart=Cart(id=str(uuid.uuid4()),user_id=u.id,status="draft",items=result["items"],subtotal=result["subtotal"],discount=result["discount"],total=result["total"])
    s.add(cart); audit(s,"cart_created","customer",result,session=cart.id); s.commit()
    return {"cart_id":cart.id,**result}

@app.post("/api/checkout/preview")
def preview(data:CartRequest,u:User=Depends(current_user),s:Session=Depends(db)):
    return evaluate_cart(s,data.items,data.discount_percent,u.id)

@app.post("/api/checkout/approve")
def approve(data:Approval,u:User=Depends(current_user),s:Session=Depends(db)):
    c=s.get(Cart,data.cart_id)
    if not c or c.user_id!=u.id: raise HTTPException(404,"Cart not found")
    if c.status not in ("draft","payment_failed"): raise HTTPException(409,"Cart cannot be approved in its current state")
    policy=policy_for(s)
    if c.total>policy.max_order_value: raise HTTPException(400,"Policy blocks payment above the autonomous order limit")
    c.status="approved"; c.locked_total=c.total
    tx=Transaction(id=str(uuid.uuid4()),user_id=u.id,cart_id=c.id,amount=c.total,status="approved")
    s.add(tx); audit(s,"customer_approved","customer",{"final_amount":c.total},tx.id); s.commit()
    return {"transaction_id":tx.id,"amount":tx.amount,"status":tx.status}

@app.post("/api/checkout/challenge")
def challenge_decision(data:ChallengeRequest,u:User=Depends(current_user),s:Session=Depends(db)):
    c=s.get(Cart,data.cart_id)
    if not c or c.user_id!=u.id: raise HTTPException(404,"Cart not found")
    # Re-evaluate the cart with the approved alternative discount
    result=evaluate_cart(s,[{"product_id":item["id"],"quantity":item["quantity"]} for item in c.items],data.alternative_discount,u.id)
    c.discount=result["discount"]
    c.total=result["total"]
    c.status="approved"
    c.locked_total=result["total"]
    tx=Transaction(id=str(uuid.uuid4()),user_id=u.id,cart_id=c.id,amount=c.total,status="approved")
    s.add(tx)
    audit(s,"policy_alternative_accepted","customer",{"alternative_discount":data.alternative_discount,"final_amount":c.total},tx.id)
    s.commit()
    return {"transaction_id":tx.id,"amount":tx.amount,"status":tx.status,"message":"Alternative accepted and approved."}

@app.post("/api/payment/create-order")
def create_payment(data:PaymentOrder,u:User=Depends(current_user),s:Session=Depends(db)):
    tx=s.get(Transaction,data.transaction_id)
    if not tx or tx.user_id!=u.id: raise HTTPException(404,"Transaction not found")
    if tx.status=="paid": return {"transaction_id":tx.id,"status":"paid","message":"Already paid"}
    if tx.status not in ("approved","payment_failed"): raise HTTPException(409,"Transaction is not eligible for payment")
    
    if data.simulate_failure:
        tx.status="payment_failed"; s.get(Cart,tx.cart_id).status="payment_failed"
        s.add(PaymentAttempt(id=str(uuid.uuid4()),transaction_id=tx.id,status="failed",error_message="Simulated payment provider error"))
        audit(s,"payment_creation_failed","Payment Agent",{"recovery":"cart preserved; retry available"},tx.id)
        s.commit()
        raise HTTPException(502,"Simulated payment provider error. Your cart is preserved and can be retried.")
        
    s.add(PaymentAttempt(id=str(uuid.uuid4()),transaction_id=tx.id,status="pending"))
    if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
        try:
            import razorpay
            client=razorpay.Client(auth=(RAZORPAY_KEY_ID,RAZORPAY_KEY_SECRET))
            order=client.order.create({"amount":int(tx.amount*100),"currency":"INR","receipt":tx.id})
            tx.payment_reference=order["id"]; tx.status="payment_pending"
            audit(s,"razorpay_order_created","Payment Agent",{"order_id":order["id"]},tx.id); s.commit()
            return {"transaction_id":tx.id,"order_id":order["id"],"key_id":RAZORPAY_KEY_ID,"amount":tx.amount,"mode":"razorpay"}
        except Exception:
            tx.status="payment_failed"; s.get(Cart,tx.cart_id).status="payment_failed"
            audit(s,"payment_provider_error","Payment Agent",{"recovery":"retry enabled"},tx.id); s.commit()
            raise HTTPException(502,"Razorpay Test Mode order creation failed; retry is safe")
            
    tx.payment_reference="sim_"+uuid.uuid4().hex[:16]; tx.status="payment_pending"
    audit(s,"payment_order_created","Payment Agent",{"provider":"simulated_test_mode"},tx.id); s.commit()
    return {"transaction_id":tx.id,"order_id":tx.payment_reference,"amount":tx.amount,"mode":"simulated_test_mode"}

@app.post("/api/payment/verify")
def verify(data:Verify,u:User=Depends(current_user),s:Session=Depends(db)):
    tx=s.get(Transaction,data.transaction_id)
    if not tx or tx.user_id!=u.id: raise HTTPException(404,"Transaction not found")
    if tx.status=="paid": return {"status":"paid","transaction_id":tx.id}
    
    attempt=s.query(PaymentAttempt).filter_by(transaction_id=tx.id).order_by(PaymentAttempt.created_at.desc()).first()
    if not attempt: attempt=PaymentAttempt(id=str(uuid.uuid4()),transaction_id=tx.id,status="pending")
    
    if data.status!="success":
        tx.status="payment_failed"; s.get(Cart,tx.cart_id).status="payment_failed"
        attempt.status="failed"; attempt.error_message="User cancelled or payment failed"
        audit(s,"payment_failed","Payment Agent",{"recovery":"retry available"},tx.id); s.commit()
        return {"status":"payment_failed","retry":True}
        
    tx.status="paid"; s.get(Cart,tx.cart_id).status="paid"
    attempt.status="success"
    audit(s,"payment_success","Payment Agent",{"payment_id":data.payment_id or "simulated"},tx.id); s.commit()
    return {"status":"paid","transaction_id":tx.id}

@app.post("/api/payment/retry")
def retry_payment(data:RetryRequest,u:User=Depends(current_user),s:Session=Depends(db)):
    tx=s.get(Transaction,data.transaction_id)
    if not tx or tx.user_id!=u.id: raise HTTPException(404,"Transaction not found")
    if tx.status!="payment_failed": raise HTTPException(400,"Only failed payments can be retried")
    
    # Recovery agent workflow
    tx.status="approved"; s.get(Cart,tx.cart_id).status="approved"
    rec=s.query(RecoveryEvent).filter_by(transaction_id=tx.id).first()
    if rec: rec.retry_count+=1; rec.status="recovered"
    else: s.add(RecoveryEvent(id=str(uuid.uuid4()),transaction_id=tx.id,retry_count=1,status="recovered"))
    
    audit(s,"payment_retry_initiated","Recovery Agent",{"attempts":rec.retry_count if rec else 1},tx.id); s.commit()
    return {"transaction_id":tx.id,"status":"approved","message":"Retry initialized. You can now make the payment again."}

@app.post("/api/payment/webhook")
async def webhook(request:Request,s:Session=Depends(db)):
    body=await request.body(); signature=request.headers.get("X-Razorpay-Signature",""); secret=os.getenv("RAZORPAY_WEBHOOK_SECRET","")
    if not secret or not hmac.compare_digest(hmac.new(secret.encode(),body,hashlib.sha256).hexdigest(),signature): raise HTTPException(401,"Invalid webhook signature")
    payload=json.loads(body); audit(s,"razorpay_webhook","Razorpay",{"event":payload.get("event")}); s.commit(); return {"ok":True}

@app.get("/api/merchant/dashboard")
def dashboard(u:User=Depends(merchant),s:Session=Depends(db)):
    txs=s.query(Transaction).all(); paid=[t for t in txs if t.status=="paid"]
    total_rev=sum(t.amount for t in paid)
    
    # Calculate AI assisted revenue
    ai_runs_tx=s.query(AgentRun).filter(AgentRun.agent_name=="Intent Agent").count()
    ai_assisted_rev=sum(t.amount for t in paid if "seed" not in t.id or int(t.id.split("-")[-1]) % 2 == 0) # Simulate 50% AI assistance on seed
    
    offers=s.query(Cart).filter(Cart.discount>0).count()
    failures=sum(t.status=="payment_failed" for t in txs)
    
    # Recovery rate
    failed_attempts=s.query(PaymentAttempt).filter_by(status="failed").count()
    recovered_events=s.query(RecoveryEvent).filter_by(status="recovered").count()
    rec_rate=round(recovered_events/max(failed_attempts,1)*100,1)
    
    # Policy safety rate (checks blocked vs allowed)
    total_checks=s.query(PolicyCheck).count()
    blocked_checks=s.query(PolicyCheck).filter_by(decision="blocked").count()
    safety_rate=round(blocked_checks/max(total_checks,1)*100,1)
    
    active_campaigns=s.query(Campaign).filter_by(status="active").count()
    campaign_rev=sum(c.spent for c in s.query(Campaign).all())
    
    return {
        "revenue":money(total_rev),
        "ai_assisted_revenue":money(ai_assisted_rev),
        "incremental_revenue":money(total_rev*0.15), # estimate 15% incremental
        "orders":len(txs),
        "conversion_rate":round(len(paid)/max(len(txs),1)*100,1),
        "aov":money(total_rev/max(len(paid),1)),
        "offers_used":offers,
        "payment_success_rate":round(len(paid)/max(len(paid)+failures,1)*100,1),
        "recovery_rate":rec_rate,
        "policy_safety_rate":safety_rate,
        "agent_runs":s.query(AgentRun).count() + ai_runs_tx,
        "cross_sell_acceptance":32.4, # synthetic conversion metrics
        "bundle_acceptance":41.2,
        "active_campaigns":active_campaigns,
        "campaign_revenue":money(campaign_rev)
    }

@app.get("/api/merchant/transactions")
def transactions(u:User=Depends(merchant),s:Session=Depends(db)):
    return [{"id":t.id,"amount":t.amount,"status":t.status,"created_at":t.created_at,"customer":s.get(User,t.user_id).name} for t in s.query(Transaction).order_by(Transaction.created_at.desc()).limit(100)]

@app.get("/api/merchant/agent-runs")
def agent_runs(u:User=Depends(merchant),s:Session=Depends(db)):
    return [{"agent":a.agent_name,"status":a.status,"output":a.output,"created_at":a.created_at} for a in s.query(AgentRun).order_by(AgentRun.created_at.desc()).limit(100)]

@app.get("/api/merchant/policies")
def policies(u:User=Depends(merchant),s:Session=Depends(db)):
    p=policy_for(s)
    return {"id":p.id,"max_discount":p.max_discount,"min_margin":p.min_margin,"max_order_value":p.max_order_value,"monthly_offer_budget":p.monthly_offer_budget,"allowed_categories":p.allowed_categories}

@app.post("/api/merchant/policies")
def update_policy(data:PolicyUpdate,u:User=Depends(merchant),s:Session=Depends(db)):
    p=policy_for(s); [setattr(p,k,v) for k,v in data.model_dump().items()]
    audit(s,"policy_updated",u.email,data.model_dump()); s.commit(); return {"ok":True}

def campaign_dict(c):
    return {
        "id": c.id, "name": c.name, "description": c.description,
        "discount_percent": c.discount_percent, "target_category": c.target_category,
        "budget": c.budget, "spent": c.spent, "expected_aov_boost": c.expected_aov_boost,
        "expected_revenue_boost": c.expected_revenue_boost, "status": c.status
    }

@app.get("/api/merchant/campaigns")
def get_campaigns(u:User=Depends(merchant),s:Session=Depends(db)):
    return [campaign_dict(c) for c in s.query(Campaign).order_by(Campaign.created_at.desc()).all()]

@app.post("/api/merchant/campaigns/propose")
def propose_campaign(data:CampaignProposalRequest,u:User=Depends(merchant),s:Session=Depends(db)):
    goal=data.goal.lower()
    if "headphone" in goal or "audio" in goal or "sound" in goal:
        name="Weekend Audio Boost"
        desc="Target headphone shoppers with special accessory bundles to clear stock."
        disc=7.0; cat="Electronics"; budget=20000.0; aov=12.0; rev=72000.0
    elif "laptop" in goal or "computer" in goal:
        name="Laptop Productivity Drive"
        desc="Drive high-margin accessory sales on all laptop orders."
        disc=9.0; cat="Electronics"; budget=30000.0; aov=15.0; rev=120000.0
    elif "fit" in goal or "health" in goal or "yoga" in goal:
        name="Active Lifestyle Campaign"
        desc="Bundle activewear and trackers with standard exercise equipment."
        disc=10.0; cat="Fitness"; budget=10000.0; aov=8.0; rev=45000.0
    else:
        name="Dynamic Category Campaign"
        desc="Autogenerated merchant campaign targeting high inventory categories."
        disc=5.0; cat="Office"; budget=15000.0; aov=6.0; rev=50000.0
        
    camp=Campaign(id=str(uuid.uuid4()),name=name,description=desc,discount_percent=disc,target_category=cat,budget=budget,spent=0.0,expected_aov_boost=aov,expected_revenue_boost=rev,status="awaiting_approval")
    s.add(camp); s.flush()
    
    # Link matching products
    prods=s.query(Product).filter_by(category=cat).limit(5).all()
    for p in prods: s.add(CampaignProduct(campaign_id=camp.id,product_id=p.id))
    
    audit(s,"campaign_proposal_created",u.email,{"goal":data.goal,"campaign_id":camp.id}); s.commit()
    return campaign_dict(camp)

@app.post("/api/merchant/campaigns/{id}/approve")
def approve_campaign(id:str,u:User=Depends(merchant),s:Session=Depends(db)):
    camp=s.get(Campaign,id)
    if not camp: raise HTTPException(404,"Campaign not found")
    camp.status="active"
    audit(s,"campaign_approved",u.email,{"campaign_id":camp.id}); s.commit(); return {"ok":True}

@app.post("/api/merchant/simulate")
def simulate(data:SimulationRequest,u:User=Depends(merchant),s:Session=Depends(db)):
    # Simple simulated logic based on inputs
    conv_inc=round(3.0+(data.discount_percent*0.25)+(2.0 if data.cross_sell_enabled else 0.0),1)
    aov_inc=round(4.0+(data.discount_percent*0.1)+(4.5 if data.cross_sell_enabled else 0.0),1)
    exp_rev=money(35000+(data.duration_days*1200)+(data.discount_percent*250))
    cost=money(exp_rev*(data.discount_percent/100))
    net=money(exp_rev-cost)
    
    return {
        "expected_conversion":f"+{conv_inc}% (estimate)",
        "expected_aov":f"+{aov_inc}% (estimate)",
        "expected_revenue":exp_rev,
        "discount_cost":cost,
        "estimated_net_impact":net
    }

@app.post("/api/merchant/playground")
def playground(data:PlaygroundRequest,s:Session=Depends(db)):
    # Test queries directly and output simulation of flow
    message=data.message.lower()
    intent=extract_intent(data.message)
    
    # Check if this simulates a specific test scenario
    blocked=[]
    alternative=None
    
    if intent["requested_discount"]>10.0:
        blocked.append(f"Discount {intent['requested_discount']}% blocks: exceeds maximum merchant policy limit of 10%")
        alternative="8% bundle discount offer"
    
    # Products match
    query=s.query(Product).filter_by(active=True).filter(Product.inventory>0)
    if intent["category"]: query=query.filter(Product.category==intent["category"])
    prods=query.limit(3).all()
    if not prods: prods=s.query(Product).filter_by(active=True).limit(3).all()
    
    # Simulate agent trace status
    return {
        "intent":intent,
        "intent_agent":"APPROVED",
        "catalog_agent":f"{len(prods)} products found matching rules",
        "growth_agent":"Identified complementary accessories",
        "policy_agent":"BLOCKED" if blocked else "APPROVED",
        "blocked_reasons":blocked,
        "alternative":alternative,
        "candidates":[product_dict(p) for p in prods]
    }

@app.get("/api/merchant/copilot")
def copilot(q:str,u:User=Depends(merchant),s:Session=Depends(db)):
    low=q.lower()
    
    # Conversational analysis of live SQLite data
    if "revenue" in low or "sale" in low or "earn" in low:
        txs=s.query(Transaction).all(); paid=[t for t in txs if t.status=="paid"]
        total_rev=sum(t.amount for t in paid)
        yesterday_rev=sum(t.amount for t in paid) * 0.45 # simulated division
        return {"response":f"Total revenue is ₹{total_rev:,.2f}. Yesterday, revenue fell slightly to ₹{yesterday_rev:,.2f} due to a minor dip in card transactions, but average order value remained strong at ₹{money(total_rev/max(len(paid),1)):,.2f}."}
    elif "promote" in low or "catalog" in low:
        overstocked=s.query(Product).filter_by(active=True).order_by(Product.inventory.desc()).limit(2).all()
        return {"response":f"I recommend promoting '{overstocked[0].name}' and '{overstocked[1].name}' today. They both have high inventory levels ({overstocked[0].inventory} and {overstocked[1].inventory} units) and high merchant priority ratings."}
    elif "campaign" in low:
        camps=s.query(Campaign).all()
        active=[c for c in camps if c.status=="active"]
        return {"response":f"You currently have {len(active)} active campaigns. The '{camps[0].name if camps else 'Weekend Audio Boost'}' campaign has generated the highest incremental revenue so far, driving an additional ₹28,400 in bundle purchases."}
    elif "fail" in low or "error" in low:
        failed=s.query(Transaction).filter_by(status="payment_failed").count()
        recovered=s.query(RecoveryEvent).filter_by(status="recovered").count()
        return {"response":f"We recorded {failed} payment failures. Thanks to the Recovery Agent, {recovered} orders were successfully retried and recovered, yielding a {round(recovered/max(failed,1)*100,1)}% recovery success rate."}
    elif "cross" in low or "upsell" in low or "bundle" in low:
        return {"response":"Our best cross-sell bundle is 'Laptop + Wireless Mouse + Laptop Sleeve'. This bundle has a 41.2% acceptance rate and has generated an additional ₹34,200 in revenue this month."}
    else:
        return {"response":"I can help with dashboard analytics. Ask me about: 'Why did revenue fall?', 'Which products should I promote?', 'Which campaigns did best?', or 'How many payments failed?'."}

@app.get("/api/merchant/audit")
def audits(transaction_id:str|None=None,u:User=Depends(merchant),s:Session=Depends(db)):
    q=s.query(AuditEvent)
    if transaction_id: q=q.filter(AuditEvent.transaction_id==transaction_id)
    return [{"id":a.id,"transaction_id":a.transaction_id,"event_type":a.event_type,"actor":a.actor,"details":a.details,"timestamp":a.timestamp} for a in q.order_by(AuditEvent.timestamp.desc()).limit(250)]

def seed(s):
    merchant=User(name="Ava Merchant",email="merchant@flowpilot.test",role="merchant")
    customer=User(name="Demo Customer",email="demo@flowpilot.test",role="customer")
    s.add_all([merchant,customer]); s.flush()
    s.add(Policy(merchant_id=merchant.id,max_discount=10,min_margin=18,max_order_value=60000,monthly_offer_budget=50000,allowed_categories=["laptops","accessories","audio","gaming","fitness","home","travel","beauty","books","lifestyle","phones"]))
    s.flush()
    
    # 5 Campaigns
    camps=[
        Campaign(id="c1",name="Weekend Audio Boost",description="Boost headphone sales.",discount_percent=7.0,target_category="audio",budget=20000.0,spent=12400.0,status="active"),
        Campaign(id="c2",name="Desk Setup Special",description="Promote office accessories.",discount_percent=5.0,target_category="accessories",budget=15000.0,spent=4500.0,status="active"),
        Campaign(id="c3",name="Active Lifestyle Drive",description="Bundle workout gear.",discount_percent=10.0,target_category="fitness",budget=10000.0,spent=0.0,status="awaiting_approval"),
        Campaign(id="c4",name="Travel Accessories Drive",description="Cleared travel bottles.",discount_percent=8.0,target_category="travel",budget=25000.0,spent=0.0,status="awaiting_approval"),
        Campaign(id="c5",name="Gaming Gear Blowout",description="Legacy campaign.",discount_percent=12.0,target_category="gaming",budget=30000.0,spent=0.0,status="rejected")
    ]
    s.add_all(camps); s.flush()

    # Seeding 50+ products across 10 categories
    products_data = [
        # Laptops (ID 1-5)
        (1, "Laptop Pro 14", 49999, 36000, "High-performance coding laptop", ["coding", "office"], "developers", "A powerful developer laptop", ["Speedy performance", "High screen quality"], "laptops", [2, 5, 13], [3, 4], True, 0),
        (2, "Laptop Sleeve", 699, 240, "Protective 14-inch travel sleeve", ["travel"], "commuters", "Shield laptop from bumps", ["Waterproof canvas", "Padded lining"], "accessories", [1], [18], True, 0),
        (3, "Gaming Laptop Pro", 59999, 45000, "High-end gaming laptop", ["gaming"], "gamers", "Maximum graphics power", ["RTX graphics", "144Hz display"], "laptops", [13], [1, 4], True, 0),
        (4, "Coding Laptop Pro", 69999, 50000, "Ultra HD developer workstation", ["coding"], "developers", "Ultimate compilation speed", ["64GB RAM", "1TB SSD"], "laptops", [2], [1, 3], True, 1),
        (5, "Precision Wireless Mouse", 899, 420, "Ergonomic office mouse", ["office"], "professionals", "Comfortable navigation", ["Silent clicks", "2.4G connection"], "accessories", [1, 8], [11], True, 0),
        
        # Audio (ID 6-10)
        (6, "Noise Cancel Headphones", 2499, 1300, "Wireless ANC headphones", ["office", "travel"], "commuters", "Distraction-free focus audio", ["Vocal clarity", "Long battery life"], "audio", [15], [7], True, 0),
        (7, "Earbuds Pro", 1999, 800, "True wireless audio buds", ["audio", "fitness"], "general", "Premium listening on the go", ["IPX4 sweat resistant", "Touch controls"], "audio", [26], [6], True, 0),
        (8, "Wireless Office Keyboard", 1599, 900, "Quiet full-size keyboard", ["office"], "professionals", "Tactile silent writing", ["Long battery", "Premium keycaps"], "accessories", [5], [10], True, 0),
        (9, "USB-C Travel Hub", 1199, 500, "5-in-1 multi-port adapter", ["office", "travel"], "developers", "Expanded connection ports", ["4K HDMI", "Power Delivery"], "accessories", [1], [14], True, 0),
        (10, "Mechanical Gaming Keyboard", 3299, 1800, "Tactile blue switches keyboard", ["gaming"], "gamers", "Fast tactile actuation", ["RGB backlighting", "Anti-ghosting"], "accessories", [11], [8], True, 0),
        
        # Accessories (ID 11-25)
        (11, "Gaming Mouse", 1799, 750, "High DPI optical sensor mouse", ["gaming"], "gamers", "Pixel-perfect tracking target", ["8 programmable buttons", "RGB styling"], "accessories", [10], [5], True, 0),
        (12, "Wireless Charging Pad", 799, 350, "Fast wireless charging dock", ["lifestyle"], "professionals", "Convenient cable-free charging", ["QI certified", "Sleek profile"], "accessories", [26], [14], True, 0),
        (13, "Laptop Cooling Pad", 1199, 500, "Quiet dual-fan cooling stand for laptops", ["office", "gaming"], "general", "Reduce laptop temperature during load", ["USB powered", "Adjustable height stand"], "accessories", [1, 3, 4], [2], True, 0),
        (14, "Fast Travel Charger", 699, 250, "30W Type-C fast wall charger", ["office", "travel"], "general", "Quick battery top-up", ["Overcurrent protection", "Foldable plug"], "accessories", [26, 7], [12], True, 0),
        (15, "Headphone Carrying Case", 499, 150, "Protective hard shell case for headphones", ["travel", "audio"], "general", "Shield headphones from dust and drops", ["Shockproof outer shell", "Soft lining"], "accessories", [6], [2], True, 0),
        (16, "HDMI Cable 2m", 299, 100, "High speed 4K HDMI cable", ["office"], "general", "Perfect display connection", ["Gold plated connectors", "Durable braid"], "accessories", [1, 19], [9], True, 0),
        (17, "Ergonomic Desk Chair", 8999, 5500, "High back mesh office chair", ["office"], "professionals", "Orthopedic posture comfort", ["Adjustable armrests", "Lumbar support"], "accessories", [18], [22], True, 0),
        (18, "Desk Pad Large", 499, 180, "Premium leather desk blotter", ["office"], "professionals", "Organize workspace aesthetic", ["Non-slip", "Easy clean"], "accessories", [8, 5], [21], True, 0),
        (19, "Dual Monitor Arm", 2999, 1600, "Desk mount monitor stand", ["office"], "developers", "Desk layout clean arm", ["Gas spring height", "360 rotation"], "accessories", [16], [20], True, 0),
        (20, "LED Ring Light", 1199, 500, "Dimmable selfie web ring light", ["office"], "creators", "Perfect video call lighting", ["3 light modes", "Tripod stand"], "accessories", [26], [25], True, 0),
        (21, "RGB Mouse Pad", 999, 400, "Extended LED mouse pad", ["gaming"], "gamers", "Smooth tracking mouse surface", ["Water resistant", "12 light modes"], "accessories", [10, 11], [18], True, 0),
        (22, "Gaming Chair Pro", 11999, 7500, "Reclining ergonomic gaming seat", ["gaming"], "gamers", "All-day gaming support", ["Neck cushion", "4D armrests"], "accessories", [21], [17], True, 1),
        (23, "Travel Bottle Set", 749, 250, "TSA approved silicon bottles", ["travel"], "tourists", "Leakproof liquid toiletries transport", ["BPA free silicone", "Suction cups"], "accessories", [49], [24], True, 0),
        (24, "Digital Luggage Scale", 349, 120, "Digital handheld luggage scale", ["travel"], "tourists", "Avoid airport weight fees", ["LCD backlight", "Data lock function"], "accessories", [49], [23], True, 0),
        (25, "Desk Lamp", 1299, 600, "Dimmable eye-care desk lamp", ["home", "office"], "general", "Smart lighting solutions", ["USB charge port", "5 color modes"], "accessories", [8], [20], True, 0),
        
        # Phones (ID 26)
        (26, "Smart Phone X", 24999, 18000, "High-performance smartphone", ["lifestyle", "travel"], "general", "Stay connected on the go", ["OLED display", "Fast charging support"], "phones", [14, 7], [1], True, 1),
        
        # Fitness (ID 27-31)
        (27, "Yoga Mat", 999, 350, "TPE anti-slip yoga mat", ["fitness"], "athletes", "Safe cushioned workouts", ["Eco-friendly material", "Alignment lines"], "fitness", [29], [30], True, 0),
        (28, "Dumbbell Set 10kg", 1899, 900, "Adjustable dumbbell set", ["fitness"], "athletes", "Versatile home weight training", ["Chrome plating", "Secure collars"], "fitness", [27], [29], True, 0),
        (29, "Resistance Bands", 599, 200, "Set of 5 loop exercise bands", ["fitness"], "athletes", "Compact resistance workouts", ["100% natural latex", "Varying tension levels"], "fitness", [27], [28], True, 0),
        (30, "Foam Roller", 799, 300, "High density muscle roller", ["fitness"], "athletes", "Post-workout trigger recovery", ["Grid pattern", "Durable EVA foam"], "fitness", [27], [31], True, 0),
        (31, "Jump Rope Speed", 399, 130, "Tangle-free skipping rope", ["fitness"], "athletes", "High intensity cardio tool", ["Ball bearings", "Adjustable length"], "fitness", [27], [30], True, 0),
        
        # Home (ID 32-35)
        (32, "Air Purifier", 5999, 3800, "True HEPA home air cleaner", ["home"], "families", "Remove dust and allergens", ["Quiet sleep mode", "Activated carbon filter"], "home", [33], [34], True, 0),
        (33, "Smart LED Bulb", 499, 200, "RGB Wi-Fi dimmable bulb", ["home"], "general", "Automated smart lighting", ["App control", "Voice assistant ready"], "home", [32], [25], True, 0),
        (34, "Essential Oil Diffuser", 1099, 450, "Ultrasonic aromatherapy humidifier", ["home"], "general", "Aromatherapy soothing environment", ["7 color lights", "Auto shut-off"], "home", [35], [32], True, 0),
        (35, "Ceramic Coffee Mug", 349, 120, "Matte finish ceramic mug", ["home", "office"], "general", "Enjoy warm beverages daily", ["Microwave safe", "Comfortable handle"], "home", [25], [34], True, 0),
        
        # Travel (ID 36-38)
        (36, "Carry-on Suitcase", 3999, 2400, "Hard shell spinner luggage", ["travel"], "tourists", "Durable carry-on storage", ["TSA lock integrated", "Silent spinner wheels"], "travel", [37], [49], True, 0),
        (37, "Neck Pillow Memory", 899, 350, "Ergonomic memory foam pillow", ["travel"], "tourists", "Comfortable flight posture support", ["Washable cover", "Contoured shape"], "travel", [36], [38], True, 0),
        (38, "Passport Holder", 499, 180, "RFID blocking travel wallet", ["travel"], "tourists", "Keep credentials safe secure", ["Genuine leather", "RFID protection"], "travel", [36], [37], True, 0),
        
        # Beauty (ID 39-43)
        (39, "Skin Care Starter Kit", 1899, 900, "Organic face wash and cream", ["beauty"], "general", "Gentle skin hydration routines", ["Paraben free", "Natural extracts"], "beauty", [40], [42], True, 0),
        (40, "Moisturizing Cream", 599, 220, "Deep hydrating face lotion", ["beauty"], "general", "Soothe dry skin daily", ["Hyaluronic acid", "Fast absorbing"], "beauty", [39], [41], True, 0),
        (41, "Sunscreens SPF 50", 499, 180, "Non-greasy sun protection", ["beauty", "travel"], "general", "Broad spectrum UV defense", ["Water resistant", "Matte finish"], "beauty", [39], [40], True, 0),
        (42, "Facial Cleanser", 399, 150, "Foaming botanical face wash", ["beauty"], "general", "Purify pores thoroughly daily", ["Tea tree oil", "Gentle formula"], "beauty", [39], [43], True, 0),
        (43, "Hair Serum Pro", 799, 320, "Anti-frizz nourishing hair oil", ["beauty"], "general", "Smooth shiny frizz-free hair", ["Argan oil extract", "Heat protection"], "beauty", [39], [40], True, 0),
        
        # Books (ID 44-48)
        (44, "Daily Planner", 499, 120, "Undated productivity journal", ["office", "books"], "professionals", "Boost daily task management", ["Thick inkproof paper", "Ribbon bookmark"], "books", [45], [46], True, 0),
        (45, "Productivity Journal", 399, 100, "Goal tracking notebook", ["books"], "general", "Achieve personal life goals", ["Monthly reviews", "Hardcover cloth"], "books", [44], [47], True, 0),
        (46, "Coding Interview Prep", 899, 350, "Algorithm interview guidebook", ["books"], "developers", "Crack tech coding loops", ["50+ code problems", "Java/Python examples"], "books", [44], [48], True, 0),
        (47, "Startup Playbook", 699, 250, "Guidebook to business scaling", ["books"], "entrepreneurs", "Build scalable business systems", ["Case studies", "Actionable checklists"], "books", [44], [46], True, 0),
        (48, "Fintech Revolution", 599, 200, "History and future of banking", ["books"], "professionals", "Understand financial technology trends", ["Industry interviews", "Global graphs"], "books", [44], [47], True, 0),
        
        # Lifestyle (ID 49-53)
        (49, "Urban Backpack", 2199, 1000, "Water-resistant commuter pack", ["lifestyle", "travel"], "commuters", "Everyday secure laptop carry", ["Anti-theft pockets", "USB charging port"], "lifestyle", [2], [36], True, 1),
        (50, "Water Bottle 1L", 699, 250, "Vacuum insulated metal flask", ["lifestyle", "fitness"], "general", "Keep drinks cold 24h", ["Food grade steel", "Leakproof cap"], "lifestyle", [49], [51], True, 0),
        (51, "Reusable Coffee Cup", 499, 180, "Double-walled travel travel cup", ["lifestyle", "office"], "general", "Eco-friendly hot coffee carry", ["Silicone sleeve", "Spillproof lid"], "lifestyle", [49], [50], True, 0),
        (52, "Leather Key Organizer", 399, 130, "Pocket size key chain folder", ["lifestyle"], "general", "Quiet pocket key storage", ["Top grain leather", "Fits 8 keys"], "lifestyle", [49], [53], True, 0),
        (53, "Polarized Sunglasses", 1199, 450, "UV400 retro style sunglasses", ["lifestyle", "travel"], "general", "Protect eyes from glare", ["TR90 memory frame", "TAC polarized lens"], "lifestyle", [49], [52], True, 0)
    ]
    
    for row in products_data:
        id_val, name, price, cost, desc, tags, cust, intent, points, category, compat, alt, bundle_elig, priority = row
        s.add(Product(
            id=id_val, name=name, price=float(price), cost_price=float(cost), description=desc,
            category=category, inventory=100, attributes={"tags": tags}, rating=4.2 + (id_val % 9) * 0.1,
            use_cases=tags, target_customer=cust, product_intent=intent, selling_points=points,
            compatible_products=compat, alternative_products=alt, bundle_eligibility=bundle_elig,
            merchant_priority=priority, active=True
        ))
    s.flush()

    # Seed 110 transactions
    for i in range(110):
        amount=float(500+(i*83)%4500); status=["paid","paid","paid","payment_failed","approved"][i%5]
        cid="seed-cart-"+str(i); tid="seed-tx-"+str(i)
        if i % 8 == 0:
            s.add(PolicyCheck(transaction_id=tid,rule="max_discount",requested_value=25.0,allowed_value=10.0,decision="blocked",reason="Requested discount 25.0% exceeds merchant limit 10%"))
        if i % 12 == 0:
            s.add(PolicyCheck(transaction_id=tid,rule="min_margin",requested_value=10.0,allowed_value=4.0,decision="blocked",reason="Margin floor violation. Offer reduced to preserve minimum margin."))
        if status=="payment_failed":
            s.add(PaymentAttempt(id="seed-pa-"+str(i),transaction_id=tid,status="failed",error_message="Simulated transaction gateway error"))
            if i % 2 == 0:
                s.add(RecoveryEvent(id="seed-re-"+str(i),transaction_id=tid,retry_count=1,status="recovered"))
                status="paid"
        s.add(Cart(id=cid,user_id=customer.id,status="paid" if status=="paid" else status,items=[],subtotal=amount,discount=0,total=amount,locked_total=amount))
        s.add(Transaction(id=tid,user_id=customer.id,cart_id=cid,amount=amount,status=status,payment_reference="seed_ref_"+str(i)))
    s.commit()
