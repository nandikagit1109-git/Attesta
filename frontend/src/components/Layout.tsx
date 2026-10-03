import { Link, NavLink, useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../lib/auth";
import type { Role } from "../lib/types";

const LINKS: { to: string; label: string; roles: Role[] | null }[] = [
  { to: "/dashboard", label: "Dashboard", roles: ["student"] },
  { to: "/graph", label: "Skill graph", roles: ["student"] },
  { to: "/career", label: "Career gap", roles: ["student"] },
  { to: "/profile", label: "Profile", roles: ["student"] },
  { to: "/issuer", label: "Issuer desk", roles: ["issuer"] },
  { to: "/recruiter", label: "Recruiter", roles: ["recruiter"] },
  { to: "/audit", label: "Audit log", roles: null },
  { to: "/verify", label: "Verify a file", roles: null },
];

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const links = LINKS.filter((l) => !l.roles || (user && l.roles.includes(user.role)));

  return (
    <div className="min-h-screen bg-paper text-ink">
      <header className="border-b border-ink">
        <div className="mx-auto max-w-page px-6 py-3 flex items-center justify-between gap-6">
          <Link to="/" className="font-display text-xl font-semibold tracking-tight">
            Attesta
          </Link>
          <nav className="flex items-center gap-5 text-sm">
            {links.map((l) => (
              <NavLink
                key={l.to}
                to={l.to}
                className={({ isActive }) =>
                  isActive ? "underline underline-offset-4" : "hover:underline"
                }
              >
                {l.label}
              </NavLink>
            ))}
          </nav>
          <div className="text-sm flex items-center gap-3">
            {user ? (
              <>
                <span className="font-mono text-xs">
                  {user.full_name} · {user.role}
                </span>
                <button
                  className="border border-ink px-3 py-1 text-xs"
                  onClick={() => {
                    logout();
                    navigate("/");
                  }}
                >
                  Log out
                </button>
              </>
            ) : (
              <Link to="/login" className="border border-ink px-3 py-1 text-xs">
                Log in
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-page px-6 py-8">{children}</main>
      <footer className="border-t border-ink">
        <div className="mx-auto max-w-page px-6 py-4 text-xs text-ink">
          Attesta. AI agents analyze evidence, issuers confirm, SHA-256 hashes are anchored
          on-chain. Verify without trusting our servers.
        </div>
      </footer>
    </div>
  );
}
