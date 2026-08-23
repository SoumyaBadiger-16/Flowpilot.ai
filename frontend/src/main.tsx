import React, { useEffect, useState, useRef } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// Global types
type User = { name: string; email: string; role: string };
type Product = {
  id: number; name: string; description: string; category: string; price: number;
  cost_price: number; inventory: number; rating: number; use_cases: string[];
  target_customer: string; product_intent: string; selling_points: string[];
  compatible_products: number[]; alternative_products: number[];
  bundle_eligibility: boolean; merchant_priority: number; active: boolean;
};
type Campaign = {
  id: string; name: string; description: string; discount_percent: number;
  target_category: string; budget: number; spent: number;
  expected_aov_boost: number; expected_revenue_boost: number; status: string;
};
type Rec = {
  session_id: string;
  intent: any;
  message: string;
  recommendation: {
    items: any[];
    subtotal: number;
    discount_percent: number;
    discount: number;
    total: number;
    margin: number;
    bundle: boolean;
    reasons: string[];
    blocked: string[];
    payable: boolean;
    cross_sells: Product[];
    original_total: number;
    savings: number;
    alternative_discount?: number;
    alternative_payable?: number;
  };
  candidates: Product[];
};

// Multilingual Dictionary
const TRANSLATIONS: Record<string, Record<string, string>> = {
  en: {
    logo: "flow", logo_sub: "pilot",
    tagline: "Policy-controlled AI commerce",
    hero_title: "Shop with a bounded AI agent.",
    hero_desc: "Discover, optimize, approve and pay — with every decision explained.",
    ask_placeholder: "Type your shopping request here (e.g. laptop under 60000)...",
    btn_ask: "Ask FlowPilot",
    btn_login: "Continue",
    customer_role: "AI shopping agent",
    merchant_role: "Merchant control center",
    recom_title: "Your AI-Approved Recommendation",
    cart_prepared: "Decision Cart prepared — review the locked total before payment.",
    payable_warning: "Policy blocks checkout above autonomous limit.",
    btn_approve: "Review & approve purchase",
    btn_pay: "Approve & pay securely",
    btn_simulate_fail: "Demo payment failure",
    btn_retry: "Retry Payment",
    payment_success: "Payment successful — complete audit record saved.",
    payment_failed: "Payment failed. Recovery agent is active.",
    catalog_title: "CATALOG AGENT RESULTS",
    back_to_shop: "Back to Shopping",
    logout: "Log out",
    shopping: "Shopping",
    catalog: "Catalog",
    cart: "Cart"
  },
  hi: {
    logo: "फ्लो", logo_sub: "पायलट",
    tagline: "नीति-नियंत्रित एआई वाणिज्य",
    hero_title: "सीमित एआई एजेंट के साथ खरीदें।",
    hero_desc: "खोजें, अनुकूलित करें, स्वीकृत करें और भुगतान करें — हर निर्णय स्पष्टीकरण के साथ।",
    ask_placeholder: "अपनी खरीदारी की आवश्यकता लिखें (जैसे: 60000 के तहत लैपटॉप)...",
    btn_ask: "फ्लोपायलट से पूछें",
    btn_login: "आगे बढ़ें",
    customer_role: "एआई शॉपिंग सहायक",
    merchant_role: "व्यापारी नियंत्रण केंद्र",
    recom_title: "आपकी एआई-स्वीकृत अनुशंसा",
    cart_prepared: "कार्ट तैयार है — भुगतान करने से पहले कुल मूल्य की समीक्षा करें।",
    payable_warning: "नीति सीमा से अधिक मूल्य का भुगतान अवरुद्ध करती है।",
    btn_approve: "समीक्षा और खरीद की स्वीकृति",
    btn_pay: "अनुमोदन और सुरक्षित भुगतान",
    btn_simulate_fail: "भुगतान विफलता का डेमो",
    btn_retry: "भुगतान पुन: प्रयास करें",
    payment_success: "भुगतान सफल — पूर्ण ऑडिट रिकॉर्ड सहेज लिया गया है।",
    payment_failed: "भुगतान विफल। रिकवरी एजेंट सक्रिय है।",
    catalog_title: "कैटलॉग परिणाम",
    back_to_shop: "खरीदारी पर वापस",
    logout: "लॉग आउट",
    shopping: "खरीदारी",
    catalog: "कैटलॉग",
    cart: "कार्ट"
  },
  kn: {
    logo: "ಫ್ಲೋ", logo_sub: "ಪೈಲಟ್",
    tagline: "ನೀತಿ-ನಿಯಂತ್ರಿತ ಎಐ ಕಾಮರ್ಸ್",
    hero_title: "ಮಿತಿಯುಳ್ಳ ಎಐ ಏಜೆಂಟ್ ಜೊತೆಗೆ ಶಾಪಿಂಗ್ ಮಾಡಿ.",
    hero_desc: "ಶೋಧಿಸಿ, ಉತ್ತಮಗೊಳಿಸಿ, ಅನುಮೋದಿಸಿ ಮತ್ತು ಪಾವತಿಸಿ — ಪ್ರತಿ ನಿರ್ಧಾರದ ವಿವರಣೆಯೊಂದಿಗೆ.",
    ask_placeholder: "ನಿಮ್ಮ ಶಾಪಿಂಗ್ ವಿನಂತಿಯನ್ನು ಇಲ್ಲಿ ಬರೆಯಿರಿ (ಉದಾ. 60000 ಕೆಳಗೆ ಲ್ಯಾಪ್‌ಟಾಪ್)...",
    btn_ask: "ಫ್ಲೋಪೈಲಟ್ ಕೇಳಿ",
    btn_login: "ಮುಂದುವರಿಯಿರಿ",
    customer_role: "ಎಐ ಶಾಪಿಂಗ್ ಏಜೆಂಟ್",
    merchant_role: "ಮರ್ಚೆಂಟ್ ನಿಯಂತ್ರಣ ಕೇಂದ್ರ",
    recom_title: "ನಿಮ್ಮ ಎಐ-ಅನುಮೋದಿತ ಶಿಫಾರಸು",
    cart_prepared: "ಕಾರ್ಟ್ ಸಿದ್ಧವಾಗಿದೆ — ಪಾವತಿಸುವ ಮುನ್ನ ಒಟ್ಟು ಮೊತ್ತವನ್ನು ಪರಿಶೀಲಿಸಿ.",
    payable_warning: "ನೀತಿಯು ಗರಿಷ್ಠ ಮಿತಿಗಿಂತ ಹೆಚ್ಚಿನ ಪಾವತಿಯನ್ನು ತಡೆಯುತ್ತದೆ.",
    btn_approve: "ಖರೀದಿಯನ್ನು ಪರಿಶೀಲಿಸಿ ಅನುಮೋದಿಸಿ",
    btn_pay: "ಅನುಮೋದಿಸಿ ಮತ್ತು ಸುರಕ್ಷಿತವಾಗಿ ಪಾವತಿಸಿ",
    btn_simulate_fail: "ಡೆಮೊ ಪಾವತಿ ವಿಫಲತೆ",
    btn_retry: "ಪಾವತಿ ಮರುಪ್ರಯತ್ನಿಸಿ",
    payment_success: "ಪಾವತಿ ಯಶಸ್ವಿಯಾಗಿದೆ — ಸಂಪೂರ್ಣ ಆಡಿಟ್ ದಾಖಲಿಸಲಾಗಿದೆ.",
    payment_failed: "ಪಾವತಿ ವಿಫಲವಾಗಿದೆ. ರಿಕವರಿ ಏಜೆಂಟ್ ಸಕ್ರಿಯವಾಗಿದೆ.",
    catalog_title: "ಕ್ಯಾಟಲಾಗ್ ಫಲಿತಾಂಶಗಳು",
    back_to_shop: "ಶಾಪಿಂಗ್‌ಗೆ ಹಿಂತಿರುಗಿ",
    logout: "ಲಾಗ್ ಔಟ್",
    shopping: "ಶಾಪಿಂಗ್",
    catalog: "ಕ್ಯಾಟಲಾಗ್",
    cart: "ಕಾರ್ಟ್"
  }
};

