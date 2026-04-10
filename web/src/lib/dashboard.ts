import type {
  AllocationRow,
  MonthlyCategoryRow,
  PortfolioBundle,
  PortfolioRow,
  PriceRow,
  SecurityMapRow,
  SecurityMasterRow,
  TransactionRow
} from "@/lib/types";
import { buildInitialSecurityMap, effectiveMapping } from "@/lib/mapping";
import { fetchEurUsd, fetchPrices } from "@/lib/market";
import { readImportedTransactionsCsv, readSecurityMap, readWorkspaceState } from "@/lib/storage";
import { buildSecurityMaster, computeMetrics, parseTransactionsCsv } from "@/lib/portfolio";

function parseDateKey(value: string): Date {
  return new Date(`${value}T00:00:00.000Z`);
}

function buildDateKeys(startDate: Date, endDate: Date): string[] {
  const start = new Date(Date.UTC(startDate.getUTCFullYear(), startDate.getUTCMonth(), startDate.getUTCDate()));
  const end = new Date(Date.UTC(endDate.getUTCFullYear(), endDate.getUTCMonth(), endDate.getUTCDate()));
  const out: string[] = [];
  for (let cursor = start; cursor <= end; cursor = new Date(cursor.getTime() + 24 * 60 * 60 * 1000)) {
    out.push(cursor.toISOString().slice(0, 10));
  }
  return out;
}

function buildPriceLookup(rows: PriceRow[]): Map<string, Map<string, number>> {
  const lookup = new Map<string, Map<string, number>>();
  for (const row of rows) {
    if (!lookup.has(row.ticker)) {
      lookup.set(row.ticker, new Map());
    }
    lookup.get(row.ticker)?.set(row.date, row.close);
  }
  return lookup;
}

function buildDateLookup(rows: PriceRow[]): Map<string, number> {
  const lookup = new Map<string, number>();
  for (const row of rows) {
    lookup.set(row.date, row.close);
  }
  return lookup;
}

function buildDailyHoldings(transactions: TransactionRow[], dateKeys: string[]): Map<string, Record<string, number>> {
  const deltas = new Map<string, Record<string, number>>();
  for (const row of transactions) {
    if (!row.assetId || row.signedQuantity === 0) {
      continue;
    }
    if (!deltas.has(row.date)) {
      deltas.set(row.date, {});
    }
    const bucket = deltas.get(row.date)!;
    bucket[row.assetId] = (bucket[row.assetId] ?? 0) + row.signedQuantity;
  }

  const snapshots = new Map<string, Record<string, number>>();
  const running: Record<string, number> = {};
  for (const date of dateKeys) {
    const delta = deltas.get(date);
    if (delta) {
      for (const [assetId, amount] of Object.entries(delta)) {
        running[assetId] = (running[assetId] ?? 0) + amount;
      }
    }
    snapshots.set(date, { ...running });
  }
  return snapshots;
}

function buildCashSeries(transactions: TransactionRow[], dateKeys: string[]): Map<string, number> {
  const byDate = new Map<string, number>();
  for (const row of transactions) {
    if (row.cashBalanceAmount === null) {
      continue;
    }
    byDate.set(row.date, row.cashBalanceAmount);
  }

  const out = new Map<string, number>();
  let running = 0;
  for (const date of dateKeys) {
    if (byDate.has(date)) {
      running = byDate.get(date) ?? running;
    }
    out.set(date, running);
  }
  return out;
}

function buildExternalFlowSeries(transactions: TransactionRow[], dateKeys: string[]): Map<string, number> {
  const flowByDate = new Map<string, number>();
  for (const row of transactions) {
    if (row.transactionCategory !== "deposits") {
      continue;
    }
    flowByDate.set(row.date, (flowByDate.get(row.date) ?? 0) + (row.transactionAmount ?? 0));
  }

  const out = new Map<string, number>();
  let running = 0;
  for (const date of dateKeys) {
    running += flowByDate.get(date) ?? 0;
    out.set(date, running);
  }
  return out;
}

function buildAllocation(
  holdings: Record<string, number>,
  mapping: SecurityMapRow[],
  latestCloseByTicker: Map<string, number>,
  latestFx: number,
  date: string
): AllocationRow[] {
  const mappingByAsset = new Map(mapping.map((row) => [row.assetId, row]));
  const rows: Array<Omit<AllocationRow, "weight">> = [];

  for (const [assetId, quantity] of Object.entries(holdings)) {
    const mappingRow = mappingByAsset.get(assetId);
    if (!mappingRow?.ticker) {
      continue;
    }
    const close = latestCloseByTicker.get(mappingRow.ticker);
    if (typeof close !== "number") {
      continue;
    }
    let valueEur = quantity * close * (mappingRow.priceScale || 1);
    if (mappingRow.assetCurrency.toUpperCase() === "USD") {
      if (typeof latestFx === "number" && latestFx > 0) {
        valueEur = valueEur / latestFx;
      }
    }
    rows.push({
      assetId,
      assetName: mappingRow.assetName,
      ticker: mappingRow.ticker,
      quantity,
      valueEur
    });
  }

  const total = rows.reduce((sum, row) => sum + row.valueEur, 0) || 1;
  return rows
    .map((row) => ({
      ...row,
      weight: row.valueEur / total
    }))
    .sort((left, right) => right.valueEur - left.valueEur);
}

