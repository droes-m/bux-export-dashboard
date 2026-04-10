import Link from "next/link";
import type { ReactNode } from "react";

type NavItem = {
  href: string;
  label: string;
  description: string;
};

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Overview", description: "Portfolio summary and quick health check" },
  { href: "/import", label: "Import", description: "Upload or replace a local BUX export" },
  { href: "/cashflows", label: "Cashflows", description: "Monthly deposits, fees, dividends, and tax" },
  { href: "/transactions", label: "Transactions", description: "Browse the raw ledger" },
  { href: "/mapping", label: "Mapping", description: "Inspect the security master and mappings" },
  { href: "/forecast", label: "Forecast", description: "Later: trend and projection layer" },
  { href: "/reconciliation", label: "Reconciliation", description: "Later: compare against the BUX app" }
];

export function AppShell({
  children,
  title,
  eyebrow,
  summary
}: {
  children: ReactNode;
  title: string;
  eyebrow: string;
  summary: string;
}) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">BX</div>
          <div>
            <p className="brand-kicker">BUX export dashboard</p>
            <h1>Local web migration</h1>
          </div>
        </div>
        <nav className="nav-list" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <Link key={item.href} href={item.href} className="nav-item">
              <span>{item.label}</span>
              <small>{item.description}</small>
            </Link>
          ))}
        </nav>
        <div className="sidebar-note">
          <p>File-based workspace</p>
          <span>CSV uploads and generated state stay under `web/data/`.</span>
        </div>
      </aside>

      <main className="content-area">
        <header className="page-hero">
          <p className="eyebrow">{eyebrow}</p>
          <h2>{title}</h2>
          <p className="summary">{summary}</p>
        </header>
        {children}
      </main>
    </div>
  );
}
