import { Suspense, lazy, useEffect, useState } from 'react';
import {
  AlertTriangle,
  Beaker,
  BookOpen,
  ChevronRight,
  Database,
  Download,
  FileText,
  GitCommit,
  ListChecks,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

const DetectorHero = lazy(() => import('./DetectorHero.jsx'));
const panel = 'rounded-[1.75rem] border border-teal-900/60 bg-[#071113]/90 p-5 shadow-[0_20px_70px_rgba(0,0,0,.32)] md:p-6';

function useJson(path) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  useEffect(() => {
    let cancelled = false;
    fetch(path)
      .then((response) => {
        if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
        return response.json();
      })
      .then((data) => { if (!cancelled) setState({ data, error: null, loading: false }); })
      .catch((error) => { if (!cancelled) setState({ data: null, error, loading: false }); });
    return () => { cancelled = true; };
  }, [path]);
  return state;
}

function Section({ icon: Icon, eyebrow, title, className = '', children }) {
  return (
    <article className={`${panel} ${className}`}>
      <div className="mb-5 flex items-center gap-3 border-b border-teal-950 pb-4">
        <span className="grid h-9 w-9 place-items-center rounded-xl border border-teal-700/50 bg-teal-400/10 text-teal-300">
          <Icon size={17} aria-hidden="true" />
        </span>
        <div>
          {eyebrow && <p className="text-[10px] uppercase tracking-[0.24em] text-teal-500">{eyebrow}</p>}
          <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
        </div>
      </div>
      {children}
    </article>
  );
}

function MetricCard({ metric, index }) {
  const hasUncertainty = metric.uncertainty_low != null && metric.uncertainty_high != null;
  const value = typeof metric.estimate === 'number' ? metric.estimate.toPrecision(4) : String(metric.estimate);
  return (
    <article className="metric-card relative overflow-hidden rounded-2xl border border-teal-900/70 bg-[#061012] p-5">
      <span className="absolute right-4 top-3 font-mono text-[10px] text-teal-800">CH-{String(index + 1).padStart(2, '0')}</span>
      <p className="pr-10 text-xs uppercase tracking-[0.16em] text-slate-500">{metric.name.replace(/_/g, ' ')}</p>
      <p className="mt-3 font-mono text-2xl font-semibold text-teal-100">
        {value}<span className="ml-1.5 text-xs font-normal text-teal-500">{metric.units}</span>
      </p>
      {hasUncertainty && (
        <p className="mt-2 text-xs text-slate-400">
          95% CI [{metric.uncertainty_low.toPrecision(3)}, {metric.uncertainty_high.toPrecision(3)}]
        </p>
      )}
      <p className="mt-1 font-mono text-[11px] text-slate-600">sample n={metric.sample_size}</p>
    </article>
  );
}

function inverseNormalCDF(p) {
  if (p <= 0 || p >= 1) return NaN;
  const a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00];
  const b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01, -1.328068155288572e+01];
  const c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00];
  const d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00];
  const pLow = 0.02425;
  const pHigh = 1 - pLow;
  let q;
  let r;
  if (p < pLow) {
    q = Math.sqrt(-2 * Math.log(p));
    return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  if (p <= pHigh) {
    q = p - 0.5;
    r = q * q;
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
  }
  q = Math.sqrt(-2 * Math.log(1 - p));
  return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
}

function ConfidenceExplorer({ metrics }) {
  const withInterval = (metrics || []).filter((metric) => metric.uncertainty_low != null && metric.uncertainty_high != null);
  const [selected, setSelected] = useState('');
  const [confidence, setConfidence] = useState(95);
  useEffect(() => {
    if (!selected && withInterval.length) setSelected(withInterval[0].name);
  }, [selected, withInterval]);
  if (!withInterval.length) return null;
  const metric = withInterval.find((item) => item.name === selected) ?? withInterval[0];
  const sigma = ((metric.uncertainty_high - metric.uncertainty_low) / 2) / 1.959963984540054;
  const zLevel = inverseNormalCDF(0.5 + confidence / 200);
  const low = metric.estimate - zLevel * sigma;
  const high = metric.estimate + zLevel * sigma;
  return (
    <Section icon={Beaker} eyebrow="Interactive diagnostic" title="Confidence-level explorer">
      <p className="text-xs leading-relaxed text-slate-500">
        Approximate interval sensitivity derived from the reported 95% bootstrap interval under a normal sampling assumption. This control does not rerun the bootstrap; the 95% values in the metric channels remain the computed result.
      </p>
      {withInterval.length > 1 && (
        <select className="mt-4 w-full rounded-xl border border-teal-900 bg-[#030a0c] px-3 py-2 text-sm text-slate-200" value={metric.name} onChange={(event) => setSelected(event.target.value)}>
          {withInterval.map((item) => <option key={item.name} value={item.name}>{item.name.replace(/_/g, ' ')}</option>)}
        </select>
      )}
      <label className="mt-5 flex items-center justify-between text-xs uppercase tracking-wider text-slate-400">
        Confidence level <span className="font-mono text-teal-300">{confidence.toFixed(1)}%</span>
      </label>
      <input className="mt-3 w-full accent-teal-400" type="range" min="50" max="99.9" step="0.1" value={confidence} onChange={(event) => setConfidence(Number(event.target.value))} />
      <p className="mt-4 font-mono text-2xl text-teal-100">[{low.toPrecision(4)}, {high.toPrecision(4)}]</p>
      <p className="mt-1 text-xs text-slate-600">{metric.units} · estimate {metric.estimate.toPrecision(4)} · n={metric.sample_size}</p>
    </Section>
  );
}

