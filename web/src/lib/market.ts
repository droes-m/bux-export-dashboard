import type { PriceRow } from "@/lib/types";

function toUnixSeconds(date: Date): number {
  return Math.floor(date.getTime() / 1000);
}

function addDays(date: Date, days: number): Date {
  const out = new Date(date);
  out.setUTCDate(out.getUTCDate() + days);
  return out;
}

function dateKey(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function buildChartUrl(ticker: string, startDate: Date, endDate: Date): string {
  const period1 = toUnixSeconds(new Date(Date.UTC(startDate.getUTCFullYear(), startDate.getUTCMonth(), startDate.getUTCDate())));
  const period2 = toUnixSeconds(new Date(Date.UTC(endDate.getUTCFullYear(), endDate.getUTCMonth(), endDate.getUTCDate(), 23, 59, 59)));
  return `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(ticker)}?period1=${period1}&period2=${period2}&interval=1d&includePrePost=false&events=div%2Csplits`;
}

async function fetchChartSeries(ticker: string, startDate: Date, endDate: Date): Promise<PriceRow[]> {
  try {
    const response = await fetch(buildChartUrl(ticker, startDate, endDate), {
      headers: {
        "user-agent": "Mozilla/5.0"
      },
      cache: "no-store"
    });
    if (!response.ok) {
      return [];
    }
    const payload = (await response.json()) as {
      chart?: {
        result?: Array<{
          timestamp?: number[];
          indicators?: {
            quote?: Array<{ close?: Array<number | null> }>;
            adjclose?: Array<{ adjclose?: Array<number | null> }>;
          };
        }>;
      };
    };
    const result = payload.chart?.result?.[0];
    const timestamps = result?.timestamp ?? [];
    const quoteClose = result?.indicators?.quote?.[0]?.close ?? [];
    const adjClose = result?.indicators?.adjclose?.[0]?.adjclose ?? [];
    const closes = adjClose.length > 0 ? adjClose : quoteClose;

    return timestamps
      .map((timestamp, index) => ({
        date: dateKey(new Date(timestamp * 1000)),
        ticker,
        close: closes[index] ?? null
      }))
      .filter((row): row is PriceRow => typeof row.close === "number" && Number.isFinite(row.close));
  } catch {
    return [];
  }
}

export async function fetchPrices(tickers: string[], startDate: Date, endDate: Date): Promise<PriceRow[]> {
  const cleaned = [...new Set(tickers.map((ticker) => ticker.trim()).filter(Boolean))];
  if (cleaned.length === 0) {
    return [];
  }
  const results = await Promise.all(cleaned.map((ticker) => fetchChartSeries(ticker, startDate, addDays(endDate, 1))));
  return results.flat().sort((left, right) => left.ticker.localeCompare(right.ticker) || left.date.localeCompare(right.date));
}

export async function fetchEurUsd(startDate: Date, endDate: Date): Promise<PriceRow[]> {
  const rows = await fetchPrices(["EURUSD=X"], startDate, endDate);
  return rows.map((row) => ({ ...row, ticker: "EURUSD=X" }));
}
