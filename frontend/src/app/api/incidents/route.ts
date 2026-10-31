import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const BACKEND_URL =
  process.env.FASTAPI_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

export async function GET() {
  try {
    const cookieStore = await cookies();
    const sessionToken = cookieStore.get("campusops_session")?.value;

    if (!sessionToken) {
      return NextResponse.json(
        { detail: "Authentication required to access incident records" },
        { status: 401 }
      );
    }

    const response = await fetch(`${BACKEND_URL}/api/v1/incidents`, {
      headers: {
        Authorization: `Bearer ${sessionToken}`,
      },
      cache: "no-store",
    });

    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json(
        { detail: typeof data.detail === "string" ? data.detail : "Failed to fetch incidents" },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal server error";
    return NextResponse.json(
      { detail: `Failed to connect to backend incident service: ${message}` },
      { status: 502 }
    );
  }
}

export async function POST(req: Request) {
  try {
    const cookieStore = await cookies();
    const sessionToken = cookieStore.get("campusops_session")?.value;

    if (!sessionToken) {
      return NextResponse.json(
        { detail: "Authentication required to seed demo incident" },
        { status: 401 }
      );
    }

    let scenarioId: string | null = null;
    try {
      const url = new URL(req.url);
      scenarioId = url.searchParams.get("scenario_id");
      if (!scenarioId) {
        const body = await req.json().catch(() => null);
        scenarioId = body?.scenario_id || null;
      }
    } catch {
      // ignore parsing failure, fallback to default scenario
    }

    const endpoint = scenarioId
      ? `${BACKEND_URL}/api/v1/incidents/seed-demo?scenario_id=${encodeURIComponent(scenarioId)}`
      : `${BACKEND_URL}/api/v1/incidents/seed-demo`;

    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${sessionToken}`,
      },
    });

    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json(
        { detail: typeof data.detail === "string" ? data.detail : "Failed to seed demo incident" },
        { status: response.status }
      );
    }

    return NextResponse.json(data, { status: 201 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal server error";
    return NextResponse.json(
      { detail: `Failed to connect to incident service: ${message}` },
      { status: 502 }
    );
  }
}
