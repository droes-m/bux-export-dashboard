import type { AssetDrilldownData, AssetDrilldownPoint, PortfolioBundle, PriceRow, TransactionRow } from "@/lib/types";

function buildDateKeys(startDate: string, endDate: string): string[] {
  const start = new Date(`${startDate}T00:00:00.000Z`);
  const end = new Date(`${endDate}T00:00:00.000Z`);
  const out: string[] = [];
  for (let cursor = start; cursor <= end; cursor = new Date(cursor.getTime() + 24 * 60 * 60 * 1000)) {
    out.push(cursor.toISOString().slice(0, 10));
  }
  return out;
}

function buildDateLookup(rows: PriceRow[], ticker: string): Map<string, number> {
  const lookup = new Map<string, number>();
  for (const row of rows) {
    if (row.ticker === ticker) {
      lookup.set(row.date, row.close);
    }
  }
  return lookup;
}

function buildFxLookup(rows: PriceRow[]): Map<string, number> {
  const lookup = new Map<string, number>();
  for (const row of rows) {
    lookup.set(row.date, row.close);
  }
  return lookup;
}

function openPositionCostBasis(trades: TransactionRow[]): { quantity: number; averageCostOriginal: number | null } {
  let quantity = 0;
  let cost = 0;

  for (const trade of trades.slice().sort((left, right) => left.transactionTime.localeCompare(right.transactionTime))) {
    const q = trade.signedQuantity ?? 0;
    const price = trade.assetPrice;
    if (q > 0 && typeof price === "number") {
      quantity += q;
      cost += q * price;
    } else if (q < 0 && quantity > 0) {
      const sellQty = Math.min(-q, quantity);
      const avgCost = quantity > 0 ? cost / quantity : 0;
      cost -= avgCost * sellQty;
      quantity -= sellQty;
      if (quantity <= 1e-12) {
        quantity = 0;
        cost = 0;
      }
    }
  }

  return {
    quantity,
    averageCostOriginal: quantity > 0 ? cost / quantity : null
  };
}

function buildAssetTimeline(
  assetTransactions: TransactionRow[],
  unitPriceByDate: Map<string, number>,
  fxByDate: Map<string, number>,
  assetCurrency: string,
  priceScale: number,
  startDate: string,
  endDate: string
): AssetDrilldownPoint[] {
  const dateKeys = buildDateKeys(startDate, endDate);
  const deltaByDate = new Map<string, number>();
  for (const tx of assetTransactions) {
    deltaByDate.set(tx.date, (deltaByDate.get(tx.date) ?? 0) + (tx.signedQuantity ?? 0));
  }

  const out: AssetDrilldownPoint[] = [];
  let quantity = 0;
  let latestUnitPriceOriginal: number | null = null;
  let latestFx: number | null = null;

  for (const date of dateKeys) {
    quantity += deltaByDate.get(date) ?? 0;
    const close = unitPriceByDate.get(date);
    if (typeof close === "number") {
      latestUnitPriceOriginal = close;
    }
    const fx = fxByDate.get(date);
    if (typeof fx === "number" && fx > 0) {
      latestFx = fx;
    }

    let unitPriceEur: number | null = null;
    if (typeof latestUnitPriceOriginal === "number") {
      unitPriceEur = latestUnitPriceOriginal * priceScale;
      if (assetCurrency.toUpperCase() === "USD" && typeof latestFx === "number" && latestFx > 0) {
        unitPriceEur = unitPriceEur / latestFx;
      }
    }

    out.push({
      date,
      quantity,
      unitPriceEur,
      marketValueEur: quantity * (unitPriceEur ?? 0)
    });
  }

  return out;
}

