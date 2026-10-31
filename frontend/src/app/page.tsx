import { redirect } from "next/navigation";
import { cookies } from "next/headers";

export const dynamic = "force-dynamic";

export default async function Home() {
  const cookieStore = await cookies();
  const session = cookieStore.get("campusops_session")?.value;

  if (session) {
    redirect("/dashboard");
  } else {
    redirect("/login");
  }
}