const warningRules = [
  { key: 'sample', label: 'Underpowered samples', severity: 'limitation', match: (text) => text.includes('below minimum') || text.includes('sample size') || text.includes('underpowered') },
  { key: 'conditioning', label: 'Ill-conditioned fits', severity: 'limitation', match: (text) => text.includes('covariance') || text.includes('condition number') || text.includes('non-finite') },
  { key: 'convergence', label: 'Non-convergent fits', severity: 'limitation', match: (text) => text.includes('converge') || text.includes('maxfev') },
  { key: 'physical', label: 'Rejected physical outliers', severity: 'limitation', match: (text) => text.includes('physically plausible') || text.includes('outside physical') },
  { key: 'failure', label: 'Validation failures', severity: 'critical', match: (text) => text.includes('checksum') || text.includes('failed validation') || text.includes('missing required') || text.startsWith('error') },
];

function groupWarnings(items) {
  const groups = new Map();
  items.forEach((warning) => {
    const text = String(warning);
    const lowered = text.toLowerCase();
    const rule = warningRules.find((candidate) => candidate.match(lowered)) ?? { key: 'other', label: 'Other recorded notes', severity: 'limitation' };
    const group = groups.get(rule.key) ?? { ...rule, entries: [] };
    group.entries.push(text);
    groups.set(rule.key, group);
  });
  return [...groups.values()];
}

function WarningSummary({ warnings }) {
  if (warnings.loading) return <p className="text-sm text-slate-500">Loading recorded warnings…</p>;
  if (warnings.error) return <p className="text-sm text-rose-300">Warnings file could not be read: {String(warnings.error)}</p>;
  const entries = Array.isArray(warnings.data) ? warnings.data : [];
  if (!entries.length) {
    return (
      <div className="rounded-2xl border border-teal-800/60 bg-teal-400/5 p-4">
        <p className="font-medium text-teal-200">No warnings recorded</p>
        <p className="mt-1 text-xs text-slate-500">results/warnings.json is present and contains no entries.</p>
      </div>
    );
  }
  return (
    <div>
      <p className="mb-4 text-sm text-slate-400">{entries.length} transparent processing notes, grouped by outcome.</p>
      <div className="space-y-2">
        {groupWarnings(entries).map((group) => (
          <div key={group.key} className={`flex items-center justify-between rounded-xl border px-4 py-3 ${group.severity === 'critical' ? 'border-rose-900 bg-rose-950/20 text-rose-200' : 'border-amber-900/70 bg-amber-950/15 text-amber-200'}`}>
            <span className="text-sm">{group.label}</span><strong className="font-mono">{group.entries.length}</strong>
          </div>
        ))}
      </div>
      <details className="mt-4 rounded-xl border border-teal-950 bg-black/20 p-4">
        <summary className="cursor-pointer text-sm text-teal-300">Show all {entries.length} raw entries</summary>
        <ol className="mt-4 max-h-80 space-y-2 overflow-auto pl-5 text-xs leading-relaxed text-slate-400">
          {entries.map((warning, index) => <li key={`${index}-${warning}`}>{String(warning)}</li>)}
        </ol>
      </details>
    </div>
  );
}

function StatusBadge({ children, tone = 'neutral' }) {
  const tones = {
    neutral: 'border-teal-900 bg-teal-950/30 text-teal-200',
    real: 'border-emerald-800 bg-emerald-950/30 text-emerald-200',
    demo: 'border-amber-800 bg-amber-950/30 text-amber-200',
  };
  return <span className={`rounded-full border px-3 py-1.5 text-xs ${tones[tone]}`}>{children}</span>;
}

