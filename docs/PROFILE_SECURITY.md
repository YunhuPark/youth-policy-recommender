# Profile access and AI request limits

`POST /api/profile` now returns `profile_id` and a separate `access_token`.
Keep the token private and send `Authorization: Bearer <access_token>` when
reading/updating that profile or its recommendation history. The token belongs
only to that profile; a second profile needs its own token. Mongo stores only a
SHA-256 digest and profile responses exclude it. There is no email/account
identity in this anonymous application, so the token is the ownership capability.
Losing it requires creating a new profile. Do not log it or put it in a URL.
Capabilities expire 30 days after creation and cannot be extended by a profile
update. A trusted operator can revoke one immediately by setting its profile's
`is_active` to false (or deleting it). Legacy/missing expiry fields fail closed.
Use TLS in deployment. The browser's API service keeps the latest orchestrator
capability in memory and provides profile read/update/history helpers; it is
discarded on page reload/close and never written to localStorage or URLs.
Orchestrator responses issue the token only to their caller, after saving
history; history never stores plaintext capabilities.

Existing records created before the security upgrade have no ownership proof and
are denied. Recreate them with the user's consent; never issue a new token based
only on possession of the old short profile ID. Existing operators may export or
delete old data through their trusted database administration workflow.

Explanation and orchestrator requests accept at most 10 policies/results. Text
input and individual explanation policy objects are bounded. `/api/explain`
requires each item to contain a `policy_id`, re-reads that policy from Mongo,
and ignores caller-supplied policy prose. Unknown IDs fail before provider calls.
Provider output is capped at 300 tokens with a 15-second timeout and no retries
if the currently disabled OpenAI integration is enabled in the future. The
existing anonymous recommendation flow remains public, with conservative shared
budget limits rather than claimed account authentication. Both entrypoints
share an atomic SQLite policy-call budget in `backend/.runtime/ai-budget.db`:
200 reserved policy explanations per UTC day globally and 20 per IP per minute
by default. Override `AI_DAILY_POLICY_LIMIT`, `AI_IP_MINUTE_POLICY_LIMIT` and
`AI_BUDGET_DB` through trusted deployment configuration. Rejected/failed provider
requests do not refund reservations, so concurrency and retries cannot bypass
the cap. Put the budget database on persistent local storage shared by all app
workers. Multiple independent hosts need a shared external gateway budget before
scaling; per-host SQLite cannot enforce an account-wide quota across hosts.

Only the socket peer IP is trusted. Behind a proxy clients may share its IP;
configure the ASGI server's trusted proxies rather than accepting arbitrary
forwarded headers in application code. The global budget remains enforced in
either case. Provider-side spend limits remain an additional safeguard.
