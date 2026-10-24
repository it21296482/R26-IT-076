import { useLanguage } from "../context/languageStore";
import { progressLabel } from "../lib/analysisProgress";

export default function AnalysisProgress({ progress, analyzing, progressDisconnected }) {
  const { t } = useLanguage();
  if (!progress) return null;
  return (
    <div className="mt-5 rounded-2xl border border-blue-100 bg-blue-50 p-4" role="status" aria-live="polite">
    <div className="flex items-center justify-between gap-3 text-sm font-semibold text-slate-800">
    <span>{t(progressLabel(progress.stage))}</span><span>{Math.round(progress.percent)}%</span>
    </div>
    <div className="mt-3 h-2 overflow-hidden rounded-full bg-blue-100" role="progressbar" aria-label={t("Analysis progress")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress.percent)}>
    <div className="h-full rounded-full bg-blue-600 transition-[width] duration-300 motion-reduce:transition-none" style={{ width: `${progress.percent}%` }} />
    </div>
    {analyzing && progress.stage === "sequence_training" && <p className="mt-2 text-xs text-slate-600">{t("Training pass {pass}: epoch {epoch} of {total}", { pass: progress.training_pass, epoch: progress.epoch, total: progress.epochs })}</p>}
    <p className="mt-2 text-xs leading-5 text-slate-500">{t("Progress follows completed analysis stages, not an estimated countdown.")}</p>
    {analyzing && progressDisconnected && <p className="mt-2 text-xs text-amber-800">{t("Progress connection interrupted. Analysis may still be running; reconnecting.")}</p>}
    </div>
  );
}
