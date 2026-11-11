import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { Dashboard } from "./Dashboard";

export default async function Home() {
  const requestHeaders = await headers();
  const cookie = requestHeaders.get("cookie");
  let employee = false;
  if (cookie) {
    try {
      const identity = await fetch("http://127.0.0.1:19766/auth", {
        headers: { Cookie: cookie, "X-Original-URI": "/geo_monitor/api/geo-capture/employee-videos" },
        cache: "no-store",
        signal: AbortSignal.timeout(3000),
      });
      employee = identity.status === 204 && identity.headers.get("X-Geo-Video-Only") === "1";
    } catch {
      // The gateway checks public access. Keep the existing local dashboard available.
    }
  }
  if (employee) redirect("/geo_monitor/employee-videos");
  return <Dashboard />;
}
