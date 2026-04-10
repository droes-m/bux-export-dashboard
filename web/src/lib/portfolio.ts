import Papa from "papaparse";

import type {
  BasicMetrics,
  DashboardMetrics,
  MonthlyCategoryRow,
  PortfolioRow,
  SecurityMasterRow,
  TransactionRow
} from "@/lib/types";

const REQUIRED_COLUMNS = ["Transaction Time (CET)", "Asset Id", "Asset Name"] as const;

function toNumber(value: unknown): number | null {
  if (value === null || value === undefined) {
    return null;
  }
  const text = String(value).trim();
  if (!text) {
    return null;
  }
  const parsed = Number(text.replace(",", "."));
  return Number.isFinite(parsed) ? parsed : null;
}

function toText(value: unknown): string {
  return String(value ?? "").trim();
}

function toDateKey(raw: string): string {
  const text = raw.slice(0, 10);
  return text;
}

function monthLabel(month: string): string {
  const [year, monthPart] = month.split("-");
  const monthIndex = Number(monthPart) - 1;
  const label = new Intl.DateTimeFormat("en", { month: "short" }).format(new Date(Date.UTC(Number(year), monthIndex, 1)));
  return `${label} ${year}`;
}

export function parseTransactionsCsv(csvText: string): TransactionRow[] {
  const parsed = Papa.parse<Record<string, string>>(csvText, {
    header: true,
    skipEmptyLines: true
  });

  if (parsed.errors.length > 0) {
    throw new Error(parsed.errors[0]?.message ?? "Could not parse CSV");
  }

  const rows = parsed.data;
  for (const column of REQUIRED_COLUMNS) {
    if (!(column in (rows[0] ?? {}))) {
      throw new Error(`Missing required column: ${column}`);
    }
  }

  return rows
    .map((row) => {
      const transactionTime = toText(row["Transaction Time (CET)"]);
      return {
        transactionTime,
        transactionCategory: toText(row["Transaction Category"]),
        transactionType: toText(row["Transaction Type"]),
        transferType: toText(row["Transfer Type"]),
        transactionAmount: toNumber(row["Transaction Amount"]),
        transactionCurrency: toText(row["Transaction Currency"]),
        cashBalanceAmount: toNumber(row["Cash Balance Amount"]),
        assetId: toText(row["Asset Id"]),
        assetName: toText(row["Asset Name"]),
        assetQuantity: toNumber(row["Asset Quantity"]),
        assetPrice: toNumber(row["Asset Price"]),
        assetCurrency: toText(row["Asset Currency"]),
        exchangeRate: toNumber(row["Exchange Rate"]),
        profitAndLossAmount: toNumber(row["Profit And Loss Amount"]),
        dividendNetAmount: toNumber(row["Dividend Net Amount"]),
        dividendTaxAmount: toNumber(row["Dividend Tax Amount"]),
        date: toDateKey(transactionTime),
        month: transactionTime.slice(0, 7),
        signedQuantity: row["Transfer Type"] === "ASSET_TRADE_BUY" ? toNumber(row["Asset Quantity"]) ?? 0 : row["Transfer Type"] === "ASSET_TRADE_SELL" ? -(toNumber(row["Asset Quantity"]) ?? 0) : 0
      };
    })
    .sort((left, right) => left.transactionTime.localeCompare(right.transactionTime));
}

export function buildSecurityMaster(transactions: TransactionRow[]): SecurityMasterRow[] {
  const seen = new Map<string, SecurityMasterRow>();

  for (const row of transactions) {
    if (!row.assetId) {
      continue;
    }
    if (!seen.has(row.assetId)) {
      seen.set(row.assetId, {
        assetId: row.assetId,
        assetName: row.assetName,
        assetCurrency: row.assetCurrency
      });
    }
  }

  return [...seen.values()].sort((left, right) => left.assetName.localeCompare(right.assetName));
}

