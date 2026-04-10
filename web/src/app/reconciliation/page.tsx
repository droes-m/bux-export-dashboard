import { AppShell } from "@/components/app-shell";
import { buildPortfolioBundleFromWorkspace } from "@/lib/dashboard";

export default async function ReconciliationPage() {
  const bundle = await buildPortfolioBundleFromWorkspace();

  return (
    <AppShell
      eyebrow="Reconciliation"
      title="Reconciling the exported data"
      summary="This page will compare local calculations against the values visible in the BUX app. The shell is ready; the market-value and gain parity logic comes after the pricing layer."
    >
      {bundle ? (
        <div className="stack">
          <div className="grid-4">
            <div className="metric-card">
              <p>Portfolio value</p>
              <strong>{bundle.metrics.portfolioValueEur.toFixed(2)} EUR</strong>
            </div>
            <div className="metric-card">
              <p>Gain</p>
              <strong>{bundle.metrics.gainAfterAllCashflowsEur.toFixed(2)} EUR</strong>
            </div>
            <div className="metric-card">
              <p>Net flows</p>
              <strong>{bundle.metrics.netExternalFlowsEur.toFixed(2)} EUR</strong>
            </div>
            <div className="metric-card">
              <p>Cash balance</p>
              <strong>{bundle.metrics.cashBalanceEur.toFixed(2)} EUR</strong>
            </div>
          </div>
          <div className="empty-state">
            This is now based on the same local valuation bundle as Overview. Next we can add BUX-entered comparison inputs and a detailed gap breakdown.
          </div>
        </div>
      ) : (
        <div className="empty-state">Import a CSV to start reconciling values.</div>
      )}
    </AppShell>
  );
}
