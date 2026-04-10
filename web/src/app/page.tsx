import { AppShell } from "@/components/app-shell";
import { MetricCard } from "@/components/metric-card";
import { SectionCard } from "@/components/section-card";
import { formatEuro } from "@/lib/portfolio";
import { buildPortfolioBundleFromWorkspace } from "@/lib/dashboard";
import { readWorkspaceState } from "@/lib/storage";

export default async function HomePage() {
  const [state, bundle] = await Promise.all([readWorkspaceState(), buildPortfolioBundleFromWorkspace()]);

  return (
    <AppShell
      eyebrow="Overview"
      title="Portfolio dashboard, rebuilt for the browser"
      summary="The web version now reads the local CSV, loads the mapped securities, fetches market prices, and turns that into portfolio value, gain, and allocation."
    >
      {bundle ? (
        <div className="stack">
          <div className="grid-4">
            <MetricCard label="Portfolio" value={formatEuro(bundle.metrics.portfolioValueEur)} detail="Cash plus market value" />
            <MetricCard label="Gain" value={formatEuro(bundle.metrics.gainAfterAllCashflowsEur)} detail={`Net external flows: ${formatEuro(bundle.metrics.netExternalFlowsEur)}`} />
            <MetricCard label="Market value" value={formatEuro(bundle.metrics.marketValueEur)} detail="Marked-to-market holdings value" />
            <MetricCard label="Cash balance" value={formatEuro(bundle.metrics.cashBalanceEur)} detail="Latest reported cash balance" />
          </div>

          <div className="two-col">
            <SectionCard title="Monthly portfolio movement">
              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Month</th>
                      <th>Portfolio change</th>
                      <th>Net deposits</th>
                      <th>Market result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bundle.monthlyPerformanceRows.map((row) => (
                      <tr key={row.month}>
                        <td>{row.monthLabel}</td>
                        <td>{formatEuro(row.totals.portfolio_change_eur)}</td>
                        <td>{formatEuro(row.totals.external_flow_eur)}</td>
                        <td>{formatEuro(row.totals.market_result_eur)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </SectionCard>

            <SectionCard title="Current allocation">
              <div style={{ overflowX: "auto" }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Asset</th>
                      <th>Ticker</th>
                      <th>Value</th>
                      <th>Weight</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bundle.allocationRows.map((row) => (
                      <tr key={row.assetId}>
                        <td>{row.assetName}</td>
                        <td>{row.ticker}</td>
                        <td>{formatEuro(row.valueEur)}</td>
                        <td>{(row.weight * 100).toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </SectionCard>
          </div>

          <div className="two-col">
            <SectionCard title="Workspace status">
              <p className="panel-copy">
                Imported at <strong>{state ? new Date(state.importedAt).toLocaleString("nl-BE") : "unknown"}</strong>.
                <br />
                The raw CSV, security map, and workspace state are on disk under <code>web/data/</code>.
              </p>
              <div className="empty-state">
                Next migration step: drilldown, reconciliation, and editable mapping parity.
              </div>
            </SectionCard>
            <SectionCard title="Coverage">
              <p className="panel-copy">
                Transactions: <strong>{bundle.transactions.length.toLocaleString("nl-BE")}</strong>
                <br />
                Securities in master: <strong>{bundle.securityMaster.length.toLocaleString("nl-BE")}</strong>
                <br />
                Mapped entries: <strong>{bundle.securityMap.filter((row) => row.ticker).length.toLocaleString("nl-BE")}</strong>
              </p>
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
