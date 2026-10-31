import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const BACKEND_URL =
  process.env.FASTAPI_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

export async function POST() {
  try {
    const cookieStore = await cookies();
    const sessionToken = cookieStore.get("campusops_session")?.value;

    if (!sessionToken) {
      return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
    }

    const response = await fetch(`${BACKEND_URL}/api/knowledge/seed-sample`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${sessionToken}`,
      },
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal server error";
    return NextResponse.json(
      { detail: `Failed to seed sample knowledge: ${message}` },
      { status: 502 }
    );
  }
}

