/** The VPS mounts this application below /geo_monitor; LAN keeps root URLs. */
export function dashboardBasePath() {
  if (typeof window === "undefined") return "";
  return /^\/geo_monitor(?:\/|$)/.test(window.location.pathname) ? "/geo_monitor" : "";
}
