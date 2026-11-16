"use client";

import { useEffect, useRef } from "react";
import { Check, FileText, X } from "lucide-react";
import { statuses } from "../lib/workflow.mjs";

export function Wordmark({ collapsed = false }) {
  if (collapsed) {
    return (
      <span className="wordmark" title="ProofLine" style={{ justifyContent: "center", display: "inline-flex" }}>
        <span
          style={{
            width: 14,
            height: 14,
            borderRadius: "50%",
            background: "linear-gradient(135deg, #2dd4bf 0%, #0d9488 100%)",
            boxShadow: "0 0 12px rgba(45, 212, 191, 0.4)",
            display: "inline-block",
          }}
        />
      </span>
    );
  }
  return (
    <span className="wordmark">
      <span className="wordmark-symbol">
        <span
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: "linear-gradient(135deg, #2dd4bf 0%, #0d9488 100%)",
            boxShadow: "0 0 10px rgba(45, 212, 191, 0.35)",
            display: "inline-block",
          }}
        />
      </span>
      ProofLine<span className="wordmark-dot">.</span>
    </span>
  );
}
export function Button({
  icon: Icon,
  variant = "primary",
  children,
  className = "",
  ...props
}) {
  return (
    <button
      type="button"
      className={`button button-${variant} ${className}`}
      style={{ transition: "all 0.2s ease" }}
      {...props}
    >
      {Icon && <Icon size={16} aria-hidden="true" />}
      {children}
    </button>
  );
}
export function Badge({ children, tone = "neutral" }) {
  return (
    <span
      className={`badge badge-${tone}`}
      style={{ transition: "all 0.15s ease" }}
    >
      {children}
    </span>
  );
}
const statusTones = {
  review: "amber",
  changes: "red",
  approved: "green",
  published: "green",
  recheck: "amber",
};
export function Status({ value }) {
  return <Badge tone={statusTones[value]}>{statuses[value]}</Badge>;
}
export function Risk({ value }) {
  return (
    <Badge
      tone={value === "High" ? "red" : value === "Medium" ? "amber" : "green"}
    >
      {value} risk
    </Badge>
  );
}
export function Header({ eyebrow, title, description, actions }) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1 style={{ fontFamily: "inherit", letterSpacing: "-0.02em" }}>
          {title}
        </h1>
        {description && (
          <p className="page-description" style={{ fontSize: 15 }}>
            {description}
          </p>
        )}
      </div>
      {actions && <div className="header-actions">{actions}</div>}
    </header>
  );
}
export function Tabs({ items, value, onChange, label }) {
  return (
    <nav className="tabs" aria-label={label}>
      {items.map((item) => {
        const { key, name } =
          typeof item === "string" ? { key: item, name: item } : item;
        const isSelected = value === key;
        return (
          <button
            type="button"
            key={key}
            className={isSelected ? "tab selected" : "tab"}
            aria-current={isSelected ? "true" : undefined}
            onClick={() => onChange(key)}
            style={{
              borderRadius: "8px",
              transition: "all 0.2s ease",
              ...(isSelected
                ? {
                    background: "var(--teal-light)",
                    color: "var(--teal-dark)",
                    borderBottom: "none",
                  }
                : {}),
            }}
          >
            {name}
          </button>
        );
      })}
    </nav>
  );
}
export function Empty({ title, detail, action, icon: Icon = FileText }) {
  return (
    <div className="empty">
      <span
        className="empty-icon"
        style={{
          width: 56,
          height: 56,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: "16px",
          background: "var(--teal-light, #e8f5f0)",
          color: "var(--teal-dark, #0d9488)",
        }}
      >
        <Icon size={28} />
      </span>
      <h3>{title}</h3>
      {detail && <p style={{ color: "#6b7280" }}>{detail}</p>}
      {action}
    </div>
  );
}
export function Modal({ title, children, onClose, className = "" }) {
  const ref = useRef(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog.showModal();
    return () => dialog.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className={`modal ${className}`.trim()}
      aria-labelledby="modal-title"
      style={{ borderRadius: "20px", backdropFilter: "blur(12px)" }}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <div className="modal-header">
        <h2 id="modal-title">{title}</h2>
        <button
          type="button"
          className="icon-button"
          aria-label="Close dialog"
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Field({ label, hint, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
      {hint && <small>{hint}</small>}
    </label>
  );
}
export function Toast({ children }) {
  return (
    <div
      className="toast"
      role="status"
      style={{ backdropFilter: "blur(12px)", borderRadius: "100px" }}
    >
      <Check size={18} />
      {children}
    </div>
  );
}
