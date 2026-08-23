# Architecture

`Customer request → Intent → Catalog → Recommendation → Growth → Policy → explicit approval → Payment → Audit`

Agent outputs are structured and treated as untrusted input. The policy engine independently validates price, inventory, discount ceiling, margin floor, and autonomous amount ceiling. Approval locks the cart total; payment cannot change it. Every recommendation, approval, payment event, and policy update is written as an append-only audit event from normal application workflows.

The backend deliberately keeps payment credentials in environment variables. Razorpay is called only from the backend with Test Mode keys. Webhooks require an HMAC signature and reject missing/invalid signatures.
