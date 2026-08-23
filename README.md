# FlowPilot

FlowPilot is a policy-controlled AI commerce MVP for Razorpay merchants. Customers describe their need in plain language; bounded agents select products, form bundles, apply only policy-approved offers, require approval, then prepare a payment and write an audit trail.

## Quick start

Requirements: Python 3.11+ and Node 20+.

1. Copy `.env.example` to `.env` and set `JWT_SECRET`. Leave Razorpay values empty for the included safe Test Mode simulator, or use Razorpay **Test Mode** keys only.
2. Backend:
   ```powershell
   cd backend
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
3. Frontend (second terminal):
   ```powershell
   cd frontend
   npm.cmd install
   npm.cmd run dev
   ```
4. Open `http://127.0.0.1:5173`.

Demo accounts: `demo@flowpilot.test` (customer) and `merchant@flowpilot.test` (merchant). No password is used in the local demo; production deployments must replace this with an identity provider/password flow.

## Payments

With `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` set to Test Mode values, the backend creates a Razorpay order. Without keys, it uses a local simulator so the approval, failure, retry, and immutable-audit workflows remain demonstrable without secrets. The “Demo payment failure” button intentionally returns a provider error while preserving the cart; approve and retry to continue. Card data is never handled or stored by FlowPilot.

## Key routes

- `POST /api/chat` runs bounded Intent, Catalog, Recommendation, Growth, and Policy agents.
- `POST /api/cart`, `/api/checkout/approve`, `/api/payment/create-order`, and `/api/payment/verify` form the approval-gated payment lifecycle.
- `/api/merchant/dashboard`, `/transactions`, `/agent-runs`, `/policies`, and `/audit` provide merchant observability.

Swagger API docs are at `http://127.0.0.1:8000/docs`. SQLite is seeded on first startup with 50 products and 100 transactions. Delete `backend/flowpilot.db` only if you explicitly want a fresh local demo dataset.
