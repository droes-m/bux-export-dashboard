export type TransactionRow = {
  transactionTime: string;
  transactionCategory: string;
  transactionType: string;
  transferType: string;
  transactionAmount: number | null;
  transactionCurrency: string;
  cashBalanceAmount: number | null;
  assetId: string;
  assetName: string;
  assetQuantity: number | null;
  assetPrice: number | null;
  assetCurrency: string;
  exchangeRate: number | null;
  profitAndLossAmount: number | null;
  dividendNetAmount: number | null;
  dividendTaxAmount: number | null;
  date: string;
  month: string;
  signedQuantity: number;
};

export type PriceRow = {
  date: string;
  ticker: string;
  close: number;
};

export type SecurityMasterRow = {
  assetId: string;
  assetName: string;
  assetCurrency: string;
};

export type SecurityMapRow = {
  assetId: string;
  assetName: string;
  assetCurrency: string;
  ticker: string;
  priceScale: number;
  exchange: string;
  source: string;
  confidence: string;
  notes: string;
};

export type MonthlyCategoryRow = {
  month: string;
  monthLabel: string;
  totals: Record<string, number>;
};

export type PortfolioRow = {
  date: string;
  cashBalanceEur: number;
  netExternalFlowsEur: number;
  marketValueEur: number;
  portfolioValueEur: number;
  gainEur: number;
  gainPct: number | null;
};

export type AllocationRow = {
  assetId: string;
  assetName: string;
  ticker: string;
  quantity: number;
  valueEur: number;
  weight: number;
};

export type DashboardMetrics = {
  portfolioValueEur: number;
  netDepositsEur: number;
  netExternalFlowsEur: number;
  gainEur: number;
  gainAfterAllCashflowsEur: number;
  gainExFeesTaxesEur: number;
  gainPct: number;
  cashBalanceEur: number;
  marketValueEur: number;
  realizedPnlEur: number;
  feesEur: number;
  taxesEur: number;
  dividendsNetEur: number;
  interestEur: number;
};

export type BasicMetrics = {
  transactionCount: number;
  depositTotalEur: number;
  netExternalFlowsEur: number;
  realizedPnlEur: number;
  dividendsNetEur: number;
  interestEur: number;
  feesEur: number;
  taxesEur: number;
  latestCashBalanceEur: number;
};

export type WorkspaceState = {
  sourceFileName: string;
  importedAt: string;
  transactionCount: number;
  metrics: BasicMetrics;
  monthlyCategoryRows: MonthlyCategoryRow[];
};

export type PortfolioBundle = {
  sourceFileName: string;
  transactions: TransactionRow[];
  securityMaster: SecurityMasterRow[];
  securityMap: SecurityMapRow[];
  effectiveMapping: SecurityMapRow[];
  portfolioRows: PortfolioRow[];
  monthlyPerformanceRows: MonthlyCategoryRow[];
  allocationRows: AllocationRow[];
  metrics: DashboardMetrics;
  prices: PriceRow[];
  eurusd: PriceRow[];
};

export type AssetDrilldownPoint = {
  date: string;
  quantity: number;
  marketValueEur: number;
  unitPriceEur: number | null;
};

export type AssetDrilldownSummary = {
  assetId: string;
  assetName: string;
  ticker: string;
  assetCurrency: string;
  priceScale: number;
  currentQuantity: number;
  currentValueEur: number;
  currentWeightPct: number;
  realizedPnlEur: number;
  unrealizedPnlEur: number;
  openQuantity: number;
  openAverageCostOriginal: number | null;
  openAverageCostEur: number | null;
  averageBuyPriceOriginal: number | null;
  latestUnitPriceOriginal: number | null;
  latestUnitPriceEur: number | null;
};

export type AssetDrilldownData = {
  summary: AssetDrilldownSummary;
  points: AssetDrilldownPoint[];
  transactions: TransactionRow[];
};
