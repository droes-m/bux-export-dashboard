import { AppShell } from "@/components/app-shell";
import { MetricCard } from "@/components/metric-card";
import { MonthlyBars } from "@/components/monthly-bars";
import { SectionCard } from "@/components/section-card";
import { readWorkspaceState } from "@/lib/storage";
import { formatEuro } from "@/lib/portfolio";

export default async function HomePage() {
  const state = await readWorkspaceState();

  return (
    <AppShell
      eyebrow="Overview"
      title="Portfolio dashboard, rebuilt for the browser"
      summary="This first React pass focuses on the modern shell, local file persistence, and transaction-driven summaries. The valuation and market-data layer will be ported next so the new app matches the Python dashboard."
    >
      {state ? (
        <div className="stack">
          <div className="grid-4">
            <MetricCard label="Transactions" value={state.transactionCount.toLocaleString("nl-BE")} detail={`Imported from ${state.sourceFileName}`} />
            <MetricCard label="Net deposits" value={formatEuro(state.metrics.netExternalFlowsEur)} detail="Cumulative external cash in" />
            <MetricCard label="Realized P/L" value={formatEuro(state.metrics.realizedPnlEur)} detail="Sell-trade P/L from the export" />
            <MetricCard label="Cash balance" value={formatEuro(state.metrics.latestCashBalanceEur)} detail="Latest reported cash balance" />
          </div>

          <div className="two-col">
            <SectionCard title="Monthly cashflow mix">
              <MonthlyBars rows={state.monthlyCategoryRows} />
            </SectionCard>

            <SectionCard title="Workspace status">
              <p className="panel-copy">
                Imported at <strong>{new Date(state.importedAt).toLocaleString("nl-BE")}</strong>.
                <br />
                The raw CSV and derived state are now on disk under <code>web/data/</code>.
              </p>
              <div className="empty-state">
                Next migration step: market pricing, portfolio valuation, and the Overview/Drilldown pages from the Streamlit app.
              </div>
            </SectionCard>
          </div>
        </div>
      ) : (
        <div className="onboarding">
          <div className="grid-4" style={{ marginBottom: 0 }}>
            <MetricCard label="Step 1" value="Upload CSV" detail="Use the Import page to create a local workspace." />
            <MetricCard label="Step 2" value="Persist files" detail="Raw export and derived JSON stay in web/data/." />
            <MetricCard label="Step 3" value="Port analytics" detail="Transactions, mapping, reconciliation, valuation." />
            <MetricCard label="Step 4" value="Polish UX" detail="Modern shell, better layout, and responsive charts." />
          </div>
        </div>
      )}
    </AppShell>
  );
}
