/** Stable API dates, independent of browser locale punctuation and order. */
export function beijingDate(now = new Date()) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Shanghai", calendar: "gregory", numberingSystem: "latn",
    year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(now);
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

export function beijingMonth(now = new Date()) {
  return beijingDate(now).slice(0, 7);
}
