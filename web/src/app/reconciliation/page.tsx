import { AppShell } from "@/components/app-shell";
import { buildPortfolioBundleFromWorkspace } from "@/lib/dashboard";
import { formatEuro } from "@/lib/portfolio";

type SearchParams = {
  buxValue?: string;
  buxGain?: string;
};

function parseAmount(value: string | undefined, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

export default async function ReconciliationPage({ searchParams }: { searchParams?: Promise<SearchParams> }) {
  const bundle = await buildPortfolioBundleFromWorkspace();
  const params = (await searchParams) ?? {};
  const buxValue = parseAmount(params.buxValue, 21824.53);
  const buxGain = parseAmount(params.buxGain, 3974.53);

  return (
    <AppShell
      eyebrow="Reconciliation"
      title="Reconciling the exported data"
      summary="Compare the local valuation bundle against the BUX app values. The comparison uses the same locally stored transactions and mapping file."
    >
      {bundle ? (
        <div className="stack">
          <section className="panel">
            <div className="panel-head">
              <h3>Comparison inputs</h3>
            </div>
            <form method="get" className="grid-4">
              <label>
                <span className="brand-kicker">BUX portfolio value</span>
                <input className="text-input" type="number" step="0.01" name="buxValue" defaultValue={buxValue} />
              </label>
              <label>
                <span className="brand-kicker">BUX gain</span>
                <input className="text-input" type="number" step="0.01" name="buxGain" defaultValue={buxGain} />
              </label>
              <div style={{ display: "flex", alignItems: "end" }}>
                <button type="submit">Recalculate</button>
              </div>
            </form>
          </section>

          <div className="grid-4">
            <div className="metric-card">
              <p>Portfolio value</p>
              <strong>{formatEuro(bundle.metrics.portfolioValueEur)}</strong>
              <span>Delta vs BUX: {formatEuro(bundle.metrics.portfolioValueEur - buxValue)}</span>
            </div>
            <div className="metric-card">
              <p>Gain</p>
              <strong>{formatEuro(bundle.metrics.gainAfterAllCashflowsEur)}</strong>
              <span>Delta vs BUX: {formatEuro(bundle.metrics.gainAfterAllCashflowsEur - buxGain)}</span>
            </div>
            <div className="metric-card">
              <p>Net flows</p>
              <strong>{formatEuro(bundle.metrics.netExternalFlowsEur)}</strong>
              <span>Implied base comparison</span>
            </div>
            <div className="metric-card">
              <p>Cash balance</p>
              <strong>{formatEuro(bundle.metrics.cashBalanceEur)}</strong>
              <span>Current local valuation</span>
            </div>
          </div>

          <section className="panel">
            <div className="panel-head">
              <h3>Gap summary</h3>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>Value gap</td>
                    <td>{formatEuro(bundle.metrics.portfolioValueEur - buxValue)}</td>
                  </tr>
                  <tr>
                    <td>Gain gap</td>
                    <td>{formatEuro(bundle.metrics.gainAfterAllCashflowsEur - buxGain)}</td>
                  </tr>
                  <tr>
                    <td>Base gap</td>
                    <td>{formatEuro(bundle.metrics.netExternalFlowsEur - (buxValue - buxGain))}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel">
            <div className="panel-head">
              <h3>Current holdings contribution</h3>
            </div>
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
          </section>

          <div className="empty-state">
            At export end {bundle.transactions[bundle.transactions.length - 1]?.date ?? "n/a"} the local valuation bundle now uses the same net-flow and market-value split as the overview.
          </div>
        </div>
      ) : (
        <div className="empty-state">Import a CSV to start reconciling values.</div>
      )}
    </AppShell>
  );
}
