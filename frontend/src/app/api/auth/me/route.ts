import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const BACKEND_URL =
  process.env.FASTAPI_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

export async function GET() {
  try {
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("campusops_session");

    if (!sessionCookie || !sessionCookie.value) {
      return NextResponse.json({ user: null }, { status: 401 });
    }

    const response = await fetch(`${BACKEND_URL}/api/auth/me`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${sessionCookie.value}`,
      },
    });

    if (!response.ok) {
      // Token expired or invalid: clear invalid cookie
      cookieStore.delete("campusops_session");
      return NextResponse.json({ user: null }, { status: 401 });
    }

    const user = await response.json();
    return NextResponse.json({ user });
  } catch {
    return NextResponse.json({ user: null }, { status: 502 });
  }
}

