"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import type { SecurityMapRow } from "@/lib/types";

function cloneRows(rows: SecurityMapRow[]): SecurityMapRow[] {
  return rows.map((row) => ({ ...row }));
}

export function MappingEditor({ initialRows }: { initialRows: SecurityMapRow[] }) {
  const router = useRouter();
  const [rows, setRows] = useState<SecurityMapRow[]>(() => cloneRows(initialRows));
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const unresolvedCount = useMemo(
    () => rows.filter((row) => !row.ticker.trim()).length,
    [rows]
  );

  function updateRow(index: number, patch: Partial<SecurityMapRow>) {
    setRows((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  }

  async function saveRows(nextRows: SecurityMapRow[]) {
    setBusy(true);
    setStatus(null);
    try {
      const response = await fetch("/api/mapping", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(nextRows)
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => null)) as { error?: string } | null;
        throw new Error(body?.error ?? "Save failed");
      }
      setStatus("Saved locally.");
      router.refresh();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="grid-4">
        <section className="metric-card">
          <p>Rows</p>
          <strong>{rows.length.toLocaleString("nl-BE")}</strong>
        </section>
        <section className="metric-card">
          <p>Unmapped</p>
          <strong>{unresolvedCount.toLocaleString("nl-BE")}</strong>
        </section>
        <section className="metric-card">
          <p>Editable fields</p>
          <strong>ticker, scale, source</strong>
        </section>
        <section className="metric-card">
          <p>Storage</p>
          <strong>web/data/security-map.json</strong>
        </section>
      </div>

      <div className="panel">
        <div className="panel-head">
          <h3>Editable mapping</h3>
          <div style={{ display: "flex", gap: 12 }}>
            <button type="button" className="secondary-button" onClick={() => setRows(cloneRows(initialRows))} disabled={busy}>
              Reset
            </button>
            <button type="button" onClick={() => void saveRows(rows)} disabled={busy}>
              {busy ? "Saving..." : "Save mapping"}
            </button>
          </div>
        </div>
        <p className="panel-copy">Edit the ticker and quote scale locally, then save to update valuation across the app.</p>
        {status ? <div className="empty-state">{status}</div> : null}

        <div style={{ overflowX: "auto" }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Asset</th>
                <th>Ticker</th>
                <th>Scale</th>
                <th>Exchange</th>
                <th>Source</th>
                <th>Confidence</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={row.assetId}>
                  <td>
                    <strong>{row.assetName}</strong>
                    <br />
                    <small>{row.assetId}</small>
                    <br />
                    <small>{row.assetCurrency || "-"}</small>
                  </td>
                  <td>
                    <input
                      className="text-input"
                      value={row.ticker}
                      onChange={(event) => updateRow(index, { ticker: event.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      className="text-input"
                      type="number"
                      step="0.01"
                      value={row.priceScale}
                      onChange={(event) => updateRow(index, { priceScale: Number(event.target.value) || 1 })}
                    />
                  </td>
                  <td>
                    <input
                      className="text-input"
                      value={row.exchange}
                      onChange={(event) => updateRow(index, { exchange: event.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      className="text-input"
                      value={row.source}
                      onChange={(event) => updateRow(index, { source: event.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      className="text-input"
                      value={row.confidence}
                      onChange={(event) => updateRow(index, { confidence: event.target.value })}
                    />
                  </td>
                  <td>
                    <textarea
                      className="text-area"
                      rows={2}
                      value={row.notes}
                      onChange={(event) => updateRow(index, { notes: event.target.value })}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
