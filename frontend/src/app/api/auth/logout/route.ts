import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const BACKEND_URL =
  process.env.FASTAPI_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

export async function POST() {
  try {
    const cookieStore = await cookies();
    const sessionCookie = cookieStore.get("campusops_session");

    if (sessionCookie?.value) {
      // Forward logout notification to backend
      try {
        await fetch(`${BACKEND_URL}/api/auth/logout`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${sessionCookie.value}`,
          },
        });
      } catch {
        // Continue clearing client cookie even if backend is unreachable
      }
    }

    cookieStore.delete("campusops_session");
    return NextResponse.json({ message: "Logged out successfully" });
  } catch {
    return NextResponse.json({ message: "Logged out" });
  }
}

