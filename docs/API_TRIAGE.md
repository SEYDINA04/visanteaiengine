# Visanté AI Engine – API documentation

All endpoints are **REST** (HTTP). There are **no WebSocket** endpoints.

Base URL (local): `http://localhost:8000`  
API prefix: `/api/v1`

---

## 1. AI triage flow (3 steps)

| Step | When | Endpoint | Type | Purpose |
|------|------|----------|------|---------|
| 1 | Start conversation | `POST /api/v1/triage/start` | REST | Start session, get first question |
| 2 | User answers each question | `POST /api/v1/triage/answer` | REST | Send answer, get next question or final outcome |
| 3 | After triage ended | `GET /api/v1/triage/result/{session_id}` | REST | Fetch full triage report |

---

## 2. Step 1 – Start triage (AI triage stage start)

**Endpoint:** `POST /api/v1/triage/start`  
**Type:** REST (JSON request/response)

### Request payload (body)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `patient_id` | string or `null` | No | `null` | Optional patient identifier |
| `language` | string | No | `"en"` | Language code for questions |
| `channel` | string | No | `"web"` | e.g. `"web"`, `"mobile"` |

**Minimal request (all optional):**

```json
{}
```

**Full example:**

```json
{
  "patient_id": "patient-123",
  "language": "en",
  "channel": "web"
}
```

### Response payload (200 OK)

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "triage_state": "ongoing",
  "first_question": {
    "question_id": "chief_complaint",
    "text": "What is your main reason for seeking care today?"
  }
}
```

| Field | Description |
|-------|-------------|
| `session_id` | UUID string – **use this for all later requests** |
| `triage_state` | Always `"ongoing"` at start |
| `first_question.question_id` | Use as `question_id` in the first `POST /triage/answer` |
| `first_question.text` | Question to show or speak to the user |

---

## 3. Step 2 – Send answers (during “user has spoken to the AI”)

**Endpoint:** `POST /api/v1/triage/answer`  
**Type:** REST (JSON request/response)

Call this once per question. Use `session_id` from start and `question_id` from the last response (or `first_question.question_id` for the first answer).

### Request payload (body)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `session_id` | string | Yes | From `POST /triage/start` response |
| `question_id` | string | Yes | From current question (e.g. `chief_complaint`, then from `next_question.question_id`) |
| `answer` | string | Yes | User’s answer (non-empty) |

**Example (first answer):**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "question_id": "chief_complaint",
  "answer": "I have a headache and fever"
}
```

**Example (later answer):**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "question_id": "duration",
  "answer": "About 2 days"
}
```

### Response payload – three shapes

The backend returns one of three shapes depending on whether triage continues, ends as emergency, or ends as completed.

**A) Triage continues (next question)** – `triage_state: "ongoing"`

```json
{
  "triage_state": "ongoing",
  "next_question": {
    "question_id": "duration",
    "text": "How long have you had these symptoms?"
  },
  "progress": 0.1
}
```

Keep calling `POST /api/v1/triage/answer` with the new `question_id` and the user’s next answer until you get **B** or **C**.

**B) Emergency** – `triage_state: "emergency"`

```json
{
  "triage_state": "emergency",
  "severity_level": "critical",
  "recommendation": "Seek emergency care.",
  "confidence_score": 0.9
}
```

Triage is finished. Use `GET /api/v1/triage/result/{session_id}` to get the full report.

**C) Completed (non-emergency)** – `triage_state: "completed"`

```json
{
  "triage_state": "completed",
  "severity_level": "low",
  "recommendation": "Rest and fluids. See a doctor if symptoms persist.",
  "confidence_score": 0.85
}
```

Triage is finished. Use `GET /api/v1/triage/result/{session_id}` to get the full report.

### Question IDs (in order)

You will receive these `question_id` values in sequence:  
`chief_complaint` → `duration` → `severity_self` → `fever` → `breathing` → `chest_pain` → `consciousness` → `bleeding` → `pain_level` → `other_symptoms`.

### Errors

| Status | Meaning |
|--------|---------|
| 404 | `session_id` not found (wrong ID or session never created) |
| 400 | Session not ongoing (triage already ended); or invalid body |
| 422 | Validation error (e.g. missing `session_id`, `question_id`, or empty `answer`) |

---

## 4. Step 3 – Fetch triage details (after user has spoken to the AI)

**Endpoint:** `GET /api/v1/triage/result/{session_id}`  
**Type:** REST (no body; response is JSON)

Use this **only after** triage has ended (`triage_state` is `"emergency"` or `"completed"` from `POST /triage/answer`).

### Request

- **Method:** GET  
- **URL:** `GET /api/v1/triage/result/{session_id}`  
- **Path parameter:** `session_id` – same UUID from `POST /triage/start`  
- **Body:** none  

Example: `GET /api/v1/triage/result/550e8400-e29b-41d4-a716-446655440000`

### Response payload (200 OK)

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "chief_complaint": "I have a headache and fever",
  "symptoms": [
    "I have a headache and fever",
    "About 2 days",
    "moderate",
    "Yes"
  ],
  "risk_flags": [],
  "severity_level": "low",
  "triage_category": "low",
  "recommendation": "Rest and fluids. See a doctor if symptoms persist.",
  "confidence_score": 0.85,
  "created_at": "2025-02-26T12:00:00Z"
}
```

| Field | Description |
|-------|-------------|
| `session_id` | Session UUID |
| `status` | `"completed"` or `"emergency"` |
| `chief_complaint` | First-answer summary |
| `symptoms` | List of all answers (in question order) |
| `risk_flags` | List of risk strings identified |
| `severity_level` | `"low"`, `"moderate"`, `"high"`, or `"critical"` |
| `triage_category` | Category label |
| `recommendation` | Care recommendation text |
| `confidence_score` | 0.0–1.0 |
| `created_at` | Session creation time (ISO 8601) |

### Errors

| Status | Meaning |
|--------|---------|
| 404 | Session not found |
| 400 | Triage not finished yet (`triage_state` still `"ongoing"`) |

---

## 5. Summary table

| What you do | Endpoint | Method | Payload you send | Payload you get |
|-------------|----------|--------|------------------|-----------------|
| Start AI triage | `/api/v1/triage/start` | POST | `{}` or `{ "patient_id", "language", "channel" }` | `session_id`, `first_question` |
| Send each answer | `/api/v1/triage/answer` | POST | `{ "session_id", "question_id", "answer" }` | Either next question (`ongoing`), or `emergency` / `completed` with recommendation |
| Fetch full details after triage | `/api/v1/triage/result/{session_id}` | GET | None (session_id in URL) | Full report: status, chief_complaint, symptoms, risk_flags, severity_level, recommendation, etc. |

All of the above are **REST** endpoints (HTTP + JSON). No WebSockets are used.
