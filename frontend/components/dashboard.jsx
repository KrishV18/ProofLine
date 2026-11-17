"use client";

import { useState } from "react";
import {
  ArrowRight,
  Bell,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronDown,
  ClipboardCheck,
  Clock3,
  FileCheck,
  FileText,
  HelpCircle,
  MessageSquare,
  PenLine,
  Plus,
  Search,
  ShieldAlert,
  ShieldCheck,
  UploadCloud,
} from "lucide-react";
import { formatDate } from "../lib/workflow.mjs";
import { Badge, Button, Empty, Header, Risk, Status, Tabs } from "./ui";

/* ── DraftTable ──────────────────────────────────────────────────── */

function DraftTable({ drafts, role, onOpen }) {
  if (!drafts.length)
    return (
      <Empty
        title="No matching drafts"
        detail="Try a different filter or click 'New draft' to get started."
      />
    );
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Draft</th>
            <th>Status</th>
            {role === "manager" && <th>Risk</th>}
            <th>Last updated</th>
            <th>
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {drafts.map((draft) => (
            <tr key={draft.id}>
              <td>
                <a
                  className="document-link"
                  href={`#draft/${draft.id}`}
                  onClick={(event) => {
                    event.preventDefault();
                    onOpen(draft.id);
                  }}
                >
                  <span className="file-icon">
                    <FileText size={18} strokeWidth={1.8} />
                  </span>
                  <span>
                    <strong>{draft.title || "Untitled draft"}</strong>
                    <small>
                      {draft.channel || "Email"} · v{draft.version || 1}
                    </small>
                  </span>
                </a>
              </td>
              <td>
                <Status value={draft.status} />
                {role === "manager" &&
                  draft.status === "review" &&
                  draft.risk === "High" && (
                    <small className="table-subtle">
                      {draft.legal
                        ? "Legal sign-off recorded"
                        : "Legal sign-off required"}
                    </small>
                  )}
              </td>
              {role === "manager" && (
                <td>
                  <Risk value={draft.risk} />
                </td>
              )}
              <td className="muted">{formatDate(draft.updated)}</td>
              <td>
                <button
                  className="icon-button row-arrow"
                  type="button"
                  aria-label={`Open ${draft.title}`}
                  onClick={() => onOpen(draft.id)}
                >
                  <ArrowRight size={17} strokeWidth={2} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ── Dashboard ───────────────────────────────────────────────────── */

export function Dashboard({ data, role, onOpen, onNew, onList }) {
  const [tableFilter, setTableFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const manager = role === "manager";
  const drafts = data.drafts.filter(
    (draft) => !manager || draft.status !== "draft"
  );

  const count = (...statuses) =>
    drafts.filter((draft) => statuses.includes(draft.status)).length;

  const inProgressCount = count("draft", "changes", "recheck");
  const inReviewCount = count("review");
  const approvedCount = count("approved", "published");

  // Filter drafts for the table
  const filteredDrafts = drafts.filter((draft) => {
    const matchesFilter =
      tableFilter === "all" ||
      draft.status === tableFilter ||
      (tableFilter === "approved" && draft.status === "published");
    const matchesSearch =
      !searchQuery.trim() ||
      `${draft.title} ${draft.channel}`
        .toLowerCase()
        .includes(searchQuery.trim().toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const recent = [...filteredDrafts].sort((a, b) =>
    b.updated.localeCompare(a.updated)
  );

  // Find latest manager feedback comment
  const feedbackDraft =
    drafts.find(
      (draft) => draft.status === "changes" && draft.comments?.length
    ) || drafts.find((draft) => draft.comments?.length);

  const latestComment = feedbackDraft?.comments?.at(-1);
  const feedbackText =
    latestComment?.text ||
    "Please update the price from ₹999 to ₹1,299 using Pricing Sheet · v3.";

  // Activity events from data.events
  const events = data.events && data.events.length > 0 ? data.events.slice(0, 5) : [
    {
      id: "ev-1",
      action: "Marked published",
      detail: "Starter Plan — Clean Review Test",
      date: new Date().toISOString(),
      draftId: drafts[0]?.id,
    },
    {
      id: "ev-2",
      action: "Approved draft",
      detail: "Starter Plan — Clean Review Test",
      date: new Date(Date.now() - 3600000).toISOString(),
      draftId: drafts[0]?.id,
    },
    {
      id: "ev-3",
      action: "Recorded legal sign-off",
      detail: "Starter Plan — Clean Review Test",
      date: new Date(Date.now() - 7200000).toISOString(),
      draftId: drafts[0]?.id,
    },
  ];

  function getEventIcon(action = "") {
    const lower = action.toLowerCase();
    if (lower.includes("publish")) return <CheckCircle2 size={15} strokeWidth={2} style={{ color: "#16a34a" }} />;
    if (lower.includes("approve")) return <ShieldCheck size={15} strokeWidth={2} style={{ color: "#0d9488" }} />;
    if (lower.includes("legal")) return <FileCheck size={15} strokeWidth={2} style={{ color: "#0284c7" }} />;
    if (lower.includes("changes")) return <MessageSquare size={15} strokeWidth={2} style={{ color: "#e11d48" }} />;
    return <Clock3 size={15} strokeWidth={2} style={{ color: "#64748b" }} />;
  }

  return (
    <>
      {/* ── Top Bar: Search drafts + New draft button ── */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 16,
          marginBottom: 20,
          flexWrap: "wrap",
        }}
      >
        <div style={{ position: "relative", width: "min(100%, 360px)" }}>
          <Search
            size={16}
            strokeWidth={2}
            style={{
              position: "absolute",
              left: 14,
              top: "50%",
              transform: "translateY(-50%)",
              color: "#94a3b8",
              pointerEvents: "none",
            }}
          />
          <input
            type="text"
            placeholder="Search drafts…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              paddingLeft: 38,
              height: 42,
              borderRadius: 12,
              background: "#ffffff",
              border: "1px solid rgba(0, 0, 0, 0.08)",
              fontSize: 13,
            }}
          />
        </div>

        <Button
          icon={Plus}
          onClick={onNew}
          style={{
            borderRadius: 10,
            padding: "9px 18px",
            fontSize: 13,
            fontWeight: 600,
            boxShadow: "0 2px 8px rgba(13, 148, 136, 0.2)",
          }}
        >
          New draft
        </Button>
      </div>

      {/* ── Page Header ── */}
      <div style={{ marginBottom: 28 }}>
        <h1
          style={{
            fontSize: "32px",
            fontWeight: 800,
            color: "#0f172a",
            letterSpacing: "-0.035em",
            margin: "0 0 6px",
          }}
        >
          {manager ? "Workspace overview" : "My workspace"}
        </h1>
        <p style={{ color: "#64748b", fontSize: "14px", margin: 0 }}>
          {manager
            ? "Review content, track risk, and keep your brand sources current."
            : "Draft, check, and send your content for review."}
        </p>
      </div>

      {/* ── 2-Column Responsive Dashboard Layout ── */}
      <div className="dashboard-grid">
        {/* ── Left Column: Metrics & Draft Table ── */}
        <div className="dashboard-main">
          {/* 3 Metric Cards */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
              gap: 14,
            }}
          >
            {/* Metric 1: In progress */}
            <div
              style={{
                background: "#f0fdf4",
                border: "1px solid #dcfce7",
                borderRadius: 18,
                padding: "18px 20px",
                display: "flex",
                flexDirection: "column",
                gap: 12,
                boxShadow: "0 1px 4px rgba(0, 0, 0, 0.02)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span style={{ fontSize: 13, fontWeight: 600, color: "#166534" }}>
                  In progress
                </span>
                <span
                  style={{
                    width: 30,
                    height: 30,
                    borderRadius: 8,
                    background: "#dcfce7",
                    color: "#166534",
                    display: "grid",
                    placeItems: "center",
                  }}
                >
                  <PenLine size={16} strokeWidth={2} />
                </span>
              </div>
              <strong
                style={{
                  fontSize: 32,
                  fontWeight: 800,
                  color: "#14532d",
                  lineHeight: 1,
                  letterSpacing: "-0.03em",
                }}
              >
                {inProgressCount}
              </strong>
            </div>

            {/* Metric 2: In review */}
            <div
              style={{
                background: "#fef3c7",
                border: "1px solid #fde68a",
                borderRadius: 18,
                padding: "18px 20px",
                display: "flex",
                flexDirection: "column",
                gap: 12,
                boxShadow: "0 1px 4px rgba(0, 0, 0, 0.02)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span style={{ fontSize: 13, fontWeight: 600, color: "#92400e" }}>
                  In review
                </span>
                <span
                  style={{
                    width: 30,
                    height: 30,
                    borderRadius: 8,
                    background: "#fde68a",
                    color: "#92400e",
                    display: "grid",
                    placeItems: "center",
                  }}
                >
                  <Clock3 size={16} strokeWidth={2} />
                </span>
              </div>
              <strong
                style={{
                  fontSize: 32,
                  fontWeight: 800,
                  color: "#78350f",
                  lineHeight: 1,
                  letterSpacing: "-0.03em",
                }}
              >
                {inReviewCount}
              </strong>
            </div>

            {/* Metric 3: Approved */}
            <div
              style={{
                background: "#e0f2fe",
                border: "1px solid #bae6fd",
                borderRadius: 18,
                padding: "18px 20px",
                display: "flex",
                flexDirection: "column",
                gap: 12,
                boxShadow: "0 1px 4px rgba(0, 0, 0, 0.02)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span style={{ fontSize: 13, fontWeight: 600, color: "#0369a1" }}>
                  Approved
                </span>
                <span
                  style={{
                    width: 30,
                    height: 30,
                    borderRadius: 8,
                    background: "#bae6fd",
                    color: "#0369a1",
                    display: "grid",
                    placeItems: "center",
                  }}
                >
                  <CheckCircle2 size={16} strokeWidth={2} />
                </span>
              </div>
              <strong
                style={{
                  fontSize: 32,
                  fontWeight: 800,
                  color: "#0c4a6e",
                  lineHeight: 1,
                  letterSpacing: "-0.03em",
                }}
              >
                {approvedCount}
              </strong>
            </div>
          </div>

          {/* Section: My drafts */}
          <section
            className="card section-card"
            style={{ borderRadius: 20, overflow: "hidden" }}
          >
            <div
              className="section-heading"
              style={{
                padding: "20px 24px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div>
                <h2 style={{ fontSize: "20px", fontWeight: 700, margin: 0 }}>
                  {manager ? "Recent submissions" : "My drafts"}
                </h2>
              </div>

              {/* Status Filter Dropdown & View All Link */}
              <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                <div style={{ position: "relative" }}>
                  <select
                    value={tableFilter}
                    onChange={(e) => setTableFilter(e.target.value)}
                    aria-label="Filter status"
                    style={{
                      height: 36,
                      borderRadius: 10,
                      padding: "6px 30px 6px 12px",
                      fontSize: 12,
                      fontWeight: 600,
                      color: "#475569",
                      background: "#f8fafc",
                      border: "1px solid #e2e8f0",
                      appearance: "none",
                      cursor: "pointer",
                    }}
                  >
                    <option value="all">All statuses</option>
                    <option value="draft">In progress</option>
                    <option value="review">In review</option>
                    <option value="approved">Approved</option>
                    <option value="changes">Changes requested</option>
                  </select>
                  <ChevronDown
                    size={14}
                    strokeWidth={2}
                    style={{
                      position: "absolute",
                      right: 10,
                      top: "50%",
                      transform: "translateY(-50%)",
                      pointerEvents: "none",
                      color: "#94a3b8",
                    }}
                  />
                </div>

                <button
                  type="button"
                  onClick={onList}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                    background: "none",
                    border: "none",
                    color: "var(--teal)",
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: "pointer",
                    padding: 0,
                  }}
                >
                  View all <ArrowRight size={14} strokeWidth={2} />
                </button>
              </div>
            </div>

            <DraftTable
              drafts={recent.slice(0, 5)}
              role={role}
              onOpen={onOpen}
            />
          </section>
        </div>

        {/* ── Right Column: Manager Feedback + Recent Activity ── */}
        <div className="dashboard-side">
          {/* Card 1: Manager Feedback */}
          <div className="feedback-card">
            <div className="feedback-header">
              <MessageSquare size={18} strokeWidth={2} />
              <span>Manager feedback</span>
            </div>
            <p className="feedback-text">{feedbackText}</p>
            <div>
              <button
                type="button"
                className="feedback-action"
                onClick={() => {
                  if (feedbackDraft) onOpen(feedbackDraft.id);
                  else if (recent[0]) onOpen(recent[0].id);
                }}
              >
                Open draft <ArrowRight size={14} strokeWidth={2} />
              </button>
            </div>
          </div>

          {/* Card 2: Recent Activity */}
          <div className="activity-card">
            <h3 className="activity-title">Recent activity</h3>
            <div className="activity-list">
              {events.map((event) => (
                <div
                  key={event.id}
                  className="activity-item"
                  onClick={() => {
                    if (event.draftId) onOpen(event.draftId);
                  }}
                >
                  <div className="activity-item-icon">
                    {getEventIcon(event.action)}
                  </div>
                  <div className="activity-item-content">
                    <p className="activity-item-action">{event.action}</p>
                    <p className="activity-item-detail">{event.detail}</p>
                    <span className="activity-item-time">
                      {formatDate(event.date, true)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

/* ── DraftList ───────────────────────────────────────────────────── */

export function DraftList({ drafts, role, onOpen, onNew }) {
  const manager = role === "manager";
  const [filter, setFilter] = useState(manager ? "review" : "all");
  const [query, setQuery] = useState("");
  const [risk, setRisk] = useState("");
  const pool = drafts.filter((draft) => !manager || draft.status !== "draft");

  const filters = manager
    ? [
        ["review", "Awaiting review"],
        ["changes", "Changes requested"],
        ["approved", "Approved"],
        ["recheck", "Needs re-check"],
        ["all", "All"],
      ]
    : [
        ["all", "All drafts"],
        ["draft", "In progress"],
        ["review", "In review"],
        ["changes", "Changes requested"],
        ["approved", "Approved"],
        ["recheck", "Needs re-check"],
      ];

  const matches = (draft, key) =>
    key === "all" ||
    draft.status === key ||
    (key === "approved" && draft.status === "published");

  const visible = pool
    .filter(
      (draft) =>
        matches(draft, filter) &&
        (!risk || draft.risk === risk) &&
        `${draft.title} ${draft.channel}`
          .toLowerCase()
          .includes(query.trim().toLowerCase())
    )
    .sort((a, b) => b.updated.localeCompare(a.updated));

  return (
    <>
      <Header
        eyebrow={manager ? "APPROVAL WORKFLOW" : "WRITER WORKSPACE"}
        title={manager ? "Review queue" : "My drafts"}
        description={
          manager
            ? "Inspect evidence, send feedback, and make approval decisions."
            : "Find and manage drafts at every stage."
        }
        actions={
          !manager && (
            <Button icon={Plus} onClick={onNew}>
              New draft
            </Button>
          )
        }
      />

      <section
        className="card section-card"
        style={{ borderRadius: "20px", overflow: "hidden" }}
      >
        <div className="toolbar">
          <Tabs
            label="Draft status"
            items={filters.map(([key, name]) => ({
              key,
              name: (
                <>
                  {name}{" "}
                  <Badge>
                    {pool.filter((draft) => matches(draft, key)).length}
                  </Badge>
                </>
              ),
            }))}
            value={filter}
            onChange={setFilter}
          />
        </div>

        <div className="toolbar search-toolbar">
          <label className="search">
            <Search size={17} strokeWidth={2} />
            <input
              aria-label="Search drafts"
              placeholder="Search drafts…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          {manager && (
            <select
              aria-label="Risk level"
              value={risk}
              onChange={(event) => setRisk(event.target.value)}
              style={{ borderRadius: "10px", height: "38px" }}
            >
              <option value="">All risk levels</option>
              <option>High</option>
              <option>Medium</option>
              <option>Low</option>
            </select>
          )}
        </div>

        <DraftTable drafts={visible} role={role} onOpen={onOpen} />
      </section>
    </>
  );
}
