import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import type { Role } from "../lib/types";

const DEMO: { role: Role; title: string; blurb: string }[] = [
  { role: "student", title: "Student", blurb: "Upload evidence, approve skills, share your link." },
  { role: "issuer", title: "Issuer", blurb: "Confirm evidence, anchor hashes on-chain, revoke." },
  { role: "admin", title: "Admin", blurb: "Owns the demo dataset, reset and one-click tamper." },
];

export default function Login() {
  const { login, demoLogin } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function homeFor(role: Role) {
    return role === "student" ? "/dashboard" : role === "issuer" ? "/issuer" : "/admin";
  }

  async function doDemo(role: Role) {
    setError("");
    setBusy(true);
    try {
      await demoLogin(role);
      navigate(homeFor(role));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function doLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const user = await login(email, password);
      navigate(homeFor(user.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      <section className="lg:col-span-5">
        <h1 className="font-display text-3xl font-semibold">Log in</h1>
        <p className="mt-2 text-sm">One click for the demo, or your own account below.</p>
        <p className="mt-2 text-xs border border-ink bg-surface px-3 py-2">
          Recruiters never log in. Students share a link and QR code; open it and
          you are the recruiter.
        </p>
        <div className="mt-6 border border-ink divide-y divide-ink">
          {DEMO.map((d) => (
            <div key={d.role} className="px-4 py-3 flex items-center justify-between gap-4">
              <div>
                <p className="font-display">{d.title}</p>
                <p className="text-xs">{d.blurb}</p>
              </div>
              <button
                disabled={busy}
                onClick={() => doDemo(d.role)}
                className="border border-ink px-3 py-1 text-xs whitespace-nowrap disabled:opacity-50"
              >
                Log in as {d.title.toLowerCase()}
              </button>
            </div>
          ))}
        </div>
        {busy && <p className="mt-3 text-sm">Loading</p>}
        {error && <p className="mt-3 text-sm text-rust">{error}</p>}
      </section>

      <section className="lg:col-span-7 lg:border-l border-ink lg:pl-8">
        <form onSubmit={doLogin} className="max-w-md space-y-4">
          <div>
            <label htmlFor="email" className="block text-xs uppercase tracking-wide mb-1">
              Email
            </label>
            <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="w-full" />
          </div>
          <div>
            <label htmlFor="password" className="block text-xs uppercase tracking-wide mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full"
            />
          </div>
          <button type="submit" disabled={busy} className="bg-rust text-paper px-5 py-2 text-sm disabled:opacity-50">
            Log in
          </button>
          <p className="text-xs">
            New here? Register an account from the command line seed or ask the issuer to bulk-load
            students; the demo accounts above are always available.
          </p>
        </form>
      </section>
    </div>
  );
}