function buildPortfolioRows(
  transactions: TransactionRow[],
  mapping: SecurityMapRow[],
  prices: PriceRow[],
  eurusd: PriceRow[]
): { portfolioRows: PortfolioRow[]; allocationRows: AllocationRow[] } {
  const start = parseDateKey(transactions[0]?.date ?? new Date().toISOString().slice(0, 10));
  const latestTxDate = parseDateKey(transactions[transactions.length - 1]?.date ?? new Date().toISOString().slice(0, 10));
  const today = new Date();
  const end = today > latestTxDate ? today : latestTxDate;
  const dateKeys = buildDateKeys(start, end);

  const holdingsByDate = buildDailyHoldings(transactions, dateKeys);
  const cashSeries = buildCashSeries(transactions, dateKeys);
  const externalFlowSeries = buildExternalFlowSeries(transactions, dateKeys);
  const priceLookup = buildPriceLookup(prices);
  const fxLookup = buildDateLookup(eurusd);
  const mappingByAsset = new Map(mapping.map((row) => [row.assetId, row]));

  const portfolioRows: PortfolioRow[] = [];
  const latestCloseByTicker = new Map<string, number>();
  let latestFx = 1;
  for (const date of dateKeys) {
    const holdings = holdingsByDate.get(date) ?? {};
    const cashBalanceEur = cashSeries.get(date) ?? 0;
    const netExternalFlowsEur = externalFlowSeries.get(date) ?? 0;
    const fxToday = fxLookup.get(date);
    if (typeof fxToday === "number" && fxToday > 0) {
      latestFx = fxToday;
    }

    let marketValueEur = 0;
    for (const [assetId, quantity] of Object.entries(holdings)) {
      const mappingRow = mappingByAsset.get(assetId);
      if (!mappingRow?.ticker) {
        continue;
      }
      const tickerSeries = priceLookup.get(mappingRow.ticker);
      const closeToday = tickerSeries?.get(date);
      if (typeof closeToday === "number") {
        latestCloseByTicker.set(mappingRow.ticker, closeToday);
      }
      const close = latestCloseByTicker.get(mappingRow.ticker);
      if (typeof close !== "number") {
        continue;
      }
      let value = quantity * close * (mappingRow.priceScale || 1);
      if (mappingRow.assetCurrency.toUpperCase() === "USD" && latestFx > 0) {
        value = value / latestFx;
      }
      marketValueEur += value;
    }

    const portfolioValueEur = cashBalanceEur + marketValueEur;
    const gainEur = portfolioValueEur - netExternalFlowsEur;
    const gainPct = netExternalFlowsEur !== 0 ? gainEur / netExternalFlowsEur : null;

    portfolioRows.push({
      date,
      cashBalanceEur,
      netExternalFlowsEur,
      marketValueEur,
      portfolioValueEur,
      gainEur,
      gainPct
    });
  }

  const latestDate = dateKeys[dateKeys.length - 1];
  const allocationRows = buildAllocation(holdingsByDate.get(latestDate) ?? {}, mapping, latestCloseByTicker, latestFx, latestDate);

  return { portfolioRows, allocationRows };
}

function buildMonthlyPerformanceRows(portfolioRows: PortfolioRow[]): MonthlyCategoryRow[] {
  const monthly = new Map<string, PortfolioRow>();
  for (const row of portfolioRows) {
    monthly.set(row.date.slice(0, 7), row);
  }

  const months = [...monthly.keys()].sort();
  return months.map((month, index) => {
    const current = monthly.get(month)!;
    const previousMonth = months[index - 1];
    const previous = previousMonth ? monthly.get(previousMonth) : null;
    const portfolioChange = previous ? current.portfolioValueEur - previous.portfolioValueEur : current.portfolioValueEur;
    const externalFlow = previous ? current.netExternalFlowsEur - previous.netExternalFlowsEur : current.netExternalFlowsEur;
    const marketResult = previous ? current.gainEur - previous.gainEur : current.gainEur;

    return {
      month,
      monthLabel: new Intl.DateTimeFormat("en", { month: "short", year: "numeric" }).format(new Date(`${month}-01T00:00:00.000Z`)),
      totals: {
        portfolio_change_eur: portfolioChange,
        external_flow_eur: externalFlow,
        market_result_eur: marketResult
      }
    };
  });
}

export async function buildPortfolioBundleFromWorkspace(): Promise<PortfolioBundle | null> {
  const csvText = await readImportedTransactionsCsv();
  if (!csvText) {
    return null;
  }
  const workspace = await readWorkspaceState();

  const transactions = parseTransactionsCsv(csvText);
  const securityMaster: SecurityMasterRow[] = buildSecurityMaster(transactions);
  const existingSecurityMap = await readSecurityMap();
  const securityMap = existingSecurityMap && existingSecurityMap.length > 0 ? effectiveMapping(securityMaster, existingSecurityMap) : buildInitialSecurityMap(securityMaster);

  const mappedTickers = [...new Set(securityMap.map((row) => row.ticker.trim()).filter(Boolean))];
  const start = parseDateKey(transactions[0]?.date ?? new Date().toISOString().slice(0, 10));
  const end = new Date();
  const prices = mappedTickers.length > 0 ? await fetchPrices(mappedTickers, start, end) : [];
  const eurusd = await fetchEurUsd(start, end);

  const { portfolioRows, allocationRows } = buildPortfolioRows(transactions, securityMap, prices, eurusd);
  const metrics = computeMetrics(transactions, portfolioRows);
  const monthlyPerformanceRows = buildMonthlyPerformanceRows(portfolioRows).slice(-12);

  return {
    sourceFileName: workspace?.sourceFileName ?? "local workspace",
    transactions,
    securityMaster,
    securityMap,
    effectiveMapping: securityMap,
    portfolioRows,
    monthlyPerformanceRows,
    allocationRows,
    metrics,
    prices,
    eurusd
  };
}
