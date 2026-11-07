# ProofLine API Contract

Base URL: `http://localhost:8000`

---

## Health Check

### `GET /health`

Returns the service health status.

- **Auth:** None
- **Roles:** Any
- **Request body:** None
- **Response (200):**
  ```json
  { "status": "ok", "service": "proofline-api" }
  ```

---

## Authentication

### `POST /auth/login`

Authenticate a user and receive a JWT token.

- **Auth:** None
- **Roles:** Any
- **Request body:**
  ```json
  { "email": "string", "password": "string" }
  ```
- **Response (200):**
  ```json
  { "access_token": "string", "token_type": "bearer" }
  ```
- **Status:** 501 Not Implemented

---

## Sources

### `POST /sources/guidelines`

Upload or create guideline rules for the organisation.

- **Auth:** Bearer JWT
- **Roles:** Admin
- **Request body:**
  ```json
  { "rule_id": "string", "text": "string", "category": "string" }
  ```
- **Response (201):**
  ```json
  { "id": "uuid", "rule_id": "string", "text": "string", "category": "string", "version": 1, "is_active": true }
  ```
- **Status:** 501 Not Implemented

### `POST /sources/facts`

Upload or create fact entries for the organisation.

- **Auth:** Bearer JWT
- **Roles:** Admin
- **Request body:**
  ```json
  { "statement": "string", "value": "string", "owner": "string", "source": "string", "expires_on": "date | null" }
  ```
- **Response (201):**
  ```json
  { "id": "uuid", "statement": "string", "value": "string", "owner": "string", "source": "string", "expires_on": "date | null", "version": 1 }
  ```
- **Status:** 501 Not Implemented

### `POST /sources/terms`

Upload or create terminology entries for the organisation.

- **Auth:** Bearer JWT
- **Roles:** Admin
- **Request body:**
  ```json
  { "term": "string", "preferred": "string", "banned": false, "notes": "string | null" }
  ```
- **Response (201):**
  ```json
  { "id": "uuid", "term": "string", "preferred": "string", "banned": false, "notes": "string | null" }
  ```
- **Status:** 501 Not Implemented

### `GET /sources`

List all sources (guidelines, facts, terminology) for the organisation.

- **Auth:** Bearer JWT
- **Roles:** Admin, Reviewer
- **Request body:** None
- **Response (200):**
  ```json
  {
    "guidelines": [{ "id": "uuid", "rule_id": "string", "text": "string", "category": "string", "version": 1, "is_active": true }],
    "facts": [{ "id": "uuid", "statement": "string", "value": "string", "owner": "string", "source": "string", "expires_on": "date | null", "version": 1 }],
    "terms": [{ "id": "uuid", "term": "string", "preferred": "string", "banned": false, "notes": "string | null" }]
  }
  ```
- **Status:** 501 Not Implemented

---

## Drafts

### `POST /drafts`

Create a new draft.

- **Auth:** Bearer JWT
- **Roles:** Creator, Admin
- **Request body:**
  ```json
  { "content": "string", "channel": "string | null" }
  ```
- **Response (201):**
  ```json
  { "id": "uuid", "organisation_id": "uuid", "created_by": "uuid", "channel": "string | null", "status": "draft", "created_at": "datetime" }
  ```
- **Status:** 501 Not Implemented

### `POST /drafts/{id}/review`

Trigger an automated review of the draft's latest version.

- **Auth:** Bearer JWT
- **Roles:** Creator, Admin
- **Request body:** None
- **Response (202):**
  ```json
  { "draft_id": "uuid", "version": 1, "findings_count": 0, "status": "review_started" }
  ```
- **Status:** 501 Not Implemented

### `GET /drafts/{id}/versions/{v}/findings`

Get all findings for a specific draft version.

- **Auth:** Bearer JWT
- **Roles:** Creator, Reviewer, Admin
- **Request body:** None
- **Response (200):**
  ```json
  [
    {
      "id": "string",
      "draft_id": "string",
      "version_id": "string",
      "quoted_text": "string",
      "start": 0,
      "end": 10,
      "severity": "blocker | warning | note",
      "reason": "string",
      "source_ref": "string",
      "source_version": 1,
      "confidence": "high | medium | low",
      "suggestion": "string | null",
      "status": "open | accepted | edited | dismissed",
      "dismissal_reason": "string | null"
    }
  ]
  ```
- **Status:** 501 Not Implemented

### `POST /drafts/{id}/request-review`

Request a human review of the draft.

- **Auth:** Bearer JWT
- **Roles:** Creator
- **Request body:** None
- **Response (202):**
  ```json
  { "draft_id": "uuid", "status": "review_requested" }
  ```
- **Status:** 501 Not Implemented

### `POST /drafts/{id}/comments`

Add a comment to a draft, optionally anchored to a text range.

- **Auth:** Bearer JWT
- **Roles:** Creator, Reviewer, Admin
- **Request body:**
  ```json
  { "text": "string", "range_start": "int | null", "range_end": "int | null" }
  ```
- **Response (201):**
  ```json
  { "id": "uuid", "draft_id": "uuid", "user_id": "uuid", "text": "string", "range_start": "int | null", "range_end": "int | null", "created_at": "datetime" }
  ```
- **Status:** 501 Not Implemented

### `POST /drafts/{id}/decision`

Record an approval decision on a draft.

- **Auth:** Bearer JWT
- **Roles:** Reviewer, Admin
- **Request body:**
  ```json
  { "decision": "approved | rejected | needs_changes", "reason": "string | null" }
  ```
- **Response (201):**
  ```json
  { "id": "uuid", "draft_id": "uuid", "user_id": "uuid", "decision": "string", "reason": "string | null", "created_at": "datetime" }
  ```
- **Status:** 501 Not Implemented

### `GET /drafts/{id}/receipt`

Get the review receipt for a draft.

- **Auth:** Bearer JWT
- **Roles:** Creator, Reviewer, Admin
- **Request body:** None
- **Response (200):**
  ```json
  { "id": "uuid", "claim_id": "uuid", "organisation_id": "uuid", "receipt_data": {} }
  ```
- **Status:** 501 Not Implemented

---

## Findings

### `PATCH /findings/{id}`

Update the status or dismissal reason of a finding.

- **Auth:** Bearer JWT
- **Roles:** Creator, Reviewer, Admin
- **Request body:**
  ```json
  { "status": "open | accepted | edited | dismissed", "dismissal_reason": "string | null" }
  ```
- **Response (200):**
  ```json
  { "id": "string", "status": "string", "dismissal_reason": "string | null" }
  ```
- **Status:** 501 Not Implemented

---

## Insights

### `GET /insights/rules`

Get rule performance analytics (most triggered rules, acceptance rates, etc.).

- **Auth:** Bearer JWT
- **Roles:** Admin
- **Request body:** None
- **Response (200):**
  ```json
  [
    { "rule_id": "string", "trigger_count": 0, "acceptance_rate": 0.0 }
  ]
  ```
- **Status:** 501 Not Implemented

---

## Audit

### `GET /audit`

Get the audit log entries.

- **Auth:** Bearer JWT
- **Roles:** Admin
- **Request body:** None
- **Response (200):**
  ```json
  [
    {
      "id": "uuid",
      "user_id": "uuid | null",
      "action": "string",
      "entity": "string",
      "entity_id": "uuid | null",
      "details": {},
      "created_at": "datetime"
    }
  ]
  ```
- **Status:** 501 Not Implemented

