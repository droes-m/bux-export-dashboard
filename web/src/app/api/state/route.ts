import { NextResponse } from "next/server";

import { readWorkspaceState } from "@/lib/storage";

export async function GET() {
  const state = await readWorkspaceState();

  if (!state) {
    return NextResponse.json({ error: "No workspace state found." }, { status: 404 });
  }

  return NextResponse.json(state);
}
