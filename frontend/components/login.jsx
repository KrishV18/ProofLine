"use client";

import { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  ClipboardCheck,
  Eye,
  EyeOff,
  FileCheck2,
  Loader2,
  PenLine,
  ShieldCheck,
  Users,
} from "lucide-react";
import { fetchCompanies, login, register } from "../lib/backend";
import { Button, Field, Wordmark } from "./ui";

const demoCredentials = {
  creator: {
    email: "writer@studionorth.demo",
    password: "proofline-demo",
  },
  manager: {
    email: "manager@studionorth.demo",
    password: "proofline-demo",
  },
};

const roleInfo = {
  creator: {
    label: "Creator",
    description: "Create and check drafts",
    Icon: PenLine,
  },
  manager: {
    label: "Manager",
    description: "Review and approve drafts",
    Icon: Users,
  },
};

export default function Login({ onLogin }) {
  // "company" | "signin" | "register"
  const [step, setStep] = useState("company");
  const [companies, setCompanies] = useState([]);
  const [companyInput, setCompanyInput] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("creator");
  const [visible, setVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchCompanies().then((list) => {
      setCompanies(list);
    });
  }, []);

  const trimmedCompany = companyInput.trim();
  const matchedCompany = companies.find(
    (c) => c.name.trim().toLowerCase() === trimmedCompany.toLowerCase()
  );

  const isDemoCompany =
    trimmedCompany.toLowerCase().includes("proofline") ||
    trimmedCompany.toLowerCase().includes("studio north") ||
    trimmedCompany.toLowerCase() === "demo";

  function handleCompanyNext() {
    if (!trimmedCompany) {
      setError("Please enter your company name.");
      return;
    }
    setError("");
    if (matchedCompany) {
      setStep("signin");
      // Auto-fill demo credentials if it's the demo company
      if (isDemoCompany) {
        setEmail(demoCredentials[role].email);
        setPassword(demoCredentials[role].password);
      } else {
        setEmail("");
        setPassword("");
      }
    } else {
      setStep("register");
      setEmail("");
      setPassword("");
    }
  }

  function handleRoleSelect(selectedRole) {
    setRole(selectedRole);
    setError("");
    if (isDemoCompany) {
      setEmail(demoCredentials[selectedRole].email);
      setPassword(demoCredentials[selectedRole].password);
    }
  }

  async function handleSignIn(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const user = await login(email, password, role);
      onLogin(user);
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Cannot reach the ProofLine API. Check that the backend is running and try again."
          : err.message || "Invalid email or password."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister(e) {
    e.preventDefault();
    setError("");
    if (!fullName.trim()) {
      setError("Please enter your full name.");
      return;
    }
    setLoading(true);
    try {
      const user = await register(
        trimmedCompany,
        fullName.trim(),
        email,
        password,
        role
      );
      onLogin(user);
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Cannot reach the ProofLine API. Check that the backend is running and try again."
          : err.message || "Registration failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login">
      <section className="login-story">
        <Wordmark />
        <div className="login-story-content">
          <p className="eyebrow">
            <span className="signal" /> Pre-publication review
          </p>
          <h1>
            Check it before
            <br />
            you publish it<span>.</span>
          </h1>
          <p className="login-tagline">
            A shared workspace for better drafts, evidence-backed feedback, and
            approvals you can trace.
          </p>
          <div className="login-steps">
            {[
              ["Draft", PenLine],
              ["Evidence", FileCheck2],
              ["Approval", ShieldCheck],
            ].map(([name, Icon]) => (
              <div className="login-step" key={name}>
                <span>
                  <Icon size={23} strokeWidth={1.7} />
                </span>
                {name}
              </div>
            ))}
          </div>
        </div>
        <p className="login-story-footer">
          <span>ProofLine</span>
          <span>Brand review workspace</span>
        </p>
      </section>

      <section className="login-panel">
        {/* ── Step 1: Company Input ── */}
        {step === "company" && (
          <form
            className="login-form"
            onSubmit={(e) => {
              e.preventDefault();
              handleCompanyNext();
            }}
          >
            <h2>Sign in to ProofLine</h2>
            <p className="muted">Enter your company name to get started.</p>

            <Field label="Company name">
              <div style={{ position: "relative" }}>
                <span
                  style={{
                    position: "absolute",
                    left: 10,
                    top: "50%",
                    transform: "translateY(-50%)",
                    color: "var(--muted)",
                    pointerEvents: "none",
                  }}
                >
                  <Building2 size={16} />
                </span>
                <input
                  type="text"
                  autoComplete="organization"
                  required
                  placeholder="e.g. ProofLine Demo Org"
                  value={companyInput}
                  onChange={(e) => {
                    setCompanyInput(e.target.value);
                    setError("");
                  }}
                  style={{ paddingLeft: 32 }}
                  list="companies-list"
                />
                <datalist id="companies-list">
                  {companies.map((c) => (
                    <option key={c.id} value={c.name} />
                  ))}
                </datalist>
              </div>
            </Field>

            {trimmedCompany && !matchedCompany && (
              <p className="muted" style={{ fontSize: "0.8rem" }}>
                No existing company found — continuing will create a new workspace for{" "}
                <strong>{trimmedCompany}</strong>.
              </p>
            )}
            {matchedCompany && (
              <p className="muted" style={{ fontSize: "0.8rem", color: "var(--teal)" }}>
                ✓ Company found — continue to sign in.
              </p>
            )}

            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}

            <Button type="submit" className="login-submit">
              Continue <ArrowRight size={17} />
            </Button>
          </form>
        )}

        {/* ── Step 2a: Sign In with Role Selection ── */}
        {step === "signin" && (
          <form className="login-form" onSubmit={handleSignIn}>
            <button
              type="button"
              className="icon-button"
              style={{ alignSelf: "flex-start", marginBottom: 4 }}
              onClick={() => {
                setStep("company");
                setError("");
              }}
            >
              <ArrowLeft size={16} />
            </button>
            <h2>Sign in to ProofLine</h2>
            <p className="muted">
              Choose how you’ll work in <strong>{matchedCompany?.name || trimmedCompany}</strong>.
            </p>

            {/* 2 Role Options: Creator and Manager */}
            <fieldset className="login-roles" disabled={loading}>
              <legend className="sr-only">Workspace role</legend>
              {["creator", "manager"].map((roleKey) => {
                const info = roleInfo[roleKey];
                const IconComponent = info.Icon;
                const isActive = role === roleKey;
                return (
                  <label
                    key={roleKey}
                    className={`login-role ${isActive ? "active" : ""}`}
                  >
                    <input
                      type="radio"
                      name="role"
                      checked={isActive}
                      onChange={() => handleRoleSelect(roleKey)}
                    />
                    <IconComponent size={22} />
                    <span>
                      <strong>{info.label}</strong>
                      <small>{info.description}</small>
                    </span>
                  </label>
                );
              })}
            </fieldset>

            <Field label="Work email">
              <input
                type="email"
                autoComplete="username"
                required
                disabled={loading}
                maxLength={254}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </Field>

            <Field label="Password">
              <span className="password-field">
                <input
                  type={visible ? "text" : "password"}
                  autoComplete="current-password"
                  required
                  disabled={loading}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="icon-button"
                  aria-label={visible ? "Hide password" : "Show password"}
                  onClick={() => setVisible(!visible)}
                >
                  {visible ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </span>
            </Field>

            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}

            <Button type="submit" className="login-submit" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 size={17} className="spin" /> Signing in…
                </>
              ) : (
                <>
                  Sign in as {roleInfo[role].label} <ArrowRight size={17} />
                </>
              )}
            </Button>

            {isDemoCompany && (
              <p className="demo-note">
                <ClipboardCheck size={16} /> Demo credentials are automatically filled in for {roleInfo[role].label}.
              </p>
            )}
          </form>
        )}

        {/* ── Step 2b: Register New Company Workspace ── */}
        {step === "register" && (
          <form className="login-form" onSubmit={handleRegister}>
            <button
              type="button"
              className="icon-button"
              style={{ alignSelf: "flex-start", marginBottom: 4 }}
              onClick={() => {
                setStep("company");
                setError("");
              }}
            >
              <ArrowLeft size={16} />
            </button>
            <h2>Create your workspace</h2>
            <p className="muted">
              Setting up <strong>{trimmedCompany}</strong> on ProofLine.
            </p>

            <Field label="Your full name">
              <input
                type="text"
                autoComplete="name"
                required
                disabled={loading}
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </Field>

            <Field label="Work email">
              <input
                type="email"
                autoComplete="username"
                required
                disabled={loading}
                maxLength={254}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </Field>

            <Field label="Password">
              <span className="password-field">
                <input
                  type={visible ? "text" : "password"}
                  autoComplete="new-password"
                  required
                  minLength={8}
                  maxLength={72}
                  disabled={loading}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="icon-button"
                  aria-label={visible ? "Hide password" : "Show password"}
                  onClick={() => setVisible(!visible)}
                >
                  {visible ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </span>
            </Field>

            <fieldset className="login-roles" disabled={loading}>
              <legend style={{ fontSize: "0.8rem", marginBottom: 6, color: "var(--muted)" }}>
                Your workspace role
              </legend>
              {["creator", "manager"].map((roleKey) => {
                const info = roleInfo[roleKey];
                const IconComponent = info.Icon;
                const isActive = role === roleKey;
                return (
                  <label
                    key={roleKey}
                    className={`login-role ${isActive ? "active" : ""}`}
                  >
                    <input
                      type="radio"
                      name="role"
                      checked={isActive}
                      onChange={() => setRole(roleKey)}
                    />
                    <IconComponent size={22} />
                    <span>
                      <strong>{info.label}</strong>
                      <small>{info.description}</small>
                    </span>
                  </label>
                );
              })}
            </fieldset>

            <p className="demo-note">Choose a password with at least 8 characters.</p>

            {error && (
              <p role="alert" className="error">
                {error}
              </p>
            )}

            <Button type="submit" className="login-submit" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 size={17} className="spin" /> Creating workspace…
                </>
              ) : (
                <>
                  Create workspace as {roleInfo[role].label} <ArrowRight size={17} />
                </>
              )}
            </Button>
          </form>
        )}
      </section>
    </main>
  );
}
