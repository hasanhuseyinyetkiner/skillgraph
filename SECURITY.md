# Security boundaries

SkillGraph is a **local demo / MVP**, not a multi-tenant SaaS or production HR platform.

## Assumptions

- Default bind is loopback (`127.0.0.1` / `localhost` / `::1`). Non-loopback hosts require an explicit `ALLOW_NETWORK_BIND=true` opt-in (see `backend/app/settings.py`).
- No multi-user authentication or authorization in this MVP.
- Intended data is **synthetic** (demo profile Avery Chen, seeded ontology). Do not load real employee PII, protected attributes, or live HR system exports.
- CORS is limited to the paired demo UI origins (`http://127.0.0.1:5105`, `http://localhost:5105` by default). CORS is not an authentication mechanism.
- Embeddings are optional and off by default (`EMBEDDINGS_ENABLED=false`). Enabling them does not change the loopback / no-auth boundaries above.

## Product limits (not security theater)

- Fit index and role rankings are **exploratory coverage measures**, not hiring probabilities, promotion decisions, or person scores.
- No protected attributes are used in scoring.
- Export / erase / reset exist for the demo profile inventory; treat them as demo convenience, not a full retention or GDPR control plane.

## Reporting

If you find a vulnerability in this repository, open a private report via GitHub Security Advisories for the repo (when available) or contact the maintainer listed in [`LICENSE`](LICENSE). Please do not file public issues that include exploit details for remote bind / data-exfiltration paths until a fix is available.

## What this is not

- Not a production security posture claim.
- Not a claim of vulnerability-free dependencies, images, or supply chain.
- Not suitable for real workforce decisioning without authn/z, tenancy, audit logging, retention, and a full security redesign.
