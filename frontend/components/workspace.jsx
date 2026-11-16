"use client";

import { useEffect, useState } from "react";
import {
  Bell,
  BookOpen,
  ChartNoAxesColumn,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  FileText,
  House,
  ListChecks,
  LogOut,
  PanelLeft,
  Search,
} from "lucide-react";
import {
  blockers,
  makeDraft,
  reviewDraft,
  roles,
  seedWorkspace,
  sourceLabel,
  stamp,
  versionOf,
} from "../lib/workflow.mjs";
import {
  checkBackendHealth,
  clearBackendToken,
  fetchBackendDrafts,
  fetchBackendSources,
  getBackendToken,
  getStoredUser,
  mapBackendDraftToFrontend,
  requestBackendHumanReview,
  runBackendReview,
  syncBackendDecision,
} from "../lib/backend";
import Login from "./login";
import { Dashboard, DraftList } from "./dashboard";
import { DraftScreen } from "./draft";
import { Alerts, Audit, Insights, Library } from "./governance";
import { Button, Toast, Wordmark } from "./ui";

const demoWorkspaceKey = "proofline.workspace.v1";
const accountKey = "proofline.writer-account";
const roleKey = "proofline.role";
const writerNav = [
  ["home", "Home", House],
  ["drafts", "My drafts", FileText],
  ["library", "Brand library", BookOpen],
];
const managerNav = [
  ["home", "Overview", House],
  ["queue", "Review queue", ClipboardCheck],
  ["library", "Brand library", BookOpen],
  ["insights", "Insights", ChartNoAxesColumn],
  ["alerts", "Alerts", Bell],
  ["audit", "Audit log", ListChecks],
];
const readRoute = () => window.location.hash.slice(1).split("/");
const hasSource = (draft, id) =>
  [...draft.findings, ...draft.claims, ...(draft.receipt?.claims || [])].some(
    (entry) => entry.source.id === id
  );
const evidenceOf = (draft) => [
  ...new Map(
    [...draft.findings, ...draft.claims].map((entry) => [
      entry.source.id,
      entry.source,
    ])
  ).values(),
];

