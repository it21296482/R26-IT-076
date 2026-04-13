import { Link } from "react-router-dom";

function BrandLogo({ to = "/", light = false, compact = false }) {
  return (
    <Link className="flex min-w-0 items-center gap-3" to={to}>
      <div className={`logo-frame ${light ? "logo-frame-light" : ""} ${compact ? "h-10 w-10" : "h-12 w-12"} shrink-0`}>
        <img alt="CSE Insight Generator logo" className="h-full w-full object-cover" src="/assets/cse-logo-source.png" />
      </div>
      <div className="min-w-0">
        <p className={`text-[10px] font-semibold uppercase tracking-[0.28em] ${light ? "text-blue-100/80" : "text-[#1d4aa8]"}`}>
          AI Market Intelligence
        </p>
        <p className={`truncate text-sm font-semibold md:text-base ${light ? "text-white" : "text-slate-900"}`}>
          CSE Insight Generator
        </p>
      </div>
    </Link>
  );
}

export default BrandLogo;