// API helper
async function api(path: string, method = 'GET', body?: unknown) {
  const token = localStorage.getItem('fp_token');
  const r = await fetch(API + path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: body ? JSON.stringify(body) : undefined
  });
  const json = await r.json();
  if (!r.ok) throw new Error(json.detail || 'Request failed');
  return json;
}

// Format Money in INR
function Money({ n }: { n: number }) {
  return <>₹{Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</>;
}

// --- LOGIN COMPONENT ---
function Login({ onLogin }: { onLogin: (u: User) => void }) {
  const [email, setEmail] = useState('demo@flowpilot.test');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr('');
    try {
      const x = await api('/api/auth/login', 'POST', { email });
      localStorage.setItem('fp_token', x.token);
      onLogin(x.user);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="login">
      <section>
        <div className="logo">flow<span>pilot</span></div>
        <p className="tagline">Policy-controlled AI commerce</p>
        <h1>Secure agentic commerce for modern platforms.</h1>
        <p className="muted">Discover, bundle, verify policies, and authorize transactions in real-time.</p>
      </section>
      <form onSubmit={submit}>
        <h2>Sign In</h2>
        <label>Email Address</label>
        <input value={email} onChange={e => setEmail(e.target.value)} required />
        <small className="demo-accounts">
          Customer: <code>demo@flowpilot.test</code><br />
          Merchant: <code>merchant@flowpilot.test</code>
        </small>
        {err && <p className="error">{err}</p>}
        <button disabled={busy}>{busy ? 'Signing In...' : 'Continue'}</button>
      </form>
    </main>
  );
}

// --- CUSTOMER AI SHOPPING MODULE ---
function Shopper({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [lang, setLang] = useState('en');
  const t = TRANSLATIONS[lang];

  const [activeTab, setActiveTab] = useState<'chat' | 'catalog' | 'cart'>('chat');
  const [message, setMessage] = useState('I need a wireless keyboard and mouse for under 2500');
  const [result, setResult] = useState<Rec>();
  const [busy, setBusy] = useState(false);
  const [cart, setCart] = useState<any>();
  const [status, setStatus] = useState('');
  const [payError, setPayError] = useState(false);
  const [products, setProducts] = useState<Product[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);

  // Fetch product catalog
  useEffect(() => {
    api('/api/products').then(setProducts).catch(e => setStatus(e.message));
  }, []);

  const searchCatalog = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const prods = await api(`/api/products?q=${searchQuery}`);
      setProducts(prods);
    } catch (e: any) {
      setStatus(e.message);
    }
  };

  // Voice Commerce
  const startVoiceInput = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser. Please use text input.");
      return;
    }
    const rec = new SpeechRecognition();
    rec.lang = lang === 'hi' ? 'hi-IN' : lang === 'kn' ? 'kn-IN' : 'en-US';
    setStatus("Listening...");
    rec.onresult = (e: any) => {
      const text = e.results[0][0].transcript;
      setMessage(text);
      setStatus("");
    };
    rec.onerror = () => setStatus("Speech error or microphone blocked.");
    rec.start();
  };

  const ask = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setBusy(true);
    setStatus('');
    setPayError(false);
    try {
      const res = await api('/api/chat', 'POST', { message });
      setResult(res);
      setCart(null);
    } catch (e: any) {
      setStatus(e.message);
    } finally {
      setBusy(false);
    }
  };

  const addCrossSell = async (p: Product) => {
    if (!result) return;
    const currentItems = result.recommendation.items.map(x => ({ product_id: x.id, quantity: x.quantity }));
    // Append the cross sell product
    currentItems.push({ product_id: p.id, quantity: 1 });
    setBusy(true);
    try {
      const res = await api('/api/checkout/preview', 'POST', {
        items: currentItems,
        discount_percent: result.recommendation.discount_percent
      });
      setResult(prev => prev ? { ...prev, recommendation: res } : undefined);
      setStatus(`Added ${p.name} to cart.`);
    } catch (e: any) {
      setStatus(e.message);
    } finally {
      setBusy(false);
    }
  };

  const createCart = async () => {
    if (!result) return;
    try {
      const c = await api('/api/cart', 'POST', {
        items: result.recommendation.items.map((x: any) => ({ product_id: x.id, quantity: x.quantity })),
        discount_percent: result.recommendation.discount_percent
      });
      setCart(c);
      setStatus(t.cart_prepared);
    } catch (e: any) {
      setStatus(e.message);
    }
  };

  const acceptChallenge = async () => {
    if (!result) return;
    try {
      setStatus("Policy Firewall: Initializing challenge flow...");
      const c = await api('/api/cart', 'POST', {
        items: result.recommendation.items.map((x: any) => ({ product_id: x.id, quantity: x.quantity })),
        discount_percent: result.recommendation.discount_percent
      });
      const res = await api('/api/checkout/challenge', 'POST', {
        cart_id: c.cart_id,
        alternative_discount: result.recommendation.alternative_discount
      });
      setCart({ cart_id: c.cart_id, ...c, total: result.recommendation.alternative_payable, discount_percent: result.recommendation.alternative_discount });
      setStatus(`Policy Alternative Accepted! Order approved at Rs. ${result.recommendation.alternative_payable}.`);
    } catch (e: any) {
      setStatus(e.message);
    }
  };

  const pay = async (fail = false) => {
    try {
      setPayError(false);
      const a = await api('/api/checkout/approve', 'POST', { cart_id: cart.cart_id });
      const o = await api('/api/payment/create-order', 'POST', {
        transaction_id: a.transaction_id,
        simulate_failure: fail
      });

      if (o.mode === 'razorpay') {
        setStatus('Razorpay Test Mode order created. Configure keys to open Checkout.');
        return;
      }

      const verified = await api('/api/payment/verify', 'POST', {
        transaction_id: a.transaction_id,
        status: 'success'
      });

      if (verified.status === 'paid') {
        setStatus(t.payment_success);
        setCart(null);
      }
    } catch (e: any) {
      setStatus(e.message);
      setPayError(true);
    }
  };

  const retryRecovery = async () => {
    if (!cart) return;
    try {
      // Find the last transaction matching our approval amount
      setStatus("Recovery Agent: Attempting retry workflow...");
      const txRes = await api('/api/payment/retry', 'POST', { transaction_id: cart.cart_id });
      setStatus(txRes.message);
      setPayError(false);
    } catch (e: any) {
      setStatus(e.message);
    }
  };

  return (
    <main className="shell">
      <header>
        <div className="logo">{t.logo}<span>{t.logo_sub}</span></div>
        <div className="header-meta">
          <span className="pill">{t.customer_role}</span>
          <select value={lang} onChange={e => setLang(e.target.value)} className="lang-selector">
            <option value="en">English</option>
            <option value="hi">हिंदी (Hindi)</option>
            <option value="kn">ಕನ್ನಡ (Kannada)</option>
          </select>
          <button onClick={onLogout} className="btn-logout">{t.logout}</button>
        </div>
      </header>

      <nav className="tab-navigation">
        <button className={activeTab === 'chat' ? 'active' : ''} onClick={() => setActiveTab('chat')}>{t.shopping}</button>
        <button className={activeTab === 'catalog' ? 'active' : ''} onClick={() => setActiveTab('catalog')}>{t.catalog}</button>
      </nav>

      {activeTab === 'chat' && (
        <div className="shop-grid">
          <section className="conversation">
            <div className="eyebrow">CONVERSATIONAL COMMERCE</div>
            <h1>{t.hero_title}</h1>
            <p className="muted">{t.hero_desc}</p>

            <form className="chat" onSubmit={ask}>
              <div className="chat-input-wrapper">
                <textarea
                  placeholder={t.ask_placeholder}
                  value={message}
                  onChange={e => setMessage(e.target.value)}
                />
                <button type="button" onClick={startVoiceInput} className="btn-voice" title="Speak request">🎤</button>
              </div>
              <button disabled={busy} className="btn-ask">{busy ? 'Thinking…' : t.btn_ask}</button>
            </form>

            <div className="chips">
              <button onClick={() => setMessage('Find a laptop with mouse under 60000')}>Laptop Bundle</button>
              <button onClick={() => setMessage('Can I get 20% off noise cancel headphones?')}>Negotiate Discount (20%)</button>
              <button onClick={() => setMessage('Yoga mat under 2000')}>Yoga Mat</button>
            </div>

            {status && (
              <div className={`notice ${payError ? 'error-notice' : ''}`}>
                <p>{status}</p>
                {payError && (
                  <button onClick={retryRecovery} className="btn-retry-now">{t.btn_retry}</button>
                )}
              </div>
            )}

            {result && (
              <div className="trace-section">
                <div className="eyebrow">AGENT DECISION TRACE</div>
                <div className="trace-timeline">
                  <div className="trace-step">
                    <strong>Intent Agent</strong>
                    <p>Primary category: <b>{result.intent.primary_category || 'None'}</b></p>
                    <p>Required product(s): <b>{result.intent.required_products.join(', ') || 'None'}</b></p>
                    <p>Budget: <b>{result.intent.budget ? `₹${result.intent.budget}` : 'None'}</b></p>
                    <p>Intent: <b>{result.intent.intent_type}</b></p>
                  </div>
                  <div className="trace-step">
                    <strong>Catalog Agent</strong>
                    <p>Found {result.candidates.length} primary candidates.</p>
                    <p>Found {result.recommendation ? Math.max(0, result.recommendation.items.length - 1) : 0} compatible complementary candidates.</p>
                  </div>
                  <div className="trace-step">
                    <strong>Recommendation Agent</strong>
                    <p>Shortlisted the best combination based on:</p>
                    <ul style={{ paddingLeft: '20px', fontSize: '13px', margin: '4px 0', color: 'var(--text-muted)' }}>
                      <li>Budget criteria limit</li>
                      <li>Relevance match score</li>
                      <li>Inventory availability</li>
                      <li>Customer intent mapping</li>
                    </ul>
                  </div>
                  <div className="trace-step">
                    <strong>Growth Agent</strong>
                    <p>
                      {result.recommendation && result.recommendation.bundle 
                        ? 'Found an eligible primary + accessory bundle.' 
                        : 'Identified upsell & cross-sell offers.'}
                    </p>
                  </div>
                  <div className="trace-step">
                    <strong>Policy Agent</strong>
                    <p>Discount: <b>{result.recommendation ? result.recommendation.discount_percent : 0}%</b></p>
                    <p>Margin: <b>{result.recommendation ? result.recommendation.margin : 0}%</b></p>
                    <p>Required margin: <b>18%</b></p>
                    <p>Status: <b className={result.recommendation && result.recommendation.blocked.length > 0 ? 'blocked-alert' : 'approved-alert'}>
                      {result.recommendation && result.recommendation.blocked.length > 0 ? 'BLOCKED' : 'APPROVED'}
                    </b></p>
                  </div>
                  <div className="trace-step">
                    <strong>Customer Approval</strong>
                    <p>{cart ? 'Customer approved cart.' : 'Waiting for customer approval.'}</p>
                  </div>
                  <div className="trace-step">
                    <strong>Payment Agent</strong>
                    <p>{cart ? 'Payment authorization pending.' : 'Payment may begin only after approval.'}</p>
                  </div>
                  <div className="trace-step">
                    <strong>Audit Agent</strong>
                    <p>Decision and transaction events recorded in ledger.</p>
                  </div>
                </div>
              </div>
            )}
          </section>
 
          <aside className="cart">
            <div className="eyebrow">{t.recom_title}</div>
            {!result ? (
              <div className="empty-cart-state">
                <p className="muted">Your policy-checked recommendations will appear here.</p>
              </div>
            ) : !result.recommendation ? (
              <div className="cart-content">
                <h3>{result.message}</h3>
              </div>
            ) : (
              <div className="cart-content">
                {/* AI Purchase Plan Header */}
                <div style={{ marginBottom: '16px', borderBottom: '1px solid var(--panel-border)', paddingBottom: '8px' }}>
                  <div className="eyebrow" style={{ color: 'var(--primary)', fontWeight: 'bold' }}>AI PURCHASE PLAN</div>
                  <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    {result.recommendation.bundle ? 'Optimize Bundle Offer' : 'Single Product Offer'}
                  </span>
                </div>

                <h3>{result.message}</h3>
                
                <div className="items-list">
                  {result.recommendation.items.map((x: any, idx: number) => (
                    <div className="item" key={x.id}>
                      <div>
                        <b>{x.name}</b>
                        <small>
                          {idx === 0 ? 'Primary Product' : 'Required Complementary Product'} · {x.category}
                        </small>
                      </div>
                      <b><Money n={x.line_total} /></b>
                    </div>
                  ))}
                </div>
 
                <div className="breakdown">
                  <div className="row">
                    <span>Original price</span>
                    <span><Money n={result.recommendation.subtotal} /></span>
                  </div>
                  {result.recommendation.discount > 0 && (
                    <div className="row green">
                      <span>Discount ({result.recommendation.discount_percent}%)</span>
                      <span>−<Money n={result.recommendation.discount} /></span>
                    </div>
                  )}
                  <div className="row total">
                    <strong>Final payable</strong>
                    <strong><Money n={result.recommendation.total} /></strong>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '12px 0', fontSize: '13px' }}>
                  <span>Policy Status</span>
                  <strong className={result.recommendation.blocked.length > 0 ? 'blocked-alert' : 'approved-alert'}>
                    {result.recommendation.blocked.length > 0 ? 'BLOCKED' : 'APPROVED'}
                  </strong>
                </div>
 
                {result.recommendation.cross_sells.length > 0 && (
                  <div className="cross-sells">
                    <div className="eyebrow">UPSELL & CROSS-SELL OFFERS</div>
                    {result.recommendation.cross_sells.map(p => (
                      <div className="cross-sell-item" key={p.id}>
                        <div>
                          <span>{p.name}</span>
                          <small>₹{p.price} · Rating {p.rating}★</small>
                        </div>
                        <button onClick={() => addCrossSell(p)}>+ Add</button>
                      </div>
                    ))}
                  </div>
                )}
 
                <div className="reasons">
                  {result.recommendation.reasons.map((r: string, idx) => (
                    <span className="reason-pill" key={idx}>✓ {r}</span>
                  ))}
                  {result.recommendation.blocked.map((r: string, idx) => (
                    <span className="reason-pill warning" key={idx}>Policy: {r}</span>
                  ))}
                </div>

                {/* Challenge Decision Section */}
                {result.recommendation.blocked.length > 0 && (
                  <div className="challenge-section" style={{ marginTop: '16px', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid #f59e0b', padding: '16px', borderRadius: '8px' }}>
                    <div className="eyebrow" style={{ color: '#f59e0b', fontWeight: 'bold' }}>POLICY FIREWALL FEEDBACK</div>
                    <p style={{ fontSize: '13px', margin: '4px 0 12px', color: 'var(--text-muted)' }}>
                      Requested discount is unauthorized. AI alternative: <b>{result.recommendation.alternative_discount}% approved discount</b> (Payable: Rs. {result.recommendation.alternative_payable})
                    </p>
                    <button className="primary" onClick={acceptChallenge} style={{ margin: '0', background: '#f59e0b', color: '#fff', border: '0', padding: '10px 14px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', width: '100%' }}>
                      Accept Alternative
                    </button>
                  </div>
                )}
 
                {!cart ? (
                  <button
                    disabled={!result.recommendation.payable}
                    className="primary"
                    onClick={createCart}
                    style={!result.recommendation.payable ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
                  >
                    {result.recommendation.payable ? t.btn_approve : 'Blocked by Policy'}
                  </button>
                ) : (
                  <div className="payment-options" style={{ marginTop: '20px' }}>
                    <button className="primary" onClick={() => pay(false)} style={{ margin: '0' }}>{t.btn_pay}</button>
                    <button className="secondary" onClick={() => pay(true)} style={{ marginTop: '8px', width: '100%' }}>{t.btn_simulate_fail}</button>
                  </div>
                )}
              </div>
            )}
          </aside>
        </div>
      )}

      {activeTab === 'catalog' && (
        <section className="catalog-browser">
          <div className="catalog-header">
            <h1>Structured Product Catalog</h1>
            <form onSubmit={searchCatalog} className="search-form">
              <input
                type="text"
                placeholder="Search products by name or category..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
              />
              <button type="submit">Search</button>
            </form>
          </div>

          <div className="products-grid">
            {products.map(p => (
              <article key={p.id} className="product-card" onClick={() => setSelectedProduct(p)}>
                <span className="category-badge">{p.category}</span>
                <h3>{p.name}</h3>
                <p className="desc">{p.description.slice(0, 80)}...</p>
                <div className="card-footer">
                  <strong>₹{p.price}</strong>
                  <span className="rating">{p.rating}★</span>
                </div>
              </article>
            ))}
          </div>

          {selectedProduct && (
            <div className="modal-backdrop" onClick={() => setSelectedProduct(null)}>
              <div className="modal-content" onClick={e => e.stopPropagation()}>
                <span className="close" onClick={() => setSelectedProduct(null)}>&times;</span>
                <span className="category-badge">{selectedProduct.category}</span>
                <h2>{selectedProduct.name}</h2>
                <p className="price">₹{selectedProduct.price}</p>
                <p>{selectedProduct.description}</p>
                
                <div className="ai-metadata">
                  <div className="eyebrow">AGENT-READABLE AI METADATA</div>
                  <div className="grid">
                    <div>
                      <strong>Target customer</strong>
                      <p>{selectedProduct.target_customer}</p>
                    </div>
                    <div>
                      <strong>Product intent</strong>
                      <p>{selectedProduct.product_intent}</p>
                    </div>
                  </div>
                  <div>
                    <strong>Key Selling Points</strong>
                    <ul>
                      {selectedProduct.selling_points.map((pt, idx) => <li key={idx}>{pt}</li>)}
                    </ul>
                  </div>
                  <div>
                    <strong>Use Cases</strong>
                    <p>{selectedProduct.use_cases.join(', ')}</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>
      )}
    </main>
  );
}

// --- MERCHANT PANEL & DASHBOARD MODULE ---
function Merchant({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [dash, setDash] = useState<any>();
  const [tx, setTx] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [policy, setPolicy] = useState<any>();
  const [msg, setMsg] = useState('');

  // Simulator
  const [simDiscount, setSimDiscount] = useState(8);
  const [simCategory, setSimCategory] = useState('Electronics');
  const [simDuration, setSimDuration] = useState(14);
  const [simCrossSell, setSimCrossSell] = useState(true);
  const [simResults, setSimResults] = useState<any>(null);

  // Playground
  const [playInput, setPlayInput] = useState('I need a Laptop under 35000 with a 30% discount');
  const [playResult, setPlayResult] = useState<any>(null);

  // Campaign Orchestrator
  const [campaignGoal, setCampaignGoal] = useState('Increase headphone sales this weekend');
  const [proposedCampaign, setProposedCampaign] = useState<any>(null);

  // Copilot Drawer
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [copilotQuery, setCopilotQuery] = useState('');
  const [copilotHistory, setCopilotHistory] = useState<any[]>([
    { sender: 'ai', text: 'Hello! I am your Merchant AI Copilot. Ask me about your revenue, campaigns, or failed payments.' }
  ]);

  const loadData = () => {
    Promise.all([
      api('/api/merchant/dashboard'),
      api('/api/merchant/transactions'),
      api('/api/merchant/audit'),
      api('/api/merchant/policies'),
      api('/api/merchant/campaigns')
    ]).then(([d, t, a, p, c]) => {
      setDash(d);
      setTx(t);
      setAuditLogs(a);
      setPolicy(p);
      setCampaigns(c);
    }).catch(e => setMsg(e.message));
  };

  useEffect(() => {
    loadData();
  }, []);

  const savePolicy = async () => {
    try {
      await api('/api/merchant/policies', 'POST', policy);
      setMsg('Merchant policy updated successfully.');
      loadData();
    } catch (e: any) {
      setMsg(e.message);
    }
  };

  const runSimulation = async () => {
    try {
      const res = await api('/api/merchant/simulate', 'POST', {
        discount_percent: simDiscount,
        target_category: simCategory,
        duration_days: simDuration,
        cross_sell_enabled: simCrossSell,
        target_segment: 'All Customers'
      });
      setSimResults(res);
    } catch (e: any) {
      setMsg(e.message);
    }
  };

  const runPlayground = async () => {
    try {
      const res = await api('/api/merchant/playground', 'POST', {
        message: playInput
      });
      setPlayResult(res);
    } catch (e: any) {
      setMsg(e.message);
    }
  };

  const proposeCampaign = async () => {
    try {
      const res = await api('/api/merchant/campaigns/propose', 'POST', {
        goal: campaignGoal
      });
      setProposedCampaign(res);
    } catch (e: any) {
      setMsg(e.message);
    }
  };

  const approveCampaign = async (id: string) => {
    try {
      await api(`/api/merchant/campaigns/${id}/approve`, 'POST');
      setProposedCampaign(null);
      setMsg('Campaign approved and activated.');
      loadData();
    } catch (e: any) {
      setMsg(e.message);
    }
  };

  const rejectCampaign = () => {
    setProposedCampaign(null);
    setMsg('Campaign proposal rejected.');
  };

  const sendCopilotMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!copilotQuery.trim()) return;
    const userMsg = copilotQuery;
    setCopilotHistory(prev => [...prev, { sender: 'user', text: userMsg }]);
    setCopilotQuery('');
    try {
      const res = await api(`/api/merchant/copilot?q=${encodeURIComponent(userMsg)}`);
      setCopilotHistory(prev => [...prev, { sender: 'ai', text: res.response }]);
    } catch (e: any) {
      setCopilotHistory(prev => [...prev, { sender: 'ai', text: `Error: ${e.message}` }]);
    }
  };

  if (!dash) {
    return <main className="shell">Loading merchant console... {msg}</main>;
  }

  return (
    <main className="shell">
      <header>
        <div className="logo">flow<span>pilot</span></div>
        <div className="header-meta">
          <span className="pill">Merchant control center</span>
          <button onClick={() => setCopilotOpen(true)} className="btn-copilot-toggle">🤖 Ask Copilot</button>
          <button onClick={onLogout} className="btn-logout">Log out</button>
        </div>
      </header>

      <section className="metrics">
        <article>
          <small>TOTAL REVENUE</small>
          <strong><Money n={dash.revenue} /></strong>
        </article>
        <article>
          <small>AI-ASSISTED REVENUE</small>
          <strong><Money n={dash.ai_assisted_revenue} /></strong>
          <span className="stat-sub font-green">({Math.round(dash.ai_assisted_revenue/dash.revenue*100)}% of total)</span>
        </article>
        <article>
          <small>PAYMENT RECOVERY RATE</small>
          <strong>{dash.recovery_rate}%</strong>
          <span className="stat-sub">Failed orders salvaged</span>
        </article>
        <article>
          <small>POLICY SAFETY RATE</small>
          <strong>{dash.policy_safety_rate}%</strong>
          <span className="stat-sub">Off-policy blocks</span>
        </article>
        <article>
          <small>CROSS-SELL / BUNDLE</small>
          <strong>{dash.bundle_acceptance}%</strong>
          <span className="stat-sub">Bundle conversion</span>
        </article>
      </section>

      <div className="merchant-grid">
        <div className="panel flex-col gap-6">
          <div className="panel-header">
            <div className="eyebrow">POLICY FIREWALL BOUNDARIES</div>
            <button onClick={savePolicy} className="btn-save-policy">Save policy</button>
          </div>
          {policy && (
            <div className="policy-inputs">
              <label>Maximum Discount (%)</label>
              <input
                type="number"
                value={policy.max_discount}
                onChange={e => setPolicy({ ...policy, max_discount: +e.target.value })}
              />
              <label>Minimum Margin (%)</label>
              <input
                type="number"
                value={policy.min_margin}
                onChange={e => setPolicy({ ...policy, min_margin: +e.target.value })}
              />
              <label>Max Autonomous Order (₹)</label>
              <input
                type="number"
                value={policy.max_order_value}
                onChange={e => setPolicy({ ...policy, max_order_value: +e.target.value })}
              />
            </div>
          )}
          {msg && <p className="notice">{msg}</p>}
        </div>

        <div className="panel">
          <div className="eyebrow">REVENUE SIMULATOR</div>
          <div className="simulator-grid">
            <div className="inputs">
              <label>Discount (%): {simDiscount}</label>
              <input
                type="range" min="1" max="25"
                value={simDiscount}
                onChange={e => setSimDiscount(+e.target.value)}
              />
              <label>Category</label>
              <select value={simCategory} onChange={e => setSimCategory(e.target.value)}>
                <option value="Electronics">Electronics</option>
                <option value="Office">Office</option>
                <option value="Gaming">Gaming</option>
                <option value="Fitness">Fitness</option>
              </select>
              <button onClick={runSimulation} className="btn-simulate">Run Simulation</button>
            </div>
            <div className="outputs">
              {simResults ? (
                <>
                  <p>Expected Conversion: <strong className="green">{simResults.expected_conversion}</strong></p>
                  <p>Expected AOV: <strong className="green">{simResults.expected_aov}</strong></p>
                  <p>Est. Gross Revenue: <strong>₹{simResults.expected_revenue.toLocaleString()}</strong></p>
                  <p>Est. Discount Cost: <span className="warning">₹{simResults.discount_cost.toLocaleString()}</span></p>
                  <p>Net Impact Estimate: <strong>₹{simResults.estimated_net_impact.toLocaleString()}</strong></p>
                </>
              ) : (
                <p className="muted text-center py-6">Adjust sliders and click simulate to preview campaign impact.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="merchant-grid">
        <div className="panel">
          <div className="eyebrow">CAMPAIGN ORCHESTRATOR</div>
          <div className="campaign-orchestrator-ui">
            <label>Business Goal</label>
            <div className="orchestrator-input">
              <input
                type="text"
                value={campaignGoal}
                onChange={e => setCampaignGoal(e.target.value)}
                placeholder="e.g. increase headphone sales this weekend..."
              />
              <button onClick={proposeCampaign}>Propose Campaign</button>
            </div>

            {proposedCampaign && (
              <div className="campaign-proposal-card">
                <h3>Campaign Proposal: {proposedCampaign.name}</h3>
                <p className="desc">{proposedCampaign.description}</p>
                <div className="details">
                  <span>Target: <b>{proposedCampaign.target_category}</b></span>
                  <span>Discount: <b>{proposedCampaign.discount_percent}%</b></span>
                  <span>Budget: <b>₹{proposedCampaign.budget.toLocaleString()}</b></span>
                </div>
                <div className="actions">
                  <button onClick={() => approveCampaign(proposedCampaign.id)} className="btn-approve-c">Approve Campaign</button>
                  <button onClick={rejectCampaign} className="btn-reject-c">Reject</button>
                </div>
              </div>
            )}

            <div className="campaigns-list">
              <h4>Active Campaigns</h4>
              {campaigns.map(c => (
                <div className="campaign-row" key={c.id}>
                  <div>
                    <strong>{c.name}</strong>
                    <p>{c.description}</p>
                  </div>
                  <span className={`status-badge ${c.status}`}>{c.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="eyebrow">AGENT PLAYGROUND</div>
          <div className="playground-ui">
            <label>Customer Request Query</label>
            <textarea
              value={playInput}
              onChange={e => setPlayInput(e.target.value)}
            />
            <button onClick={runPlayground} className="btn-run-agent">Run Agent Trace</button>

            {playResult && (
              <div className="playground-output">
                <div className="agent-item">
                  <span>Intent Agent</span>
                  <strong>{playResult.intent_agent}</strong>
                </div>
                <div className="agent-item">
                  <span>Catalog Agent</span>
                  <strong>{playResult.catalog_agent}</strong>
                </div>
                <div className="agent-item">
                  <span>Policy Agent</span>
                  <strong className={playResult.policy_agent === 'BLOCKED' ? 'red' : 'green'}>{playResult.policy_agent}</strong>
                </div>
                {playResult.blocked_reasons.length > 0 && (
                  <div className="alert-box">
                    <strong>Blocked Reason:</strong>
                    <p>{playResult.blocked_reasons.join(', ')}</p>
                    {playResult.alternative && (
                      <p className="alt">Alternative: {playResult.alternative}</p>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="eyebrow">IMMUTABLE AUDIT EXPLORER</div>
        <div className="audit-ledger">
          {auditLogs.slice(0, 15).map(a => (
            <div className="audit-row" key={a.id}>
              <div className="meta">
                <strong>{a.event_type.replaceAll('_', ' ').toUpperCase()}</strong>
                <small>{a.actor} · {new Date(a.timestamp).toLocaleString()}</small>
              </div>
              <p className="details">{JSON.stringify(a.details)}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Copilot Drawer */}
      {copilotOpen && (
        <div className="copilot-drawer">
          <div className="drawer-header">
            <h3>Merchant AI Copilot</h3>
            <button onClick={() => setCopilotOpen(false)}>&times;</button>
          </div>
          <div className="drawer-content">
            <div className="messages">
              {copilotHistory.map((m, idx) => (
                <div className={`message-bubble ${m.sender}`} key={idx}>
                  <p>{m.text}</p>
                </div>
              ))}
            </div>
            <div className="copilot-chips">
              <button onClick={() => setCopilotQuery('Why did revenue fall yesterday?')}>Why did revenue fall?</button>
              <button onClick={() => setCopilotQuery('Which product should I promote today?')}>What to promote?</button>
              <button onClick={() => setCopilotQuery('How many payments failed?')}>Payment failures</button>
            </div>
            <form onSubmit={sendCopilotMessage} className="drawer-input">
              <input
                type="text"
                placeholder="Ask a question about dashboard..."
                value={copilotQuery}
                onChange={e => setCopilotQuery(e.target.value)}
              />
              <button type="submit">Send</button>
            </form>
          </div>
        </div>
      )}
    </main>
  );
}

// --- MAIN APPLICATION ROUTER ---
function App() {
  const [user, setUser] = useState<User | null>(null);

  // Authenticate user check
  useEffect(() => {
    const token = localStorage.getItem('fp_token');
    if (token) {
      // Decode user role from token locally for state
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        setUser({
          name: payload.role === 'merchant' ? 'Ava Merchant' : 'Demo Customer',
          email: payload.role === 'merchant' ? 'merchant@flowpilot.test' : 'demo@flowpilot.test',
          role: payload.role
        });
      } catch (e) {
        localStorage.removeItem('fp_token');
      }
    }
  }, []);

  const handleLogin = (u: User) => {
    setUser(u);
  };

  const handleLogout = () => {
    localStorage.removeItem('fp_token');
    setUser(null);
  };

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  return user.role === 'merchant' ? (
    <Merchant user={user} onLogout={handleLogout} />
  ) : (
    <Shopper user={user} onLogout={handleLogout} />
  );
}

createRoot(document.getElementById('root')!).render(<App />);