export default function Workspace() {
  const [data, setData] = useState(null);
  const [role, setRole] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [workspaceKey, setWorkspaceKey] = useState(demoWorkspaceKey);
  const [route, setRoute] = useState(["home"]);
  const [notice, setNotice] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [storageWarning, setStorageWarning] = useState(false);
  const [backendLive, setBackendLive] = useState(false);
  const [aiReviewing, setAiReviewing] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("proofline.sidebar.collapsed");
      if (saved === "true") setSidebarCollapsed(true);
    } catch {}
  }, []);

  function toggleSidebar() {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("proofline.sidebar.collapsed", String(next));
      } catch {}
      return next;
    });
  }

  // Init: restore session, check backend health
  useEffect(() => {
    checkBackendHealth().then(setBackendLive);
    try {
      // Restore user profile from sessionStorage
      const storedUser = getStoredUser();
      const writerId = sessionStorage.getItem(accountKey);
      const hasAuth = (writerId || storedUser?.id) && getBackendToken();
      const key = hasAuth
        ? `${demoWorkspaceKey}.${writerId || storedUser?.id}`
        : demoWorkspaceKey;
      setWorkspaceKey(key);
      // For authenticated sessions start with empty state; hydrateFromDB fills it
      setData({ drafts: [], sources: [], events: [], alerts: [] });

      if (storedUser && getBackendToken()) {
        const isMgr = storedUser.role === "manager" || storedUser.role === "reviewer" || storedUser.role === "admin";
        const uiRole = isMgr ? "manager" : "writer";
        setRole(uiRole);
        setUserProfile(storedUser);
        // Async hydration from DB
        setTimeout(() => {
          fetchBackendDrafts()
            .then((remoteDrafts) => {
              if (!Array.isArray(remoteDrafts)) return;
              const mapped = remoteDrafts.map(mapBackendDraftToFrontend);
              setData((prev) => {
                if (!prev) return prev;
                const remoteIds = new Set(mapped.map((d) => d.id));
                const localOnly = (prev.drafts || []).filter(
                  (d) => !d.backendId && !remoteIds.has(d.id)
                );
                return { ...prev, drafts: [...mapped, ...localOnly] };
              });
            })
            .catch(() => {});
        }, 100);
      } else {
        const active = sessionStorage.getItem(roleKey);
        if (Object.hasOwn(roles, active) && (!writerId || getBackendToken())) setRole(active);
      }
    } catch {
      setData({ drafts: [], sources: [], events: [], alerts: [] });
      setStorageWarning(true);
    }
    const read = () => setRoute(readRoute());
    read();
    window.addEventListener("hashchange", read);
    return () => window.removeEventListener("hashchange", read);
  }, []);

  // Watch for cross-tab localStorage changes (keyed to current workspaceKey)
  useEffect(() => {
    const refresh = (event) => {
      if (event.key !== workspaceKey || !event.newValue) return;
      try {
        setData(JSON.parse(event.newValue));
      } catch {
        setStorageWarning(true);
      }
    };
    window.addEventListener("storage", refresh);
    return () => window.removeEventListener("storage", refresh);
  }, [workspaceKey]);

  // Automatic hydration pass from backend (Loophole 3)
  useEffect(() => {
    const token = getBackendToken();
    if (!backendLive || !token) return;

    let cancelled = false;

    async function hydrate() {
      try {
        const [remoteDrafts, remoteSources] = await Promise.all([
          fetchBackendDrafts(),
          fetchBackendSources(),
        ]);

        if (cancelled || !remoteDrafts) return;

        setData((prev) => {
          if (!prev) return prev;
          let nextDrafts = [...prev.drafts];

          if (remoteDrafts.length > 0) {
            const isMockSeed = prev.drafts.every(
              (d) =>
                d.id === "summer-launch" ||
                d.id === "product-refresh" ||
                d.id === "launch-announcement" ||
                d.id === "november-newsletter"
            );

            const mappedRemote = remoteDrafts.map((d) => {
              const existing = prev.drafts.find(
                (loc) => loc.backendId === d.id || loc.id === d.id
              );
              if (existing) {
                return {
                  ...existing,
                  backendId: d.id,
                  title: d.title || existing.title,
                  text: d.content || existing.text,
                  channel: d.channel || existing.channel,
                  status: d.status || existing.status,
                  version: d.latest_version || existing.version,
                  intent:
                    d.intent_lock && Object.keys(d.intent_lock).length
                      ? d.intent_lock
                      : existing.intent,
                };
              }
              return {
                id: d.id,
                backendId: d.id,
                title: d.title || "Untitled Draft",
                text: d.content || "",
                channel: d.channel || "Email",
                intent: d.intent_lock || { message: "", audience: "", action: "" },
                visual: { foreground: "", background: "" },
                attachment: "",
                status: d.status || "draft",
                version: d.latest_version || 1,
                versions: [
                  {
                    version: d.latest_version || 1,
                    text: d.content || "",
                    findings: 0,
                    date: d.created_at || new Date().toISOString(),
                    note: "Initial version",
                  },
                ],
                checked: d.status !== "draft",
                findings: [],
                claims: [],
                risk: "Low",
                comments: [],
                receipt:
                  d.status === "approved" || d.status === "published"
                    ? {
                        version: d.latest_version || 1,
                        claims: [],
                        date: d.created_at || new Date().toISOString(),
                        approver: "Manager",
                      }
                    : null,
                legal: "",
                updated: d.created_at || new Date().toISOString(),
              };
            });

            if (isMockSeed) {
              nextDrafts = mappedRemote;
            } else {
              const remoteIds = new Set(mappedRemote.map((m) => m.id));
              const localKept = prev.drafts.filter(
                (loc) => !remoteIds.has(loc.id) && !remoteIds.has(loc.backendId)
              );
              nextDrafts = [...mappedRemote, ...localKept];
            }
          }

          let nextSources = [...prev.sources];
          if (remoteSources) {
            const existingKeys = new Set(prev.sources.map((s) => s.id));
            const newBackendSources = [];

            (remoteSources.guidelines || []).forEach((g) => {
              const sId = g.rule_id || g.id;
              if (!existingKeys.has(sId)) {
                existingKeys.add(sId);
                newBackendSources.push({
                  id: sId,
                  backendId: g.id,
                  type: "Guidelines",
                  check: g.category || "tone",
                  title: (g.text || "").slice(0, 50),
                  source: "Company Policy",
                  owner: "Brand",
                  version: g.version || 1,
                  text: g.text || "",
                });
              }
            });

            (remoteSources.facts || []).forEach((f) => {
              const sId = f.fact_key || f.id;
              if (!existingKeys.has(sId)) {
                existingKeys.add(sId);
                newBackendSources.push({
                  id: sId,
                  backendId: f.id,
                  type: "Approved facts",
                  title: (f.statement || f.fact_key || "").slice(0, 50),
                  source: f.source || "Fact Ledger",
                  owner: f.owner || "Company",
                  version: f.version || 1,
                  value: f.value || "",
                  text: f.statement || "",
                  expires: f.expires_on || "2027-12-31",
                  keyword: f.fact_key || "",
                });
              }
            });

            (remoteSources.terms || []).forEach((t) => {
              const sId = t.id;
              if (!existingKeys.has(sId)) {
                existingKeys.add(sId);
                newBackendSources.push({
                  id: sId,
                  backendId: t.id,
                  type: "Terminology",
                  title: t.preferred ? `Use "${t.preferred}"` : t.term,
                  source: "Brand Guide",
                  owner: "Brand",
                  version: t.version || 1,
                  keyword: t.term,
                  value: t.preferred || "",
                  text:
                    t.notes ||
                    (t.banned
                      ? `Do not use "${t.term}". Prefer "${t.preferred || ""}".`
                      : `Approved term: "${t.term}"`),
                });
              }
            });

            if (newBackendSources.length > 0) {
              nextSources = [...prev.sources, ...newBackendSources];
            }
          }

          const nextState = { ...prev, drafts: nextDrafts, sources: nextSources };
          try {
            localStorage.setItem(workspaceKey, JSON.stringify(nextState));
          } catch {}
          return nextState;
        });
      } catch (e) {
        console.warn("Hydration failed:", e);
      }
    }

    hydrate();
    return () => {
      cancelled = true;
    };
  }, [backendLive, workspaceKey, userProfile]);

  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 4000);
    return () => clearTimeout(timer);
  }, [notice]);

  function go(...parts) {
    window.location.hash = parts.join("/");
    setRoute(parts);
    setMobileOpen(false);
    window.scrollTo(0, 0);
  }

  function changeRole(value) {
    try {
      if (value && typeof value === "object" && value.role) {
        // Real login: value is a user profile object from backend
        const isMgr = value.role === "manager" || value.role === "reviewer" || value.role === "admin";
        const uiRole = isMgr ? "manager" : "writer";
        const userId = value.id;
        const key = userId ? `${demoWorkspaceKey}.${userId}` : demoWorkspaceKey;
        setWorkspaceKey(key);
        sessionStorage.setItem(roleKey, uiRole);
        if (userId) sessionStorage.setItem(accountKey, userId);
        else sessionStorage.removeItem(accountKey);
        // Start with empty workspace — hydrateFromDB() will populate from DB
        setData({ drafts: [], sources: [], events: [], alerts: [] });
        setUserProfile(value);
        setBackendLive(true);
        setRole(uiRole);
        // Kick off DB hydration (async, non-blocking)
        setTimeout(hydrateFromDB, 50);
      } else if (value) {
        // Legacy fallback: value is a role string
        sessionStorage.setItem(roleKey, value);
        setRole(value);
      } else {
        // Sign out — clear all state
        sessionStorage.removeItem(roleKey);
        sessionStorage.removeItem(accountKey);
        clearBackendToken();
        setUserProfile(null);
        setWorkspaceKey(demoWorkspaceKey);
        setData({ drafts: [], sources: [], events: [], alerts: [] });
        setRole(null);
      }
    } catch {
      setData({ drafts: [], sources: [], events: [], alerts: [] });
      setStorageWarning(true);
    }
    setAiReviewing(false);
    go("home");
  }

  // ---------------------------------------------------------------------------
  // Hydrate workspace drafts from the backend DB (company-scoped via JWT)
  // ---------------------------------------------------------------------------
  async function hydrateFromDB() {
    const token = getBackendToken();
    if (!token) return;
    try {
      const remoteDrafts = await fetchBackendDrafts();
      if (!Array.isArray(remoteDrafts)) return;
      const mapped = remoteDrafts.map(mapBackendDraftToFrontend);
      setData((prev) => {
        if (!prev) return prev;
        // Merge: keep any purely-local drafts that have no backendId yet
        const remoteIds = new Set(mapped.map((d) => d.id));
        const localOnly = (prev.drafts || []).filter(
          (d) => !d.backendId && !remoteIds.has(d.id)
        );
        const merged = [...mapped, ...localOnly];
        const next = { ...prev, drafts: merged };
        try {
          const uid = sessionStorage.getItem(accountKey);
          const wsKey = uid ? `${demoWorkspaceKey}.${uid}` : demoWorkspaceKey;
          localStorage.setItem(wsKey, JSON.stringify(next));
        } catch {}
        return next;
      });
    } catch (err) {
      console.warn("hydrateFromDB failed:", err);
    }
  }

  async function enrichWithLiveAI(savedDraft) {
    const token = getBackendToken();
    if (!backendLive || !token) return;
    setAiReviewing(true);
    try {
      const remote = await runBackendReview(savedDraft);
      // If user signed out or token changed while we were waiting, discard
      if (getBackendToken() !== token) return;
      setData((prev) => {
        if (!prev) return prev;
        const nextDrafts = prev.drafts.map((item) => {
          if (item.id !== savedDraft.id) return item;
          const existingKeys = new Set(
            item.findings.map((f) => `${f.original.toLowerCase()}::${f.source?.id}`)
          );
          const extraFindings = remote.findings.filter(
            (f) =>
              f.original &&
              !existingKeys.has(`${f.original.toLowerCase()}::${f.source?.id}`)
          );
          // If local checks found nothing, use backend findings directly (no merge needed)
          const mergedFindings =
            item.findings.length === 0
              ? remote.findings
              : [...item.findings, ...extraFindings];

          const existingClaimTexts = new Set(
            item.claims.map((c) => c.text.toLowerCase())
          );
          const extraClaims = remote.claims.filter(
            (c) => c.text && !existingClaimTexts.has(c.text.toLowerCase())
          );
          const mergedClaims = [...item.claims, ...extraClaims];

          const hasBlocker = mergedFindings.some(
            (f) => f.severity === "Blocker" && f.decision === "open"
          );
          const hasWarning = mergedFindings.some(
            (f) => f.severity === "Warning" && f.decision === "open"
          );
          const nextRisk = hasBlocker
            ? "High"
            : hasWarning && item.risk === "Low"
            ? "Medium"
            : item.risk;

          return {
            ...item,
            backendId: remote.backendId,
            findings: mergedFindings,
            claims: mergedClaims,
            risk: nextRisk,
          };
        });
        const nextState = { ...prev, drafts: nextDrafts };
        try {
          localStorage.setItem(workspaceKey, JSON.stringify(nextState));
        } catch {}
        return nextState;
      });
    } catch (err) {
      console.warn("Live backend review skipped:", err);
    } finally {
      if (getBackendToken() === token) setAiReviewing(false);
    }
  }
  function commit(next, message) {
    setData(next);
    try {
      localStorage.setItem(workspaceKey, JSON.stringify(next));
    } catch {
      setStorageWarning(true);
    }
    if (message) setNotice(message);
  }
  function addEvent(workspace, action, detail, fields = {}) {
    return {
      ...workspace,
      events: [
        {
          id: crypto.randomUUID(),
          actor: userProfile?.full_name || roles[role],
          action,
          detail,
          date: stamp(),
          ...fields,
        },
        ...workspace.events,
      ],
    };
  }
  function saveDraft(draft, action, message, metadata) {
    const updated = { ...draft, updated: stamp() };
    const exists = data.drafts.some((item) => item.id === draft.id);
    const drafts = exists
      ? data.drafts.map((item) => (item.id === draft.id ? updated : item))
      : [updated, ...data.drafts];
    const next = { ...data, drafts };
    commit(
      action
        ? addEvent(next, action, draft.title, {
            draftId: draft.id,
            ...metadata,
          })
        : next,
      message
    );
    return updated;
  }
  function runChecks(
    draft,
    note = "Ran content checks",
    previousFindings = draft.findings
  ) {
    const checked = reviewDraft(draft, data.sources);
    // Retain decisions only when the cited version and original excerpt still match.
    const findings = checked.findings.map((finding) => {
      const previous = previousFindings.find(
        (item) =>
          item.id === finding.id &&
          item.original === finding.original &&
          item.source.version === finding.source.version &&
          item.decision === "dismissed"
      );
      return previous
        ? { ...finding, decision: previous.decision, note: previous.note }
        : finding;
    });
    const next = {
      ...draft,
      ...checked,
      findings,
      checked: true,
      version: draft.version + 1,
      legal: "",
    };
    next.versions = [...draft.versions, versionOf(next, note)];
    return next;
  }
  function bulkAddSources(newEntries, filename) {
    if (!newEntries || !newEntries.length) return;
    const nextSources = [...newEntries, ...data.sources];
    commit(
      addEvent(
        { ...data, sources: nextSources },
        "Imported policy rules",
        filename ? `from ${filename}` : `${newEntries.length} items`,
        { count: newEntries.length, filename }
      ),
      `Imported ${newEntries.length} items from ${filename || "document"}`
    );
  }

  function saveSource(values, existing) {
    const entry = {
      ...values,
      id:
        existing?.id || `SRC-${crypto.randomUUID().slice(0, 8).toUpperCase()}`,
      version: (existing?.version || 0) + 1,
    };
    const sourceList = existing
      ? data.sources.map((source) => (source.id === entry.id ? entry : source))
      : [entry, ...data.sources];
    let next = { ...data, sources: sourceList };
    if (existing?.type === "Approved facts") {
      const affected = data.drafts.filter((draft) =>
        hasSource(draft, existing.id)
      );
      if (affected.length) {
        const ids = new Set(affected.map((draft) => draft.id));
        const alert = {
          id: crypto.randomUUID(),
          source: entry,
          previous: existing,
          date: stamp(),
          resolved: false,
          affected: affected.map(({ id, title, status }) => ({
            id,
            title,
            status,
          })),
        };
        next = {
          ...next,
          alerts: [alert, ...data.alerts],
          drafts: data.drafts.map((draft) =>
            ids.has(draft.id) && draft.status !== "published"
              ? {
                  ...draft,
                  status: "recheck",
                  checked: false,
                  legal: "",
                  updated: stamp(),
                }
              : draft
          ),
        };
      }
    }
    commit(
      addEvent(
        next,
        existing ? "Updated source" : "Added source",
        `${entry.title} · v${entry.version}`,
        { sourceId: entry.id }
      ),
      `${sourceLabel(entry)} saved`
    );
  }
  function approve(draft, override) {
    if (
      draft.status !== "review" ||
      !draft.checked ||
      (blockers(draft).length && !override) ||
      (draft.risk === "High" && !draft.legal)
    )
      return;
    const receipt = {
      version: draft.version,
      claims: draft.claims,
      date: stamp(),
      approver: userProfile?.full_name || roles[role],
      legal: draft.legal,
      override,
    };
    const pastReceipts = draft.receipt
      ? [draft.receipt, ...(draft.pastReceipts || [])]
      : [];
    saveDraft(
      { ...draft, status: "approved", receipt, pastReceipts },
      override ? "Approved with override" : "Approved draft",
      "Approved and Claim Receipt recorded",
      {
        note: override,
        sources: evidenceOf(draft),
        overrideSources: blockers(draft).map((item) => item.source.id),
      }
    );
    syncBackendDecision(draft.backendId, "approved", override || draft.legal);
  }

  if (!data)
    return (
      <main className="loading">
        <Wordmark />
        <p>Opening your workspace…</p>
      </main>
    );
  if (!role) return <Login onLogin={changeRole} />;

  const navigation = role === "writer" ? writerNav : managerNav;
  const [page, id] = route;
  const candidate = data.drafts.find((item) => item.id === id);
  const draft = candidate;
  const allowed = page === "draft" || navigation.some(([key]) => key === page);
  const activePage = allowed && page ? page : "home";
  const activeNav =
    activePage === "draft"
      ? role === "writer"
        ? "drafts"
        : "queue"
      : activePage;
  const startDraft = () => go("draft", "new");
  const openDraft = (value) => {
    go("draft", value);
    // If the draft exists and was loaded from DB with no text yet, hydrate it
    const existing = data.drafts.find((d) => d.id === value);
    if (existing?.backendId && !existing.text) {
      fetchBackendDraft(value)
        .then((full) => {
          if (!full) return;
          setData((prev) => {
            if (!prev) return prev;
            const updated = prev.drafts.map((d) =>
              d.id === value ? { ...d, text: full.content || "", intent: full.intent_lock || d.intent } : d
            );
            return { ...prev, drafts: updated };
          });
        })
        .catch(() => {});
    }
  };
  let content;

  switch (activePage) {
    case "draft":
      content = (
        <DraftScreen
          key={id}
          draft={draft}
          newDraft={id === "new"}
          role={role}
          aiReviewing={aiReviewing}
          onBack={() => go(activeNav)}
          events={data.events.filter((event) => event.draftId === id)}
          onApprove={approve}
          onSave={(fields, run) => {
            const base = draft || makeDraft({});
            let next = { ...base, ...fields, checked: false };
            if (run) next = runChecks(next);
            else {
              next = {
                ...next,
                findings: [],
                claims: [],
                risk: "Low",
                legal: "",
                version: base.version + 1,
              };
              next.versions = [
                ...base.versions,
                versionOf(next, "Saved draft"),
              ];
            }
            const saved = saveDraft(
              next,
              run ? "Ran checks" : "Saved draft",
              run ? "Content checks complete" : "Draft saved",
              run ? { sources: evidenceOf(next) } : undefined
            );
            if (run) {
              enrichWithLiveAI(saved);
            } else if (!saved.backendId) {
              createBackendDraft(saved).then((created) => {
                if (created?.id) {
                  setData((prev) => {
                    if (!prev) return prev;
                    return {
                      ...prev,
                      drafts: prev.drafts.map((d) =>
                        d.id === saved.id ? { ...d, backendId: created.id } : d
                      ),
                    };
                  });
                }
              }).catch(() => {});
            }
            if (!draft) openDraft(saved.id);
            return saved;
          }}
          onRecheck={(target) => {
            const checked = runChecks(target);
            const saved = saveDraft(checked, "Ran checks", "Content checks complete", {
              sources: evidenceOf(checked),
            });
            enrichWithLiveAI(saved);
          }}
          onApply={(finding, replacement) => {
            if (
              draft.text.slice(
                finding.start,
                finding.start + finding.original.length
              ) !== finding.original
            )
              return;
            const text =
              draft.text.slice(0, finding.start) +
              replacement +
              draft.text.slice(finding.start + finding.original.length);

            // Run local checks on the new text
            const checked = runChecks({ ...draft, text }, "Edited and re-checked");

            // Carry forward all OTHER backend findings whose flagged text
            // still exists in the updated content — only drop the one just fixed
            const survivingFindings = draft.findings.filter(
              (f) => f.id !== finding.id && text.includes(f.original)
            );
            const localIds = new Set(checked.findings.map((f) => f.id));
            const mergedFindings = [
              ...checked.findings,
              ...survivingFindings.filter((f) => !localIds.has(f.id)),
            ];

            const saved = saveDraft(
              { ...checked, findings: mergedFindings },
              "Applied correction",
              "Correction applied and draft re-checked",
              { sourceId: finding.source.id, sources: [finding.source] }
            );
            // Re-run backend check on the corrected text in background
            enrichWithLiveAI(saved);
          }}
          onDismiss={(finding, note) =>
            saveDraft(
              {
                ...draft,
                findings: draft.findings.map((item) =>
                  item.id === finding.id
                    ? { ...item, decision: "dismissed", note }
                    : item
                ),
              },
              "Dismissed finding",
              "Dismissal recorded",
              { sourceId: finding.source.id, sources: [finding.source], note }
            )
          }
          onSubmit={async (note) => {
            let backendId = draft.backendId;
            if (!backendId) {
              const created = await createBackendDraft(draft);
              if (created?.id) {
                backendId = created.id;
              }
            }
            saveDraft(
              { ...draft, backendId, status: "review", submissionNote: note, legal: "" },
              "Requested review",
              "Draft sent to the manager",
              { note }
            );
            if (backendId) {
              requestBackendHumanReview(backendId);
            }
          }}
          onComment={(note, quote, changes) => {
            const comments = [
              ...draft.comments,
              { author: userProfile?.full_name || roles[role], text: note, quote, date: stamp() },
            ];
            saveDraft(
              {
                ...draft,
                comments,
                ...(changes ? { status: "changes", legal: "" } : {}),
              },
              changes ? "Requested changes" : "Added comment",
              changes ? "Changes requested" : "Comment added",
              { note }
            );
          }}
          onLegal={(reference) =>
            saveDraft(
              { ...draft, legal: reference },
              "Recorded legal sign-off",
              "Legal sign-off recorded",
              { note: reference }
            )
          }
          onPublish={(url) =>
            saveDraft(
              { ...draft, status: "published", url },
              "Marked published",
              "Publication recorded",
              { note: url }
            )
          }
        />
      );
      break;
    case "drafts":
    case "queue":
      content = (
        <DraftList
          drafts={data.drafts}
          role={role}
          onOpen={openDraft}
          onNew={startDraft}
        />
      );
      break;
    case "library":
      content = (
        <Library
          sources={data.sources}
          role={role}
          onSave={saveSource}
          onBulkImport={bulkAddSources}
        />
      );
      break;
    case "insights":
      content = (
        <Insights
          data={data}
          onAlerts={() => go("alerts")}
          onLibrary={() => go("library")}
        />
      );
      break;
    case "alerts":
      content = (
        <Alerts
          alerts={data.alerts}
          onOpen={openDraft}
          onResolve={(alert) => {
            const alerts = data.alerts.map((item) =>
              item.id === alert.id ? { ...item, resolved: true } : item
            );
            commit(
              addEvent(
                { ...data, alerts },
                "Acknowledged fact change",
                alert.source.title,
                { sourceId: alert.source.id }
              ),
              "Alert acknowledged"
            );
          }}
        />
      );
      break;
    case "audit":
      content = <Audit events={data.events} onOpen={openDraft} />;
      break;
    default:
      content = (
        <Dashboard
          data={data}
          role={role}
          onOpen={openDraft}
          onNew={startDraft}
          onList={() =>
            go(activeNav === "home" && role === "manager" ? "queue" : "drafts")
          }
        />
      );
  }

  /* Split manager nav: first 4 items under WORKSPACE, last 2 (alerts, audit) under TOOLS */
  const mainNav = role === "manager" ? navigation.slice(0, 4) : navigation;
  const toolsNav = role === "manager" ? navigation.slice(4) : [];

  /* Resolve current page label for the top bar breadcrumb */
  const currentPageLabel = navigation.find(([key]) => key === activeNav)?.[1] || "Home";

  return (
    <div className={`app-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
      <a
        className="skip-link"
        href="#main"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("main").focus();
        }}
      >
        Skip to content
      </a>
      <div className="mobile-bar">
        <Wordmark />
        <Button
          variant="ghost"
          icon={PanelLeft}
          aria-expanded={mobileOpen}
          aria-controls="sidebar"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          Menu
        </Button>
      </div>
      <aside
        id="sidebar"
        className={`sidebar ${sidebarCollapsed ? "is-collapsed" : ""} ${mobileOpen ? "sidebar-open" : ""}`}
      >
        {/* ── Sidebar Top Header & Morph Toggle Button ── */}
        <div className="sidebar-header">
          <a href="#home" className="sidebar-logo" onClick={() => go("home")}>
            <Wordmark collapsed={sidebarCollapsed} />
          </a>
          <button
            type="button"
            className="sidebar-toggle-btn"
            onClick={toggleSidebar}
            title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {sidebarCollapsed ? (
              <ChevronRight size={16} strokeWidth={2.2} />
            ) : (
              <ChevronLeft size={16} strokeWidth={2.2} />
            )}
          </button>
        </div>

        {/* ── Workspace Pill ── */}
        <div
          className="workspace-label"
          title={userProfile?.organisation_name || "Studio North"}
        >
          <span className="workspace-avatar">
            {userProfile?.organisation_name
              ? userProfile.organisation_name.slice(0, 2).toUpperCase()
              : "SN"}
          </span>
          <span className="workspace-label-text">
            <strong>{userProfile?.organisation_name || "Studio North"}</strong>
            <small>Brand workspace</small>
          </span>
        </div>

        {/* ── Main Workspace Navigation ── */}
        <p className="nav-label">WORKSPACE</p>
        <div className="sidebar-divider" />
        <nav className="sidebar-links" aria-label="Main navigation">
          {mainNav.map(([key, label, Icon]) => (
            <a
              href={`#${key}`}
              key={key}
              aria-current={activeNav === key ? "page" : undefined}
              className={activeNav === key ? "active" : ""}
              onClick={() => go(key)}
            >
              <Icon size={18} strokeWidth={1.8} />
              <span className="sidebar-nav-text">{label}</span>
              {sidebarCollapsed && (
                <span className="sidebar-tooltip">{label}</span>
              )}
            </a>
          ))}
        </nav>

        {/* ── Tools Navigation ── */}
        {toolsNav.length > 0 && (
          <>
            <div style={{ height: 16 }} />
            <p className="nav-label">TOOLS</p>
            <div className="sidebar-divider" />
            <nav className="sidebar-links" aria-label="Tools navigation">
              {toolsNav.map(([key, label, Icon]) => (
                <a
                  href={`#${key}`}
                  key={key}
                  aria-current={activeNav === key ? "page" : undefined}
                  className={activeNav === key ? "active" : ""}
                  onClick={() => go(key)}
                >
                  <Icon size={18} strokeWidth={1.8} />
                  <span className="sidebar-nav-text">{label}</span>
                  {sidebarCollapsed && (
                    <span className="sidebar-tooltip">{label}</span>
                  )}
                  {key === "alerts" &&
                    data.alerts.some((alert) => !alert.resolved) && (
                      <span className="nav-dot" />
                    )}
                </a>
              ))}
            </nav>
          </>
        )}

        {/* ── Sidebar Footer / User Profile ── */}
        <div className="sidebar-footer">
          <div style={{ display: "flex", gap: 9, alignItems: "center" }}>
            <span
              className="profile-initial"
              title={userProfile?.full_name || roles[role]}
            >
              {userProfile?.full_name
                ? userProfile.full_name.slice(0, 2).toUpperCase()
                : role === "writer" ? "CW" : "M"}
            </span>
            <div className="sidebar-footer-info">
              <strong>{userProfile?.full_name || roles[role]}</strong>
              <small>
                {userProfile
                  ? (userProfile.role.charAt(0).toUpperCase() + userProfile.role.slice(1)) +
                    (backendLive ? " · Live" : "")
                  : backendLive ? "Connected" : "Offline"}
              </small>
            </div>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label="Sign out"
            title="Sign out"
            style={{ width: 32, height: 32, borderRadius: 8 }}
            onClick={() => changeRole(null)}
          >
            <LogOut size={16} strokeWidth={1.8} />
          </button>
        </div>
      </aside>
      <main id="main" tabIndex={-1} className="main">
        {/* ── Apple/iOS-style Top Control Bar ── */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "14px 32px",
            background: "#ffffff",
            borderBottom: "1px solid rgba(0, 0, 0, 0.06)",
            position: "sticky",
            top: 0,
            zIndex: 10,
            backdropFilter: "blur(12px)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <span style={{ fontSize: "15px", fontWeight: 700, color: "#1e293b", letterSpacing: "-0.01em" }}>
              {currentPageLabel}
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            {/* Profile Avatar & Company Badge */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                background: "#f8fafc",
                padding: "4px 12px 4px 6px",
                borderRadius: "100px",
                border: "1px solid #e2e8f0",
                fontSize: "12px",
              }}
            >
              <span
                style={{
                  width: 22,
                  height: 22,
                  borderRadius: "50%",
                  background: "#0d9488",
                  color: "white",
                  fontSize: "10px",
                  fontWeight: 700,
                  display: "grid",
                  placeItems: "center",
                }}
              >
                {userProfile?.full_name ? userProfile.full_name.charAt(0).toUpperCase() : "U"}
              </span>
              <span style={{ fontWeight: 600, color: "#334155" }}>
                {userProfile?.organisation_name || "Studio North"}
              </span>
            </div>
          </div>
        </div>
        <div className="page">
          {storageWarning && (
            <p className="callout">
              Browser storage is unavailable. Changes last for this session.
            </p>
          )}
          {content}
        </div>
      </main>
      {notice && <Toast>{notice}</Toast>}
    </div>
  );
}