export default function App() {
  const project = useJson('./project.json');
  const summary = useJson('./results/summary.json');
  const warnings = useJson('./results/warnings.json');
  const benchmarks = useJson('./results/benchmarks.json');

  if (project.loading) return <main className="grid min-h-screen place-items-center bg-[#020607] text-teal-300">Initializing detector audit…</main>;
  if (project.error || !project.data) return <main className="grid min-h-screen place-items-center bg-[#020607] text-rose-300">Could not load project.json: {String(project.error)}</main>;

  const p = project.data;
  const isDemo = summary.data?.data_kind === 'synthetic_smoke_test' || summary.data?.data_kind === 'synthetic_demo';

  return (
    <main className="cr-background min-h-screen">
      <div className="mx-auto max-w-[1500px] px-4 py-6 md:px-8 md:py-10">
        <header className="hero-frame relative overflow-hidden rounded-[2.25rem] border border-teal-800/60 bg-[#040b0d]/95">
          <div className="grid min-h-[520px] lg:grid-cols-[1.08fr_.92fr]">
            <div className="relative z-10 flex flex-col justify-between p-7 md:p-10 lg:p-12">
              <div>
                <div className="mb-8 flex items-center gap-3 text-[11px] uppercase tracking-[0.28em] text-teal-400">
                  <span className="h-px w-10 bg-teal-400" />
                  {p.category}
                </div>
                <h1 className="max-w-4xl text-4xl font-semibold leading-[1.06] tracking-[-0.035em] text-white md:text-6xl">{p.title}</h1>
                <p className="mt-6 max-w-2xl text-base leading-relaxed text-slate-300 md:text-lg">{p.question}</p>
              </div>
              <div className="mt-9">
                <div className="flex flex-wrap gap-2">
                  <StatusBadge>{p.status}</StatusBadge>
                  <StatusBadge>Priority {p.priority}/10</StatusBadge>
                  <StatusBadge>{p.dataMode}</StatusBadge>
                  {summary.data && <StatusBadge tone={isDemo ? 'demo' : 'real'}>{isDemo ? 'SYNTHETIC DEMO RESULTS' : 'REAL DATA RESULTS'}</StatusBadge>}
                </div>
                <p className="mt-5 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.15em] text-slate-600"><Sparkles size={13} /> HST detector-event benchmark</p>
              </div>
            </div>
            <div className="relative min-h-[360px] border-t border-teal-950 lg:border-l lg:border-t-0">
              <Suspense fallback={<div className="grid h-full min-h-[360px] place-items-center font-mono text-xs text-teal-700">Loading stylized detector…</div>}>
                <DetectorHero />
              </Suspense>
              <p className="absolute bottom-4 right-5 rounded-full border border-teal-900 bg-black/60 px-3 py-1 font-mono text-[10px] text-slate-500 backdrop-blur">Stylized illustration, not flight data</p>
            </div>
          </div>
        </header>

        {isDemo && (
          <div className="mt-5 flex items-start gap-3 rounded-2xl border border-amber-900/70 bg-amber-950/20 p-4 text-sm leading-relaxed text-amber-200">
            <AlertTriangle size={18} className="mt-0.5 shrink-0" />
            The displayed metrics and figures use a clearly labelled synthetic demo background with injected synthetic cosmic rays, not real HST observations. The real-data path replaces them only after the archive workflow is run.
          </div>
        )}

        <section className="mt-6 grid gap-6 xl:grid-cols-[1fr_340px]">
          <div>
            <div className="mb-3 flex items-end justify-between">
              <div><p className="text-[10px] uppercase tracking-[0.24em] text-teal-600">Detection telemetry</p><h2 className="mt-1 text-xl font-semibold text-white">Measured outcomes</h2></div>
              <span className="font-mono text-[10px] text-slate-600">LIVE JSON</span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {summary.data?.metrics?.slice(0, 6).map((metric, index) => <MetricCard key={metric.name} metric={metric} index={index} />)}
              {!summary.data && <article className="metric-card rounded-2xl border border-teal-900 bg-[#061012] p-5 text-slate-400">No results yet. Run scripts/run_analysis.py first.</article>}
            </div>
          </div>
          <ConfidenceExplorer metrics={summary.data?.metrics} />
        </section>

        <section className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(340px,.55fr)]">
          <Section icon={BookOpen} eyebrow="Evidence plate" title="Figure gallery">
            <div className="grid gap-4 md:grid-cols-2">
              {p.figures.map((figure, index) => (
                <figure key={figure.id} className={`group overflow-hidden rounded-2xl border border-teal-950 bg-[#020708] p-3 ${index === 0 ? 'md:col-span-2' : ''}`}>
                  <div className="overflow-hidden rounded-xl bg-white">
                    <img src={`./figures/${figure.id}.svg`} alt={figure.label} className={`w-full transition duration-500 group-hover:scale-[1.01] ${index === 0 ? 'max-h-[620px] object-contain' : ''}`} onError={(event) => { event.currentTarget.style.display = 'none'; }} />
                  </div>
                  <figcaption className="mt-3 flex items-center justify-between gap-3 text-sm text-slate-300"><span>{figure.label}</span><ChevronRight size={14} className="text-teal-600" /></figcaption>
                </figure>
              ))}
            </div>
          </Section>

          <div className="grid content-start gap-6">
            <Section icon={ShieldCheck} eyebrow="Research boundary" title="Provenance">
              <p className="text-sm leading-relaxed text-slate-300">{p.novelty}</p>
              <div className="mt-5 rounded-xl border border-amber-900/70 bg-amber-950/15 p-4 text-xs leading-relaxed text-amber-200">No result is public-ready until validation and provenance checks pass.</div>
              {summary.data?.provenance && (
                <dl className="mt-5 space-y-3 text-xs">
                  <div className="flex gap-2"><GitCommit size={14} className="text-teal-600" /><dt className="text-slate-600">commit</dt><dd className="ml-auto max-w-[12rem] truncate font-mono text-slate-300">{summary.data.provenance.git_commit}</dd></div>
                  <div className="flex gap-2"><FileText size={14} className="text-teal-600" /><dt className="text-slate-600">config sha256</dt><dd className="ml-auto max-w-[12rem] truncate font-mono text-slate-300">{summary.data.provenance.config_sha256 ?? 'n/a'}</dd></div>
                  <div className="flex gap-2"><Beaker size={14} className="text-teal-600" /><dt className="text-slate-600">package</dt><dd className="ml-auto font-mono text-slate-300">{summary.data.provenance.package_version}</dd></div>
                </dl>
              )}
            </Section>
            <Section icon={AlertTriangle} eyebrow="Transparent audit" title="Warnings"><WarningSummary warnings={warnings} /></Section>
          </div>
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-3">
          <Section icon={ListChecks} eyebrow="Release gate" title="Validation contract" className="lg:col-span-2">
            <ol className="grid gap-3 md:grid-cols-2">
              {p.validationContract.map((item, index) => <li key={item} className="flex gap-3 rounded-xl border border-teal-950 bg-black/15 p-3 text-sm leading-relaxed text-slate-300"><span className="font-mono text-teal-500">{String(index + 1).padStart(2, '0')}</span>{item}</li>)}
            </ol>
          </Section>
          <Section icon={Beaker} eyebrow="Pipeline" title="Methodology"><p className="text-sm leading-relaxed text-slate-300">{p.methodology}</p></Section>
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-2">
          <Section icon={AlertTriangle} eyebrow="Interpretation" title="Assumptions and limitations">
            <p className="mb-2 text-[10px] uppercase tracking-[0.22em] text-teal-600">Assumptions</p>
            <ul className="mb-6 space-y-2 text-sm leading-relaxed text-slate-300">{p.assumptions.map((item) => <li key={item}>— {item}</li>)}</ul>
            <p className="mb-2 text-[10px] uppercase tracking-[0.22em] text-amber-600">Limitations</p>
            <ul className="space-y-2 text-sm leading-relaxed text-slate-300">{p.limitations.map((item) => <li key={item}>— {item}</li>)}</ul>
          </Section>
          <div className="grid gap-6">
            <Section icon={Download} eyebrow="Reproducibility" title="Downloads and provenance manifest">
              <div className="grid gap-2 text-sm sm:grid-cols-2">
                <a className="download-link" href="./manifest.csv" download>data/manifest.csv</a>
                <a className="download-link" href="./results/summary.json" download>results/summary.json</a>
                {benchmarks.data && <a className="download-link" href="./results/benchmarks.json" download>results/benchmarks.json</a>}
              </div>
              <p className="mt-4 text-xs leading-relaxed text-slate-600">The manifest records product identifier, source URL, retrieval time, checksum, file size, selection reason, and archive terms for every real product used.</p>
            </Section>
            <Section icon={Database} eyebrow="Credit" title="Citation and licence">
              <p className="text-sm text-slate-300">Author: {p.citation.author}</p><p className="mt-1 text-sm text-slate-300">Licence: {p.citation.license}</p>
              <a className="mt-3 inline-block text-sm text-teal-300 hover:text-teal-100" href={p.citation.repository}>{p.citation.repository}</a>
            </Section>
          </div>
        </section>
      </div>
    </main>
  );
}
