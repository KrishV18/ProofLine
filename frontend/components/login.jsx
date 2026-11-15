"use client";

import { useEffect, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Building2,
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
    fetchCompanies().then(setCompanies);
  }, []);

  const matchedCompany = companies.find(
    (c) => c.name.trim().toLowerCase() === companyInput.trim().toLowerCase()
  );

  function handleCompanyNext() {
    if (!companyInput.trim()) {
      setError("Please enter your company name.");
      return;
    }
    setError("");
    if (matchedCompany) {
      setStep("signin");
    } else {
      setStep("register");
    }
  }

  async function handleSignIn(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const user = await login(email, password);
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
        companyInput.trim(),
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
        {/* ── Step 1: Company ── */}
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
                  placeholder="e.g. Studio North"
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

            {companyInput.trim() && !matchedCompany && (
              <p className="muted" style={{ fontSize: "0.8rem" }}>
                No company found — continuing will create a new account for{" "}
                <strong>{companyInput.trim()}</strong>.
              </p>
            )}
            {matchedCompany && (
              <p className="muted" style={{ fontSize: "0.8rem", color: "var(--teal)" }}>
                ✓ Company found — sign in with your credentials.
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

        {/* ── Step 2a: Sign In ── */}
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
            <h2>Welcome back</h2>
            <p className="muted">
              Signing in to <strong>{companyInput.trim()}</strong>
            </p>

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
                  Sign in <ArrowRight size={17} />
                </>
              )}
            </Button>
          </form>
        )}

        {/* ── Step 2b: Register new company ── */}
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
              Setting up <strong>{companyInput.trim()}</strong> on ProofLine.
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
                Your role
              </legend>
              {[
                ["creator", PenLine, "Create and check drafts"],
                ["manager", Users, "Review and approve drafts"],
              ].map(([value, Icon, description]) => (
                <label
                  key={value}
                  className={`login-role ${role === value ? "active" : ""}`}
                >
                  <input
                    type="radio"
                    name="role"
                    checked={role === value}
                    onChange={() => setRole(value)}
                  />
                  <Icon size={22} />
                  <span>
                    <strong style={{ textTransform: "capitalize" }}>{value}</strong>
                    <small>{description}</small>
                  </span>
                </label>
              ))}
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
                  Create workspace <ArrowRight size={17} />
                </>
              )}
            </Button>
          </form>
        )}
      </section>
    </main>
  );
}
