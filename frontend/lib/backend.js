/**
 * Live ProofLine FastAPI Backend Bridge for frontend-proofline.
 * Real JWT-based auth — no hardcoded demo accounts.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const JWT_KEY = "proofline.jwt";
const USER_KEY = "proofline.user";

// ---------------------------------------------------------------------------
// Token / session helpers
// ---------------------------------------------------------------------------

export function getBackendToken() {
  if (typeof window === "undefined") return null;
  try {
    return sessionStorage.getItem(JWT_KEY);
  } catch {
    return null;
  }
}

export function clearBackendToken() {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(JWT_KEY);
    sessionStorage.removeItem(USER_KEY);
  } catch {}
}

export function getStoredUser() {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function storeSession(data) {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(JWT_KEY, data.access_token);
    sessionStorage.setItem(USER_KEY, JSON.stringify(data.user));
  } catch {}
}

// ---------------------------------------------------------------------------
// Low-level fetch wrapper
// ---------------------------------------------------------------------------

async function apiRequest(path, options = {}, tokenOverride = null) {
  const token = tokenOverride || getBackendToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      // Guard: FastAPI sometimes returns non-string detail (e.g. validation array)
      detail = typeof err.detail === "string" ? err.detail : detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Auth API calls
// ---------------------------------------------------------------------------

export async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_URL}/health`);
    if (!res.ok) return false;
    const data = await res.json();
    return data?.status === "ok";
  } catch {
    return false;
  }
}

/** Login with real credentials. Returns user profile or throws. */
export async function login(email, password, expectedRole = null) {
  const data = await apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (expectedRole) {
    const normUserRole = data.user?.role === "reviewer" ? "manager" : data.user?.role;
    const normExpected = expectedRole === "reviewer" ? "manager" : expectedRole;
    if (normUserRole && normUserRole !== normExpected && data.user?.role !== "admin") {
      const displayExpected = normExpected === "creator" ? "Creator" : "Manager";
      const displayActual = normUserRole === "creator" ? "Creator" : "Manager";
      throw new Error(
        `This account is registered as a ${displayActual}, but you selected ${displayExpected}. Please select ${displayActual} to sign in.`
      );
    }
  }
  storeSession(data);
  return data.user;
}

/** Register a new company + first user. Returns user profile or throws. */
export async function register(companyName, fullName, email, password, role = "manager") {
  const data = await apiRequest("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      company_name: companyName,
      full_name: fullName,
      email,
      password,
      role,
    }),
  });
  storeSession(data);
  return data.user;
}

/** Fetch companies list for autocomplete. */
export async function fetchCompanies() {
  try {
    return await apiRequest("/auth/companies");
  } catch {
    return [];
  }
}

/** Re-validate the stored JWT and return the user profile. */
export async function getMe() {
  return apiRequest("/auth/me");
}

// ---------------------------------------------------------------------------
// Draft review API
// ---------------------------------------------------------------------------

function capitalize(str) {
  if (!str) return "";
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

function mapClaimStatus(status) {
  const map = {
    supported: "Supported",
    conflicts: "Conflicts",
    expired_evidence: "Expired evidence",
    unsupported: "Unsupported",
    needs_human: "Needs a human",
  };
  return map[status] || "Needs a human";
}

export async function runBackendReview(draft) {
  const writerToken = getBackendToken();
  if (!writerToken) {
    throw new Error("Not authenticated — please sign in first");
  }

  let backendDraftId = draft.backendId;
  let versionNumber = 1;

  if (!backendDraftId) {
    const created = await apiRequest(
      "/drafts",
      {
        method: "POST",
        body: JSON.stringify({
          title: draft.title || "Untitled Draft",
          content: draft.text,
          channel: draft.channel || "Email",
          intent_lock: draft.intent || {},
        }),
      },
      writerToken
    );
    backendDraftId = created.id;
  } else {
    const ver = await apiRequest(
      `/drafts/${backendDraftId}/versions`,
      {
        method: "POST",
        body: JSON.stringify({
          content: draft.text,
          intent_lock: draft.intent || {},
        }),
      },
      writerToken
    );
    versionNumber = ver.version_number;
  }

  const reviewSummary = await apiRequest(
    `/drafts/${backendDraftId}/review`,
    { method: "POST" },
    writerToken
  );

  const [findingsRaw, claimsRaw] = await Promise.all([
    apiRequest(
      `/drafts/${backendDraftId}/versions/${reviewSummary.version || versionNumber}/findings`,
      { method: "GET" },
      writerToken
    ),
    apiRequest(
      `/drafts/${backendDraftId}/versions/${reviewSummary.version || versionNumber}/claims`,
      { method: "GET" },
      writerToken
    ),
  ]);

  const mappedFindings = findingsRaw.map((f) => ({
    id: `AI-${f.id}`,
    backendFindingId: f.id,
    start: f.start ?? 0,
    original: f.quoted_text || "",
    source: {
      id: f.source_ref,
      title: `${f.source_ref} (AI Grounded)`,
      type:
        f.source_type === "fact"
          ? "Approved facts"
          : f.source_type === "term"
          ? "Terminology"
          : "Guidelines",
      version: f.source_version || 1,
    },
    title: `${capitalize(f.severity)}: ${f.source_ref}`,
    severity: capitalize(f.severity),
    reason: f.reason,
    suggested: f.suggestion || null,
    confidence: capitalize(f.confidence),
    decision: f.status === "open" ? "open" : f.status,
    note: f.dismissal_reason || "",
  }));

  const mappedClaims = claimsRaw.map((c) => ({
    text: c.quoted_text || "",
    status: mapClaimStatus(c.status),
    source: {
      id: c.source_ref || "FACT-LEDGER",
      title: c.source_ref || "Fact Ledger",
      version: c.evidence_version || 1,
    },
  }));

  return {
    backendId: backendDraftId,
    findings: mappedFindings,
    claims: mappedClaims,
    summary: reviewSummary,
  };
}

export async function syncBackendDecision(backendDraftId, decision, reason) {
  if (!backendDraftId) return null;
  try {
    const token = getBackendToken();
    if (!token) return null;
    return await apiRequest(
      `/drafts/${backendDraftId}/decision`,
      {
        method: "POST",
        body: JSON.stringify({
          decision: decision === "approved" ? "approved" : "changes_requested",
          reason: reason || "Reviewed in ProofLine workspace",
        }),
      },
      token
    );
  } catch {
    return null;
  }
}

export async function searchBackendRag(query) {
  try {
    const token = getBackendToken();
    if (!token) return null;
    return await apiRequest(
      `/sources/rag-search?query=${encodeURIComponent(query)}&top_k=5`,
      { method: "GET" },
      token
    );
  } catch {
    return null;
  }
}
