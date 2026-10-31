import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const BACKEND_URL =
  process.env.FASTAPI_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const cookieStore = await cookies();
    const sessionToken = cookieStore.get("campusops_session")?.value;

    if (!sessionToken) {
      return NextResponse.json(
        { detail: "Authentication required to access incident" },
        { status: 401 }
      );
    }

    const response = await fetch(`${BACKEND_URL}/api/v1/incidents/${id}`, {
      headers: {
        Authorization: `Bearer ${sessionToken}`,
      },
      cache: "no-store",
    });

    const data = await response.json();
    if (!response.ok) {
      return NextResponse.json(
        { detail: typeof data.detail === "string" ? data.detail : "Failed to fetch incident" },
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