export function buildAssetDrilldown(bundle: PortfolioBundle, assetId: string | null | undefined): AssetDrilldownData | null {
  const mapping = bundle.effectiveMapping.find((row) => row.assetId === assetId) ?? bundle.securityMap.find((row) => row.assetId === assetId);
  if (!mapping) {
    return null;
  }

  const assetTransactions = bundle.transactions
    .filter((row) => row.assetId === assetId)
    .slice()
    .sort((left, right) => left.transactionTime.localeCompare(right.transactionTime));

  if (assetTransactions.length === 0) {
    return null;
  }

  const buyRows = assetTransactions.filter((row) => row.transferType === "ASSET_TRADE_BUY");
  const sellRows = assetTransactions.filter((row) => row.transferType === "ASSET_TRADE_SELL");
  const { quantity: openQuantity, averageCostOriginal: openAverageCostOriginal } = openPositionCostBasis(assetTransactions);
  const realizedPnlEur = sellRows.reduce((total, row) => total + (row.profitAndLossAmount ?? 0), 0);

  const unitPriceByDate = buildDateLookup(bundle.prices, mapping.ticker);
  const fxByDate = buildFxLookup(bundle.eurusd);
  const startDate = assetTransactions[0].date;
  const endDate = bundle.portfolioRows[bundle.portfolioRows.length - 1]?.date ?? startDate;
  const timeline = buildAssetTimeline(
    assetTransactions,
    unitPriceByDate,
    fxByDate,
    mapping.assetCurrency,
    mapping.priceScale || 1,
    startDate,
    endDate
  );
  const latest = timeline[timeline.length - 1];
  const latestRawUnitPrice = bundle.prices
    .slice()
    .reverse()
    .find((row) => row.ticker === mapping.ticker)?.close ?? null;
  const latestFx = bundle.eurusd.slice().reverse().find((row) => typeof row.close === "number")?.close ?? null;

  let latestUnitPriceEur: number | null = null;
  const latestUnitPriceOriginal = typeof latestRawUnitPrice === "number" ? latestRawUnitPrice * (mapping.priceScale || 1) : null;
  if (typeof latestUnitPriceOriginal === "number") {
    latestUnitPriceEur = latestUnitPriceOriginal;
    if (mapping.assetCurrency.toUpperCase() === "USD" && typeof latestFx === "number" && latestFx > 0) {
      latestUnitPriceEur = latestUnitPriceEur / latestFx;
    }
  }

  const averageBuyPriceOriginal =
    buyRows.length > 0
      ? buyRows.reduce((sum, row) => sum + (row.assetPrice ?? 0) * (row.assetQuantity ?? 0), 0) /
        Math.max(
          buyRows.reduce((sum, row) => sum + (row.assetQuantity ?? 0), 0),
          1
        )
      : null;

  const currentAllocation = bundle.allocationRows.find((row) => row.assetId === assetId);
  const currentValueEur = currentAllocation?.valueEur ?? latest?.marketValueEur ?? 0;
  const marketValueTotal = bundle.metrics.marketValueEur || 1;
  const currentWeightPct = bundle.metrics.marketValueEur > 0 ? currentValueEur / marketValueTotal : 0;

  let openAverageCostEur: number | null = openAverageCostOriginal;
  if (typeof openAverageCostOriginal === "number" && mapping.assetCurrency.toUpperCase() === "USD" && typeof latestFx === "number" && latestFx > 0) {
    openAverageCostEur = openAverageCostOriginal / latestFx;
  }

  let unrealizedPnlEur = 0;
  if (typeof openAverageCostEur === "number" && openQuantity > 0 && typeof latestUnitPriceEur === "number") {
    unrealizedPnlEur = (latestUnitPriceEur - openAverageCostEur) * openQuantity;
  }

  return {
    summary: {
      assetId: mapping.assetId,
      assetName: mapping.assetName,
      ticker: mapping.ticker,
      assetCurrency: mapping.assetCurrency,
      priceScale: mapping.priceScale,
      currentQuantity: latest?.quantity ?? openQuantity,
      currentValueEur,
      currentWeightPct,
      realizedPnlEur,
      unrealizedPnlEur,
      openQuantity,
      openAverageCostOriginal,
      openAverageCostEur,
      averageBuyPriceOriginal,
      latestUnitPriceOriginal,
      latestUnitPriceEur
    },
    points: timeline,
    transactions: assetTransactions
  };
}
