---
title: Compass — Signup & Workspace Provisioning
category: backend
author: tomas.herrera@meridiandata.io
team: Growth Eng
created: 2023-02-14
updated: 2026-05-30
status: current
version: 2.2
---

# Compass

Compass owns the flow from "someone hit the Sign Up button" to "the new
workspace is usable and has sample data in it." It is small on purpose —
most of what it does is orchestrate other services. Everything Compass does
must be safely re-runnable, because the signup flow retries on any
half-completed provisioning.

## Runtime

- **Language:** Python 3.11
- **Framework:** FastAPI + Uvicorn.
- **Deployment:** EKS (us-west-2), 2-pod baseline, HPA to 8.
- **Owner:** Growth Eng (Tomás Herrera).

## Endpoints

```
POST /v3/signup                            # email + password (or OAuth token)
POST /v3/signup/verify-email
POST /v3/workspaces                        # create additional workspace for user
GET  /v3/workspaces/{id}/provisioning       # status of async provisioning
POST /v3/workspaces/{id}/reseed-samples    # (support-only, requires staff JWT)
```

## Provisioning steps

When a new workspace is created, Compass runs these steps as a background
task keyed by `provisioning_id`:

1. **Insert** a row into Postgres `workspaces` (status `provisioning`).
   Columns include `id`, `slug`, `name`, `plan` (defaults to `starter`),
   `created_by_user_id`, `region` (`us` — the EU toggle is not GA yet).
2. **Provision default schemas** by calling Cartograph:
   `POST /v1/workspaces/{id}/schemas:bootstrap`. This loads our standard
   e-commerce event set (`page_viewed`, `product_viewed`, `add_to_cart`,
   `checkout_started`, `order_completed`).
3. **Seed sample data** by copying a fixture from S3
   (`s3://meridian-sample-data/starter-shopify/`) into
   `events` under the new `workspace_id`. This is ~120k events spanning
   90 days. Copy is done by a signed presigned-URL job into Pulse's
   backfill topic, so the data flows through the same enrichment pipeline
   as live customer data.
4. **Create the first API write key**, insert into `write_keys` and return
   its plaintext value **once** in the response.
5. **Send the welcome email** via Postmark using template `welcome-v3`
   (dynamic variables: `first_name`, `workspace_slug`, `write_key`).
6. **Flip** `workspaces.status` to `active` and publish
   `WorkspaceProvisioned` on the internal `platform.events` bus.

FastAPI wiring for step 1:

```python
@router.post("/v3/workspaces", response_model=WorkspaceCreated, status_code=202)
async def create_workspace(
    body: CreateWorkspaceRequest,
    user: AuthedUser = Depends(auth.current_user),
    tasks: BackgroundTasks = None,
) -> WorkspaceCreated:
    ws = await workspaces.insert_provisioning_row(body, user)
    tasks.add_task(provisioning.run, workspace_id=ws.id)
    return WorkspaceCreated(id=ws.id, provisioning_id=ws.provisioning_id)
```

## Error handling

If any step fails, Compass marks
`workspaces.provisioning_state = 'failed:{step}'` and enqueues a retry via
SQS (`compass-provisioning-retries`, visibility 60s, max 5 attempts). After
5 failures a PagerDuty incident is created against App on-call and the
workspace is left in `failed`; the user sees a "we're setting things up,
this is taking longer than expected" page in Portal until support intervenes.

Common error codes:

| Code       | Meaning                                                 |
|------------|---------------------------------------------------------|
| `CMP-4409` | Slug already taken                                      |
| `CMP-5210` | Cartograph schema bootstrap failed                      |
| `CMP-5220` | Sample data copy failed                                 |
| `CMP-5230` | Postmark rejected the welcome email (bad address, etc.) |

## Related

- `backend/cartograph.md` — schema bootstrap endpoint.
- `backend/ledger-service.md` — Compass posts a `SubscriptionCreated`
  message that Ledger consumes to open a Stripe subscription in trial.
- `frontend/portal-authentication.md` — session cookies are set by
  Gatekeeper after Compass confirms signup, not by Compass itself.
