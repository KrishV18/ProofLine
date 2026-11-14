"use client";

import { useState } from "react";
import {
  ArrowRight,
  ClipboardCheck,
  Eye,
  EyeOff,
  FileCheck2,
  PenLine,
  ShieldCheck,
  Users,
} from "lucide-react";
import { checkBackendHealth, clearBackendToken, signIn, signUpWriter } from "../lib/backend";
import { roles } from "../lib/workflow.mjs";
import { Button, Field, Wordmark } from "./ui";

const demoUsers = {
  writer: "writer@studionorth.demo",
  manager: "manager@studionorth.demo",
};

export default function Login({ onLogin }) {
  const [role, setRole] = useState("writer");
  const [email, setEmail] = useState(demoUsers.writer);
  const [password, setPassword] = useState("proofline-demo");
  const [visible, setVisible] = useState(false);
  const [error, setError] = useState("");
  const [signup, setSignup] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  function showSignup(value) {
    setSignup(value);
    setEmail("");
    setPassword("");
    setVisible(false);
    setError("");
    setMessage("");
  }

  async function submit(event) {
    event.preventDefault();
    const address = email.trim().toLowerCase();
    const demo = address === demoUsers[role] && password === "proofline-demo";
    setBusy(true);
    setError("");
    try {
      if (signup) {
        await signUpWriter(address, password);
        showSignup(false);
        setEmail(address);
        setMessage("Account created. Sign in with your new password.");
      } else {
        clearBackendToken();
        if (demo && !(await checkBackendHealth())) {
          onLogin(role);
          return;
        }
        const user = await signIn(address, password, role);
        onLogin(role, role === "writer" && !demo ? user.id : null);
      }
    } catch (problem) {
      setError(problem instanceof TypeError
        ? "Cannot reach the ProofLine API. Check that the backend is running and try again."
        : problem.message);
    } finally {
      setBusy(false);
    }
  }

  function selectRole(value) {
    showSignup(false);
    setRole(value);
    setEmail(demoUsers[value]);
    setPassword("proofline-demo");
    setError("");
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
        <form className="login-form" onSubmit={submit}>
          <h2>{signup ? "Create a Content Writer account" : "Sign in to ProofLine"}</h2>
          <p className="muted">Choose how you’ll work in Studio North.</p>
          <fieldset className="login-roles" disabled={busy}>
            <legend className="sr-only">Workspace role</legend>
            {[
              ["writer", PenLine, "Create and check drafts"],
              ["manager", Users, "Review and manage standards"],
            ].map(([value, Icon, description]) => (
              <label
                key={value}
                className={`login-role ${role === value ? "active" : ""}`}
              >
                <input
                  type="radio"
                  name="role"
                  checked={role === value}
                  onChange={() => selectRole(value)}
                  onClick={() => {
                    if (role === value) selectRole(value);
                  }}
                />
                <Icon size={22} />
                <span>
                  <strong>{roles[value]}</strong>
                  <small>{description}</small>
                </span>
              </label>
            ))}
          </fieldset>
          <Field label="Work email">
            <input
              type="email"
              autoComplete="username"
              required
              disabled={busy}
              maxLength={254}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </Field>
          <Field label="Password">
            <span className="password-field">
              <input
                type={visible ? "text" : "password"}
                autoComplete={signup ? "new-password" : "current-password"}
                minLength={signup ? 8 : undefined}
                maxLength={signup ? 72 : undefined}
                disabled={busy}
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
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
          {message && <p role="status">{message}</p>}
          <Button type="submit" className="login-submit" disabled={busy}>
            {busy ? (signup ? "Creating account…" : "Signing in…") :
              signup ? "Create account" : `Sign in as ${roles[role]}`}
            <ArrowRight size={17} />
          </Button>
          {role === "writer" && (
            <p className="demo-note">
              <button type="button" className="text-button" disabled={busy} onClick={() => showSignup(!signup)}>
                {signup ? "Back to sign in" : "Create a Content Writer account"}
              </button>
            </p>
          )}
          {signup ? (
            <p className="demo-note">Choose a password with at least 8 characters.</p>
          ) : role === "manager" && (
            <p className="demo-note">
              <ClipboardCheck size={16} /> Use your provided Manager credentials.
            </p>
          )}
        </form>
      </section>
    </main>
  );
}