export function computeBasicMetrics(transactions: TransactionRow[]): BasicMetrics {
  const latestCashBalanceEur = transactions.reduce((latest, row) => (row.cashBalanceAmount !== null ? row.cashBalanceAmount : latest), 0);
  const depositTotalEur = sumWhere(transactions, (row) => row.transactionCategory === "deposits");
  const realizedPnlEur = sumWhere(transactions, (row) => row.transactionType === "Sell Trade", "profitAndLossAmount");
  const dividendsNetEur = sumField(transactions, "dividendNetAmount");
  const feesEur = sumWhere(transactions, (row) => row.transactionCategory === "fees");
  const taxesEur = sumWhere(transactions, (row) => row.transactionCategory === "tax");
  const interestEur = sumWhere(transactions, (row) => row.transactionCategory === "interest");

  return {
    transactionCount: transactions.length,
    depositTotalEur,
    netExternalFlowsEur: depositTotalEur,
    realizedPnlEur,
    dividendsNetEur,
    interestEur,
    feesEur,
    taxesEur,
    latestCashBalanceEur
  };
}

export function computeMetrics(transactions: TransactionRow[], portfolioRows: PortfolioRow[]): DashboardMetrics {
  const latest = portfolioRows[portfolioRows.length - 1] ?? {
    portfolioValueEur: 0,
    netExternalFlowsEur: 0,
    gainEur: 0,
    gainPct: null,
    cashBalanceEur: 0,
    marketValueEur: 0
  };

  const realizedPnlEur = transactions
    .filter((row) => row.transactionType === "Sell Trade")
    .reduce((total, row) => total + (row.profitAndLossAmount ?? 0), 0);
  const feesEur = transactions.filter((row) => row.transactionCategory === "fees").reduce((total, row) => total + (row.transactionAmount ?? 0), 0);
  const taxesEur = transactions.filter((row) => row.transactionCategory === "tax").reduce((total, row) => total + (row.transactionAmount ?? 0), 0);
  const dividendsNetEur = transactions.reduce((total, row) => total + (row.dividendNetAmount ?? 0), 0);
  const interestEur = transactions.filter((row) => row.transactionCategory === "interest").reduce((total, row) => total + (row.transactionAmount ?? 0), 0);
  const netExternalFlowsEur = latest.netExternalFlowsEur;
  const gainAfterAllCashflowsEur = latest.portfolioValueEur - netExternalFlowsEur;
  const gainExFeesTaxesEur = gainAfterAllCashflowsEur - feesEur - taxesEur;

  return {
    portfolioValueEur: latest.portfolioValueEur,
    netDepositsEur: netExternalFlowsEur,
    netExternalFlowsEur,
    gainEur: gainAfterAllCashflowsEur,
    gainAfterAllCashflowsEur,
    gainExFeesTaxesEur,
    gainPct: latest.gainPct ?? 0,
    cashBalanceEur: latest.cashBalanceEur,
    marketValueEur: latest.marketValueEur,
    realizedPnlEur,
    feesEur,
    taxesEur,
    dividendsNetEur,
    interestEur
  };
}

function sumField(transactions: TransactionRow[], field: keyof TransactionRow): number {
  return transactions.reduce((total, row) => total + (typeof row[field] === "number" && Number.isFinite(row[field] as number) ? (row[field] as number) : 0), 0);
}

function sumWhere(transactions: TransactionRow[], predicate: (row: TransactionRow) => boolean, field: keyof TransactionRow = "transactionAmount"): number {
  return transactions.reduce((total, row) => {
    if (!predicate(row)) {
      return total;
    }
    const value = row[field];
    return total + (typeof value === "number" && Number.isFinite(value) ? value : 0);
  }, 0);
}

export function buildMonthlyCategoryRows(transactions: TransactionRow[]): MonthlyCategoryRow[] {
  const monthMap = new Map<string, Record<string, number>>();

  for (const row of transactions) {
    const month = row.month;
    if (!monthMap.has(month)) {
      monthMap.set(month, {});
    }
    const bucket = monthMap.get(month)!;
    const category = row.transactionCategory || "uncategorized";
    bucket[category] = (bucket[category] ?? 0) + (row.transactionAmount ?? 0);
  }

  return [...monthMap.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([month, totals]) => ({
      month,
      monthLabel: monthLabel(month),
      totals
    }));
}

export function formatEuro(value: number): string {
  const sign = value < 0 ? "-" : "";
  const absolute = Math.abs(value);
  if (absolute >= 1_000_000) {
    return `${sign}EUR ${(absolute / 1_000_000).toFixed(2)}M`;
  }
  if (absolute >= 1_000) {
    return `${sign}EUR ${(absolute / 1_000).toFixed(2)}k`;
  }
  return `${sign}EUR ${absolute.toFixed(2)}`;
}
