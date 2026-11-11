import type { ReactNode } from "react";

export function DeltaIndicator({ value, unavailable = "昨日无数据" }: { value?: number | null; unavailable?: string }) {
  if (value === undefined || value === null) return <small className="rate-delta unavailable">{unavailable}</small>;
  const normalized = Math.abs(value) < 0.005 ? 0 : value;
  const className = normalized > 0 ? "increase" : normalized < 0 ? "decrease" : "unchanged";
  const prefix = normalized > 0 ? "↑ +" : normalized < 0 ? "↓ " : "→ ";
  return <small className={`rate-delta ${className}`}>较昨日 {prefix}{normalized.toFixed(1)} 个百分点</small>;
}

export function OwnedProductStateCard({ label, className, rate, rateLabel, detail, change, surface }: {
  label: string; className: string; rate?: string | null; rateLabel?: string; detail: ReactNode;
  change?: ReactNode; surface?: boolean;
}) {
  return <span className={`${surface ? "owned-product-surface" : "owned-product-state"} ${className}`}>
    <span className="owned-product-state-head"><b>{label}</b>
      {rate != null && <strong className="owned-product-rate" aria-label={rateLabel ? `${rateLabel} ${rate}` : undefined}>{rate}</strong>}
    </span>
    <small>{detail}</small>{change}
  </span>;
}

export function OwnedProductAverageCard({ rate, detail, change, surface }: {
  rate: number | null; detail: ReactNode; change?: ReactNode; surface?: boolean;
}) {
  const display = rate?.toFixed(1);
  const state = display === undefined ? "empty" : Number(display) === 0 ? "zero" : "";
  const className = ["owned-product-model-average", surface && "owned-product-surface", state].filter(Boolean).join(" ");
  return <span className={className}><b>{display === undefined ? "—" : `${display}%`}</b><small>{detail}</small>{change}</span>;
}
