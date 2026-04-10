import type { SecurityMapRow, SecurityMasterRow } from "@/lib/types";

type DefaultTicker = [ticker: string, exchange: string, source: string, confidence: string, priceScale?: number];

const DEFAULT_NAME_TO_TICKER: Record<string, DefaultTicker> = {
  "Alphabet A": ["GOOGL", "NASDAQ", "seed_default", "medium"],
  Apple: ["AAPL", "NASDAQ", "seed_default", "high"],
  Duolingo: ["DUOL", "NASDAQ", "seed_default", "high"],
  "Enphase Energy": ["ENPH", "NASDAQ", "seed_default", "high"],
  NVIDIA: ["NVDA", "NASDAQ", "seed_default", "high"],
  Qualcomm: ["QCOM", "NASDAQ", "seed_default", "high"],
  Tesla: ["TSLA", "NASDAQ", "seed_default", "high"],
  "Vanguard S&P 500": ["VUSA.AS", "Euronext Amsterdam", "seed_default", "medium"],
  "iShares Global Clean Energy": ["IQQH.DE", "XETRA", "seed_default", "medium"],
  "iShares Automation & Robotics": ["2B76.DE", "XETRA", "seed_default", "medium"]
};

const DEFAULT_ISIN_TO_TICKER: Record<string, DefaultTicker> = {
  BE0974313455: ["ECONB.BR", "Brussels", "seed_isin", "high", 1.0],
  IE00BJXRZJ40: ["CYBP.L", "London", "seed_isin", "medium", 1.0],
  IE00B8GKDB10: ["VHYL.AS", "Amsterdam", "seed_isin", "high", 1.0],
  IE00B1XNHC34: ["IQQH.DE", "XETRA", "seed_isin", "medium", 1.0],
  IE000I8KRLL9: ["SEC0.DE", "XETRA", "seed_isin", "high", 1.0],
  IE00BQN1K786: ["CEMR.DE", "XETRA", "seed_isin", "medium", 1.0]
};

const EUR_TICKER_SUFFIXES = [".DE", ".AS", ".PA", ".BR"];

export function buildInitialSecurityMap(securityMaster: SecurityMasterRow[]): SecurityMapRow[] {
  return securityMaster
    .map((row) => {
      const existingByIsin = DEFAULT_ISIN_TO_TICKER[row.assetId];
      const existingByName = DEFAULT_NAME_TO_TICKER[row.assetName];
      const match = existingByIsin ?? existingByName;

      const ticker = match?.[0] ?? "";
      const exchange = match?.[1] ?? "";
      const source = match?.[2] ?? "pending";
      const confidence = match?.[3] ?? "unmapped";
      const priceScale = match?.[4] ?? 1.0;

      return {
        assetId: row.assetId,
        assetName: row.assetName,
        assetCurrency: row.assetCurrency ?? "",
        ticker,
        priceScale,
        exchange,
        source,
        confidence,
        notes: ""
      };
    })
    .map((row) => inferCurrencyFromTicker(row));
}

export function mergeSecurityMap(securityMaster: SecurityMasterRow[], existing: SecurityMapRow[] | null): SecurityMapRow[] {
  const current = new Map<string, SecurityMapRow>();
  for (const row of existing ?? []) {
    current.set(row.assetId, row);
  }

  return securityMaster
    .map((masterRow) => {
      const currentRow = current.get(masterRow.assetId);
      if (currentRow) {
        return inferCurrencyFromTicker({
          ...currentRow,
          assetName: masterRow.assetName,
          assetCurrency: currentRow.assetCurrency || masterRow.assetCurrency
        });
      }
      return inferCurrencyFromTicker({
        assetId: masterRow.assetId,
        assetName: masterRow.assetName,
        assetCurrency: masterRow.assetCurrency,
        ticker: "",
        priceScale: 1,
        exchange: "",
        source: "pending",
        confidence: "unmapped",
        notes: ""
      });
    })
    .sort((left, right) => left.assetName.localeCompare(right.assetName));
}

export function inferCurrencyFromTicker(row: SecurityMapRow): SecurityMapRow {
  const ticker = row.ticker.trim().toUpperCase();
  if (row.assetCurrency.trim()) {
    return row;
  }
  if (!EUR_TICKER_SUFFIXES.some((suffix) => ticker.endsWith(suffix))) {
    return row;
  }
  const notes = row.notes.toLowerCase().includes("currency inferred from ticker suffix")
    ? row.notes
    : [row.notes, "currency inferred from ticker suffix"].filter(Boolean).join("; ");
  return {
    ...row,
    assetCurrency: "EUR",
    source: row.source || "ticker_suffix_infer",
    confidence: row.confidence || "low",
    notes
  };
}

export function effectiveMapping(securityMaster: SecurityMasterRow[], existing: SecurityMapRow[] | null): SecurityMapRow[] {
  const merged = mergeSecurityMap(securityMaster, existing);
  return merged.map((row) => {
    const defaultByIsin = DEFAULT_ISIN_TO_TICKER[row.assetId];
    const defaultByName = DEFAULT_NAME_TO_TICKER[row.assetName];
    if (row.ticker) {
      return row;
    }
    const match = defaultByIsin ?? defaultByName;
    if (!match) {
      return row;
    }
    return inferCurrencyFromTicker({
      ...row,
      ticker: match[0],
      exchange: match[1],
      source: match[2],
      confidence: match[3],
      priceScale: match[4] ?? 1.0
    });
  });
}
