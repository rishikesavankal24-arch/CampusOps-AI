import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const BACKEND_URL =
  process.env.FASTAPI_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const cookieStore = await cookies();
    const sessionToken = cookieStore.get("campusops_session")?.value;

    if (!sessionToken) {
      return NextResponse.json(
        { detail: "Authentication required to execute recovery action" },
        { status: 401 }
      );
    }

    let body = {};
    try {
      body = await request.json();
    } catch {
      // Empty body is valid
    }

    const response = await fetch(`${BACKEND_URL}/api/v1/incidents/${id}/investigation/execute-recovery`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${sessionToken}`,
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json(
        { detail: typeof data.detail === "string" ? data.detail : "Recovery execution failed" },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal server error";
    return NextResponse.json(
      { detail: `Failed to connect to recovery service: ${message}` },
      { status: 502 }
    );
  }
}

