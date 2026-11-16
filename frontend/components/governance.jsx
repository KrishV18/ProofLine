"use client";

import { useRef, useState } from "react";
import {
  ArrowRight,
  Bell,
  BookOpen,
  Check,
  FileText,
  History,
  Loader2,
  Plus,
  Search,
  Sparkles,
  TriangleAlert,
  UploadCloud,
} from "lucide-react";
import {
  formatDate,
  isExpired,
  libraryTabs,
  money,
  sourceLabel,
  statuses,
} from "../lib/workflow.mjs";
import { extractPolicyDocument, bulkImportSources } from "../lib/backend";
import { Badge, Button, Empty, Field, Header, Modal, Tabs } from "./ui";

const singular = {
  Guidelines: "guideline",
  "Approved facts": "fact",
  Terminology: "term",
  Assets: "asset",
};
const types = {
  claim: "Promotional claims",
  tone: "Tone",
  alt: "Missing alt text",
  disclaimer: "Required disclaimer",
  contrast: "Text contrast",
};

function SourceEditor({ source, type, onSave, onClose }) {
  const [fields, setFields] = useState(
    source || {
      type,
      title: "",
      source: "",
      owner: "",
      text: "",
      expires: "",
      keyword: "",
      value: "",
      check: "",
    }
  );
  const update = (key, value) =>
    setFields((previous) => ({ ...previous, [key]: value }));
  function submit(event) {
    event.preventDefault();
    if (
      [fields.title, fields.source, fields.owner, fields.text].some(
        (value) => !value.trim()
      )
    )
      return;
    onSave(
      Object.fromEntries(
        Object.entries(fields).map(([key, value]) => [
          key,
          typeof value === "string" ? value.trim() : value,
        ])
      ),
      source
    );
    onClose();
  }
  return (
    <Modal
      title={source ? `Update ${singular[type]}` : `Add ${singular[type]}`}
      onClose={onClose}
    >
      <form className="modal-body" onSubmit={submit}>
        {source && (
          <p className="callout compact">
            Saving creates version {source.version + 1} and preserves existing
            citations.
          </p>
        )}
        <Field label="Title">
          <input
            required
            value={fields.title}
            onChange={(event) => update("title", event.target.value)}
          />
        </Field>
        <div className="field-row">
          <Field label="Source name">
            <input
              required
              value={fields.source}
              onChange={(event) => update("source", event.target.value)}
            />
          </Field>
          <Field label="Owner">
            <input
              required
              value={fields.owner}
              onChange={(event) => update("owner", event.target.value)}
            />
          </Field>
        </div>
        <Field
          label={
            type === "Assets"
              ? "Asset description or approved URL"
              : "Approved text"
          }
        >
          <textarea
            required
            rows={3}
            value={fields.text}
            onChange={(event) => update("text", event.target.value)}
          />
        </Field>
        {type === "Approved facts" && (
          <>
            <div className="field-row">
              <Field label="Product name (optional)">
                <input
                  value={fields.keyword || ""}
                  onChange={(event) => update("keyword", event.target.value)}
                />
              </Field>
              <Field label="Price in ₹ (optional)">
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={fields.value || ""}
                  onChange={(event) => update("value", event.target.value)}
                />
              </Field>
            </div>
            <Field label="Evidence expiry date">
              <input
                required
                type="date"
                value={fields.expires || ""}
                onChange={(event) => update("expires", event.target.value)}
              />
            </Field>
          </>
        )}
        {type === "Terminology" && (
          <div className="field-row">
            <Field label="Flag this term">
              <input
                required
                value={fields.keyword || ""}
                onChange={(event) => update("keyword", event.target.value)}
              />
            </Field>
            <Field label="Preferred term">
              <input
                required
                value={fields.value || ""}
                onChange={(event) => update("value", event.target.value)}
              />
            </Field>
          </div>
        )}
        {type === "Guidelines" && (
          <Field label="Demo check">
            <select
              value={fields.check || ""}
              onChange={(event) => update("check", event.target.value)}
            >
              <option value="">Reference only</option>
              {Object.entries(types).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
        )}
        <div className="modal-actions">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit">Save {singular[type]}</Button>
        </div>
      </form>
    </Modal>
  );
}
function PolicyDocumentImporter({ onClose, onImportSuccess }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [extracted, setExtracted] = useState(null);
  const [activeTab, setActiveTab] = useState("Guidelines");
  const [selectedGuidelines, setSelectedGuidelines] = useState(new Set());
  const [selectedFacts, setSelectedFacts] = useState(new Set());
  const [selectedTerms, setSelectedTerms] = useState(new Set());
  const fileInputRef = useRef(null);

  async function handleFileSelected(selectedFile) {
    if (!selectedFile) return;
    setFile(selectedFile);
    setError("");
    setLoading(true);
    try {
      const data = await extractPolicyDocument(selectedFile);
      setExtracted(data);
      // Select all by default
      setSelectedGuidelines(new Set(data.guidelines.map((_, i) => i)));
      setSelectedFacts(new Set(data.facts.map((_, i) => i)));
      setSelectedTerms(new Set(data.terms.map((_, i) => i)));
      if (!data.guidelines.length && data.facts.length) {
        setActiveTab("Facts");
      } else if (!data.guidelines.length && !data.facts.length && data.terms.length) {
        setActiveTab("Terminology");
      }
    } catch (err) {
      setError(err.message || "Failed to parse document rules.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!extracted) return;
    const chosenGuidelines = extracted.guidelines.filter((_, i) => selectedGuidelines.has(i));
    const chosenFacts = extracted.facts.filter((_, i) => selectedFacts.has(i));
    const chosenTerms = extracted.terms.filter((_, i) => selectedTerms.has(i));

    if (!chosenGuidelines.length && !chosenFacts.length && !chosenTerms.length) {
      setError("Please select at least one item to import.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      await bulkImportSources({
        guidelines: chosenGuidelines.map((g) => ({
          rule_id: g.rule_id,
          text: g.rule_text,
          category: g.category,
        })),
        facts: chosenFacts.map((f) => ({
          fact_key: f.fact_key,
          statement: f.statement,
          value: f.value || "",
          owner: f.owner || "Policy Document",
          source: file?.name || "Document Import",
          expires_on: f.expires_on || null,
        })),
        terms: chosenTerms.map((t) => ({
          term: t.term,
          preferred: t.preferred,
          banned: t.banned,
          notes: t.notes || "",
        })),
      });

      const newLocalSources = [
        ...chosenGuidelines.map((g) => ({
          id: g.rule_id,
          type: "Guidelines",
          check: "tone",
          title: g.rule_text.slice(0, 50),
          source: file?.name || "Imported Policy",
          owner: "Brand",
          version: 1,
          text: g.rule_text,
          severity: g.severity,
        })),
        ...chosenFacts.map((f) => ({
          id: f.fact_key,
          type: "Approved facts",
          title: f.statement.slice(0, 50),
          source: file?.name || "Imported Policy",
          owner: f.owner || "Company",
          version: 1,
          value: f.value || "",
          text: f.statement,
          expires: f.expires_on || "2027-12-31",
        })),
        ...chosenTerms.map((t) => ({
          id: `TERM-${crypto.randomUUID().slice(0, 6).toUpperCase()}`,
          type: "Terminology",
          title: t.preferred ? `Use "${t.preferred}"` : t.term,
          source: file?.name || "Imported Policy",
          owner: "Brand",
          version: 1,
          keyword: t.term,
          value: t.preferred || t.term,
          text: t.notes || (t.banned ? `Do not use "${t.term}". Prefer "${t.preferred}".` : `Approved term: "${t.term}"`),
        })),
      ];

      if (onImportSuccess) {
        onImportSuccess(newLocalSources, file?.name);
      }
      onClose();
    } catch (err) {
      setError(err.message || "Failed to save imported sources.");
    } finally {
      setSaving(false);
    }
  }

  const totalSelected = selectedGuidelines.size + selectedFacts.size + selectedTerms.size;

  return (
    <Modal title="Import Policy Document" className="wide-modal" onClose={onClose}>
      <div className="importer-body">
        {!extracted && !loading && (
          <div className="upload-panel">
            <UploadCloud size={32} />
            <strong>Upload Company Guidelines Document</strong>
            <p>Upload any PDF, Word (.docx), PowerPoint (.pptx), or text file containing your company's rules, brand guidelines, facts, or terminology.</p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.pptx,.ppt,.txt,.md"
              style={{ display: "none" }}
              onChange={(e) => handleFileSelected(e.target.files?.[0])}
            />
            <Button
              type="button"
              icon={Sparkles}
              onClick={() => fileInputRef.current?.click()}
            >
              Choose document & extract rules
            </Button>
          </div>
        )}

        {loading && (
          <div className="importer-loading">
            <Loader2 size={32} className="spin" />
            <strong>AI Extraction Bot Running…</strong>
            <p className="callout compact">
              Analyzing {file?.name}: extracting actionable guidelines, verified facts, and brand terminology into structured JSON…
            </p>
          </div>
        )}

        {extracted && !loading && (
          <>
            <div className="importer-summary">
              <Sparkles size={18} />
              <span>
                <strong>{file?.name}</strong>: {extracted.summary}
              </span>
            </div>

            <div className="toolbar" style={{ marginTop: 4 }}>
              <Tabs
                items={[
                  `Guidelines (${extracted.guidelines.length})`,
                  `Facts (${extracted.facts.length})`,
                  `Terminology (${extracted.terms.length})`,
                ]}
                value={
                  activeTab === "Guidelines"
                    ? `Guidelines (${extracted.guidelines.length})`
                    : activeTab === "Facts"
                    ? `Facts (${extracted.facts.length})`
                    : `Terminology (${extracted.terms.length})`
                }
                onChange={(val) => {
                  if (val.startsWith("Guidelines")) setActiveTab("Guidelines");
                  else if (val.startsWith("Facts")) setActiveTab("Facts");
                  else setActiveTab("Terminology");
                }}
                label="Extracted tabs"
              />
            </div>

            {activeTab === "Guidelines" && (
              <div className="importer-list">
                {!extracted.guidelines.length ? (
                  <p className="callout compact">No guidelines found in this document.</p>
                ) : (
                  extracted.guidelines.map((g, idx) => {
                    const checked = selectedGuidelines.has(idx);
                    return (
                      <label key={idx} className="importer-item">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) => {
                            const next = new Set(selectedGuidelines);
                            if (e.target.checked) next.add(idx);
                            else next.delete(idx);
                            setSelectedGuidelines(next);
                          }}
                        />
                        <div className="importer-item-content">
                          <div className="importer-badges">
                            <Badge>{g.rule_id}</Badge>
                            <Badge tone="blue">{g.category}</Badge>
                            <Badge tone={g.severity === "blocker" ? "red" : g.severity === "warning" ? "amber" : "neutral"}>
                              {g.severity}
                            </Badge>
                          </div>
                          <div>{g.rule_text}</div>
                        </div>
                      </label>
                    );
                  })
                )}
              </div>
            )}

            {activeTab === "Facts" && (
              <div className="importer-list">
                {!extracted.facts.length ? (
                  <p className="callout compact">No facts found in this document.</p>
                ) : (
                  extracted.facts.map((f, idx) => {
                    const checked = selectedFacts.has(idx);
                    return (
                      <label key={idx} className="importer-item">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) => {
                            const next = new Set(selectedFacts);
                            if (e.target.checked) next.add(idx);
                            else next.delete(idx);
                            setSelectedFacts(next);
                          }}
                        />
                        <div className="importer-item-content">
                          <div className="importer-badges">
                            <Badge>{f.fact_key}</Badge>
                            {f.value && <Badge tone="green">{f.value}</Badge>}
                            {f.owner && <Badge tone="neutral">{f.owner}</Badge>}
                          </div>
                          <div>{f.statement}</div>
                          {f.expires_on && <small>Expires: {f.expires_on}</small>}
                        </div>
                      </label>
                    );
                  })
                )}
              </div>
            )}

            {activeTab === "Terminology" && (
              <div className="importer-list">
                {!extracted.terms.length ? (
                  <p className="callout compact">No terminology rules found in this document.</p>
                ) : (
                  extracted.terms.map((t, idx) => {
                    const checked = selectedTerms.has(idx);
                    return (
                      <label key={idx} className="importer-item">
                        <input
                          type="checkbox"
                          checked={checked}
                          onChange={(e) => {
                            const next = new Set(selectedTerms);
                            if (e.target.checked) next.add(idx);
                            else next.delete(idx);
                            setSelectedTerms(next);
                          }}
                        />
                        <div className="importer-item-content">
                          <div className="importer-badges">
                            <Badge tone={t.banned ? "red" : "green"}>
                              {t.banned ? "Avoid" : "Approved"}
                            </Badge>
                            <strong>"{t.term}"</strong>
                            {t.preferred && <span>→ Prefer "{t.preferred}"</span>}
                          </div>
                          {t.notes && <small>{t.notes}</small>}
                        </div>
                      </label>
                    );
                  })
                )}
              </div>
            )}
          </>
        )}

        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}

        <div className="modal-actions">
          <Button variant="secondary" onClick={onClose} disabled={saving}>
            Cancel
          </Button>
          {extracted && (
            <Button
              icon={Sparkles}
              disabled={saving || totalSelected === 0}
              onClick={handleSave}
            >
              {saving ? "Importing…" : `Import ${totalSelected} selected into Library`}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}

export function Library({ sources, role, onSave, onBulkImport }) {
  const [tab, setTab] = useState("Approved facts");
  const [query, setQuery] = useState("");
  const [detail, setDetail] = useState(null);
  const [editing, setEditing] = useState(null);
  const [importingDoc, setImportingDoc] = useState(false);
  const manager = role === "manager" || role === "reviewer" || role === "admin";
  const visible = sources.filter(
    (source) =>
      source.type === tab &&
      `${source.title} ${source.source} ${source.owner} ${source.id}`
        .toLowerCase()
        .includes(query.trim().toLowerCase())
  );
  return (
    <>
      <Header
        eyebrow="SOURCE OF TRUTH"
        title="Brand library"
        description="The approved sources behind your brand checks and editorial decisions."
        actions={
          manager && (
            <div style={{ display: "flex", gap: "8px" }}>
              <Button
                variant="secondary"
                icon={UploadCloud}
                onClick={() => setImportingDoc(true)}
              >
                Import document
              </Button>
              <Button icon={Plus} onClick={() => setEditing({})}>
                Add {singular[tab]}
              </Button>
            </div>
          )
        }
      />
      <section className="card section-card">
        <div className="toolbar">
          <Tabs
            items={libraryTabs}
            value={tab}
            onChange={(value) => {
              setTab(value);
              setQuery("");
            }}
            label="Source types"
          />
        </div>
        <div className="toolbar search-toolbar">
          <label className="search">
            <Search size={17} />
            <input
              aria-label="Search brand library"
              value={query}
              placeholder={`Search ${tab.toLowerCase()}…`}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
        </div>
        {!visible.length ? (
          <Empty
            icon={BookOpen}
            title="No matching sources"
            detail="Try another search or source type."
          />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Owner</th>
                  <th>Version</th>
                  {tab === "Approved facts" && <th>Expires</th>}
                  <th>
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {visible.map((source) => (
                  <tr key={source.id}>
                    <td>
                      <button
                        className="document-link text-button"
                        type="button"
                        onClick={() => setDetail(source)}
                      >
                        <span className="file-icon">
                          <FileText size={18} />
                        </span>
                        <span>
                          <strong>{source.title}</strong>
                          <small>
                            {source.source} · {source.id}
                          </small>
                        </span>
                      </button>
                    </td>
                    <td>{source.owner}</td>
                    <td>
                      <Badge>v{source.version}</Badge>
                    </td>
                    {tab === "Approved facts" && (
                      <td>
                        {isExpired(source) ? (
                          <Badge tone="amber">Expired</Badge>
                        ) : (
                          formatDate(source.expires)
                        )}
                      </td>
                    )}
                    <td>
                      <Button variant="ghost" onClick={() => setDetail(source)}>
                        View <ArrowRight size={15} />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {detail && (
        <Modal title={detail.title} onClose={() => setDetail(null)}>
          <div className="modal-body source-modal">
            <Badge tone="teal">{sourceLabel(detail)}</Badge>
            <p>{detail.text}</p>
            <dl>
              <div>
                <dt>Owner</dt>
                <dd>{detail.owner}</dd>
              </div>
              <div>
                <dt>Source ID</dt>
                <dd>{detail.id}</dd>
              </div>
              {detail.expires && (
                <div>
                  <dt>Expires</dt>
                  <dd>{formatDate(detail.expires)}</dd>
                </div>
              )}
            </dl>
            {manager && (
              <div className="modal-actions">
                <Button
                  onClick={() => {
                    setEditing({ source: detail });
                    setDetail(null);
                  }}
                >
                  Edit source
                </Button>
              </div>
            )}
          </div>
        </Modal>
      )}
      {editing && (
        <SourceEditor
          source={editing.source}
          type={tab}
          onSave={onSave}
          onClose={() => setEditing(null)}
        />
      )}
      {importingDoc && (
        <PolicyDocumentImporter
          onClose={() => setImportingDoc(false)}
          onImportSuccess={(newSources, filename) => {
            if (onBulkImport) {
              onBulkImport(newSources, filename);
            }
          }}
        />
      )}
    </>
  );
}
export function Insights({ data, onAlerts, onLibrary }) {
  const rules = data.sources
    .filter(
      (source) => source.type !== "Approved facts" && source.type !== "Assets"
    )
    .map((source) => ({
      ...source,
      dismissals: data.events.filter(
        (event) =>
          event.action === "Dismissed finding" && event.sourceId === source.id
      ).length,
      overrides: data.events.filter(
        (event) =>
          event.action === "Approved with override" &&
          (event.overrideSources?.includes(source.id) ??
            event.sources?.some((item) => item.id === source.id))
      ).length,
    }))
    .sort((a, b) => b.dismissals + b.overrides - (a.dismissals + a.overrides));
  const sourceCounts = new Map();
  for (const draft of data.drafts) {
    for (const finding of draft.findings) {
      const category =
        finding.source.type === "Approved facts"
          ? "Facts"
          : types[finding.source.check] || finding.source.type;
      sourceCounts.set(category, (sourceCounts.get(category) || 0) + 1);
    }
  }
  const counts = [...sourceCounts].sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...sourceCounts.values());
  const currentAlert = data.alerts.find((alert) => !alert.resolved);
  const staleFacts = data.sources.filter(
    (source) => source.type === "Approved facts" && isExpired(source)
  );
  return (
    <>
      <Header
        eyebrow="GOVERNANCE"
        title="Insights"
        description="See where drafts repeatedly run into issues and which rules reviewers override."
      />
      <div className="insights-grid">
        <div className="stack">
          <section className="card section-card">
            <div className="section-heading">
              <div>
                <h2>Guideline Health</h2>
                <p>
                  Dismissals and overrides can point to rules that need
                  clarification.
                </p>
              </div>
              <Button variant="ghost" onClick={onLibrary}>
                Brand library <ArrowRight size={15} />
              </Button>
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Rule</th>
                    <th>Dismissals</th>
                    <th>Overrides</th>
                    <th>Health</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => (
                    <tr key={rule.id}>
                      <td>
                        <strong>{rule.title}</strong>
                        <small className="table-subtle">
                          {rule.id} · v{rule.version}
                        </small>
                      </td>
                      <td>{rule.dismissals}</td>
                      <td>{rule.overrides}</td>
                      <td>
                        <Badge
                          tone={
                            rule.dismissals + rule.overrides >= 2
                              ? "amber"
                              : "green"
                          }
                        >
                          {rule.dismissals + rule.overrides >= 2
                            ? "Review rule"
                            : "Steady"}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section className="card section-card">
            <div className="section-heading">
              <div>
                <h2>Recurring findings</h2>
                <p>Findings in the latest checks across all drafts.</p>
              </div>
            </div>
            {counts.length ? (
              <div className="chart">
                {counts.map(([name, count]) => (
                  <div key={name}>
                    <span>{name}</span>
                    <div className="bar-track" aria-hidden="true">
                      <div
                        className="chart-bar"
                        style={{ width: `${(count / max) * 100}%` }}
                      />
                    </div>
                    <strong>{count}</strong>
                  </div>
                ))}
              </div>
            ) : (
              <Empty title="No findings to chart" />
            )}
          </section>
        </div>
        <div className="stack">
          <section className="card section-card">
            <div className="section-heading">
              <div>
                <h2>Fact-change alerts</h2>
                <p>Find drafts that depend on earlier facts.</p>
              </div>
            </div>
            {currentAlert ? (
              <div className="finding-body">
                <Badge tone="amber">Open alert</Badge>
                <h3>{currentAlert.source.title} updated</h3>
                <p>
                  {currentAlert.affected.length} affected{" "}
                  {currentAlert.affected.length === 1 ? "draft" : "drafts"}.
                </p>
                <Button icon={Bell} onClick={onAlerts}>
                  View affected content
                </Button>
              </div>
            ) : (
              <Empty
                title="No open alerts"
                detail="Updating an approved fact creates an alert when content cites it."
                icon={Bell}
              />
            )}
          </section>
          <section className="card section-card">
            <div className="section-heading">
              <div>
                <h2>Expired evidence</h2>
                <p>Facts that need their owner’s review.</p>
              </div>
              <Badge tone={staleFacts.length ? "amber" : "green"}>
                {staleFacts.length}
              </Badge>
            </div>
            {staleFacts.length ? (
              <ul className="simple-list">
                {staleFacts.map((fact) => (
                  <li key={fact.id}>
                    <strong>{fact.title}</strong>
                    <small>
                      {fact.owner} · Expired {formatDate(fact.expires)}
                    </small>
                  </li>
                ))}
              </ul>
            ) : (
              <Empty title="No expired facts" icon={Check} />
            )}
          </section>
        </div>
      </div>
    </>
  );
}

export function Alerts({ alerts, onOpen, onResolve }) {
  const [tab, setTab] = useState("Open");
  const visible = alerts.filter(
    (alert) => alert.resolved === (tab === "Acknowledged")
  );
  return (
    <>
      <Header
        eyebrow="GOVERNANCE"
        title="Fact-change alerts"
        description="See which drafts need a fresh review and which published items need correction."
      />
      <Tabs
        items={["Open", "Acknowledged"]}
        value={tab}
        onChange={setTab}
        label="Alert status"
      />
      <div className="stack">
        {visible.length ? (
          visible.map((alert) => (
            <section className="card section-card" key={alert.id}>
              <div className="section-heading">
                <div>
                  <div className="heading-icon">
                    <TriangleAlert size={20} />
                    <h2>{alert.source.title} updated</h2>
                  </div>
                  <p>
                    {sourceLabel(alert.previous)} → {sourceLabel(alert.source)}{" "}
                    · {formatDate(alert.date, true)}
                  </p>
                </div>
                {!alert.resolved && (
                  <Button variant="secondary" onClick={() => onResolve(alert)}>
                    Acknowledge
                  </Button>
                )}
              </div>
              {alert.previous.value && alert.source.value && (
                <p className="callout compact">
                  <strong>
                    {money(alert.previous.value)} → {money(alert.source.value)}
                  </strong>
                </p>
              )}
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Affected content</th>
                      <th>Status at update</th>
                      <th>Next action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {alert.affected.map((draft) => (
                      <tr key={draft.id}>
                        <td>
                          <button
                            className="text-button"
                            type="button"
                            onClick={() => onOpen(draft.id)}
                          >
                            {draft.title}
                          </button>
                        </td>
                        <td>{statuses[draft.status]}</td>
                        <td>
                          <Badge tone="amber">
                            {draft.status === "published"
                              ? "Correct on live channel"
                              : "Re-check draft"}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ))
        ) : (
          <div className="card">
            <Empty
              title={
                tab === "Open"
                  ? "No open fact-change alerts"
                  : "No acknowledged alerts"
              }
              detail="Fact updates and the content they affect will appear here."
              icon={Bell}
            />
          </div>
        )}
      </div>
    </>
  );
}

export function Audit({ events, onOpen }) {
  const [query, setQuery] = useState("");
  const visible = events.filter((event) =>
    `${event.action} ${event.actor} ${event.detail} ${event.note || ""} ${
      event.sources?.map(sourceLabel).join(" ") || ""
    }`
      .toLowerCase()
      .includes(query.trim().toLowerCase())
  );
  return (
    <>
      <Header
        eyebrow="GOVERNANCE"
        title="Audit log"
        description="Review decisions, content changes, and updates to the source of truth."
      />
      <section className="card section-card">
        <div className="toolbar search-toolbar">
          <label className="search">
            <Search size={17} />
            <input
              aria-label="Search audit log"
              placeholder="Search audit events…"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
        </div>
        {visible.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Item</th>
                  <th>Actor</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((event) => (
                  <tr key={event.id}>
                    <td>
                      <strong>{event.action}</strong>
                      {event.note && (
                        <small className="table-subtle">{event.note}</small>
                      )}
                      {event.sources?.length > 0 && (
                        <small className="table-subtle">
                          {event.sources.map(sourceLabel).join(", ")}
                        </small>
                      )}
                    </td>
                    <td>
                      {event.draftId ? (
                        <button
                          className="text-button"
                          type="button"
                          onClick={() => onOpen(event.draftId)}
                        >
                          {event.detail}
                        </button>
                      ) : (
                        event.detail
                      )}
                    </td>
                    <td>{event.actor}</td>
                    <td>{formatDate(event.date, true)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty title="No matching activity" icon={History} />
        )}
      </section>
    </>
  );
}
