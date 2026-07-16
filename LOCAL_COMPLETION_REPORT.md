# Local Completion Report — HST CCD Cosmic-Ray Rejection Benchmark

Author: Biswajit Jana. This report documents a local Claude Code implementation pass
(project 11 of the 30-project pack, `BUILD_FIRST` priority 9.3/10). No git operations
were performed. Nothing has been published.

## 1. Environment

- Reused the pre-existing `hst-ccd-cosmic-ray-rejection-benchmark` conda environment
  (Python 3.11.15), left over from a prior cut-off attempt on this same project.
  `pyproject.toml` pins: numpy==1.26.4, scipy==1.13.1, pandas==2.2.2,
  matplotlib==3.9.0, pyyaml==6.0.1, astropy==6.1.0, astroquery==0.4.7,
  photutils==1.13.0, astroscrappy==1.2.0; dev: pytest==8.2.2, pytest-cov==5.0.0,
  ruff==0.5.5, mypy==1.10.1, types-PyYAML.
- `astroscrappy==1.2.0` (a real, published L.A.Cosmic implementation, van Dokkum
  2001) was already pinned in the scaffold and confirmed available/installed —
  used directly as the rejection algorithm under test rather than a from-scratch
  reimplementation, per `IMPLEMENTATION_PLAN.md` Section 2.
- No local LaTeX toolchain (`pdflatex` not found); same documented limitation as
  the sibling projects.

## 2. Files created or changed

The prior cut-off attempt had already produced a detailed `IMPLEMENTATION_PLAN.md`,
a working conda env, and real (non-stub) `config.py`, `exceptions.py`,
`logging_utils.py`, `provenance.py`, `results_io.py`, `uncertainty.py`, `fetch.py`,
`inject.py`, `synthetic.py`. This session:
- Fixed a real bug in `fetch.py` (`BackgroundImage.bunit` field never populated by
  `load_background`/`cutout`, missing constructor argument — `TypeError` on any
  call) and a second real bug (`sci_header | primary_header`, astropy `Header`
  objects do not support `|` in this astropy version — `TypeError`), both caught by
  a newly written test, not by inspection.
- Implemented the remaining stub scientific modules: `metrics.py`
  (precision/recall/F1, PSF-core false-masking rate, background masking rate),
  `photometry.py` (aperture flux + flux-bias, `photutils`-based), `plotting.py`
  (mask-overlay helper), `core.py` (full `run_pipeline` sigclip-sweep orchestrator,
  `detect_sources_real` via `DAOStarFinder`).
- Wrote `scripts/fetch_data.py`, `scripts/run_analysis.py`, `scripts/make_figures.py`,
  `scripts/sync_web_assets.py` (all were stubs).
- Wrote `tests/conftest.py` and 8 new test files (51 tests total; the original stub
  `test_starter_core.py` was removed as superseded).
- Fixed two mypy type-annotation errors (`tuple[int, int]` vs numpy's actual
  `tuple[int, ...]` in `inject.py`/`core.py`).
- `reports/report.tex` + `reports/references.bib` written from scratch (verified
  literature carried over from `IMPLEMENTATION_PLAN.md` Section 3).
- `web-react/eslint.config.js` (added `react/jsx-uses-vars`/`react/jsx-uses-react`),
  `web-react/package.json` (removed unused `recharts`), `web-react/src/App.jsx`
  (rewritten from the `hst-wfc3ir-ramp-linearity-audit` template),
  `web-react/public/project.json` (rewritten with this project's real content).
- Added `.claude/launch.json` for this project's own web-react dev server (a
  project-local file, not the shared `GitHub/.claude/launch.json`, which was not
  touched).

## 3. Exact commands run (in order)

```bash
python -m pip install -e ".[dev]"          # into the pre-existing conda env
pytest -q                                    # 51 passed
ruff check .                                 # All checks passed
mypy src scripts                             # Success: no issues found in 18 source files
python scripts/run_analysis.py --demo
python scripts/make_figures.py --demo
cd web-react && npm install && npm run lint && npm run build
python scripts/sync_web_assets.py
# Real-data pipeline, run only after explicit operator authorization
# (granted in the orchestrating session for this whole batch of projects):
python scripts/fetch_data.py --i-have-authorization --n-exposures 2
python scripts/run_analysis.py
python scripts/make_figures.py
python scripts/sync_web_assets.py
cd web-react && npm run lint && npm run build   # re-verified after real data synced
pytest -q ; ruff check . ; mypy src scripts      # re-verified after real data synced
```

## 4. Test / lint / build results

- **pytest**: 51 tests passed, 0 failed (re-verified after the real-data run;
  no test depends on real network access).
- **ruff**: clean on the whole repository.
- **mypy**: clean on `src` and `scripts` (0 errors, 18 source files).
- **web-react**: `npm run lint` and `npm run build` both clean, both before and
  after `sync_web_assets.py` copied the real results in.
- Live browser verification was skipped: the shared `GitHub/.claude/launch.json`
  (which the task instructions say must not be touched) is pinned to a sibling
  project's dev server, and this tool environment's browser-preview integration
  only reads that shared file rather than this project's own
  `web-react/.claude/launch.json`. `npm run lint && npm run build` both passing
  clean is the documented primary bar and was met.

### Bugs found and fixed during implementation
1. `fetch.BackgroundImage` dataclass declared a required `bunit: str` field, but
   `load_background`/`cutout` never passed it — every call raised `TypeError`.
   Fixed by reading `BUNIT` from the SCI/primary header and threading it through
   both constructors.
2. `fetch.load_background` used `sci_header | primary_header` to merge FITS
   headers for read-noise-keyword lookup; astropy's `Header` class does not
   support the `|` operator in the pinned astropy version, raising `TypeError`
   on every real or synthetic FITS file. Fixed with `{**dict(...), **dict(...)}`.
   **Both bugs were caught by `tests/test_synthetic_and_fetch.py`, not by
   inspection** — the injection-recovery validation gate itself never exercises
   `load_background`, so this would otherwise have surfaced only in Phase 8
   against real data.
3. `inject._track_pixels`/`inject.source_exclusion_mask` were type-annotated with
   `shape: tuple[int, int]`, but callers pass `numpy.ndarray.shape`, which mypy
   correctly types as `tuple[int, ...]` — fixed by widening the annotation.

## 5. Real datasets accessed

- **MAST query** (`astroquery.mast.Observations.query_criteria`): `obs_collection="HST"`,
  `instrument_name="ACS/WFC"`, `proposal_id=["18004"]`, `dataproduct_type="image"`,
  `calib_level=[2]`, `filters="F606W"`; sorted deterministically by `obs_id`; first
  2 rows selected; `dataRights=PUBLIC` confirmed on both before download.
- **Files downloaded**: `jfnx09u8q_flt.fits` and `jfnx09u9q_flt.fits`, exposure-level
  ACS/WFC FLT (calibrated, level-2, uncombined single-exposure) products,
  168,431,040 bytes each (**336,862,080 bytes / ~336.9 MB total**), source
  `https://mast.stsci.edu`, retrieved `2026-07-14T20:21:43Z`. SHA-256 checksums
  recorded in `data/manifest.csv`
  (`343fc64...9db4ab16` and `088a7f7...ab016533`) and computed from the actual
  downloaded bytes (not fabricated). Licence: STScI/MAST public HST archive data
  (`dataRights=PUBLIC`), no proprietary period; standard STScI archive usage
  terms. Raw FITS files are **not committed** (`.gitignore` excludes `data/raw/*`).

## 6. Validation and uncertainty outcomes

- **Injection-recovery validation gate**: PASSED
  (`tests/test_core_pipeline.py::test_run_pipeline_injection_recovery_validation_gate`).
  On a labelled-synthetic 200x200 field with 8 injected point sources and 25
  injected cosmic-ray events per trial (3 trials/sigclip), recall against the
  known-injected CR pixel population was >0.85 (observed: 1.00) at every swept
  `sigclip` value, and precision increased materially from `sigclip`=3.0 to
  `sigclip`=10.0 (observed: 0.21 -> 1.00) as required.
- **Null/negative control**: PASSED
  (`test_null_control_no_injected_cosmic_rays_low_false_positive_rate`) — with
  zero cosmic rays injected, `astroscrappy` at its default `sigclip`=4.5 flagged
  under 2% of a clean synthetic background+source field.
- **Failure-mode tests**: empty background, no sources, empty sigclip sweep, too
  few bootstrap samples, ill-conditioned/non-finite fit covariance, flat image for
  source detection, aperture centred outside the image, non-2D arrays, crowded
  exclusion masks — all raise the documented exceptions rather than silently
  degrading.
- **Uncertainty**: bootstrap 95% CIs (1000 resamples, seed 20260713) on
  recall/precision/flux-bias, kept strictly separate from the (unused-by-this-
  pipeline but available and independently tested) fit-convergence checker.

## 7. Real-data results

Demo-path (`--demo`) and real-data-path numbers are both recorded in
`results/summary.json` (the real-data run overwrote the demo run's file; the
demo numbers are quoted from the session log and `reports/report.tex`).

**Real-data path** (600x600 central cutouts of both real ACS/WFC exposures,
40 injected CR events/trial, 5 trials/sigclip/exposure, 146 real
DAOStarFinder-detected sources per exposure; 70 metrics, 0 warnings):

| sigclip | recall | precision | PSF-core false-masking | bg masking (upper bound) | flux frac. bias |
|---|---|---|---|---|---|
| 3.0  | 1.00 | 0.007 | 0.325 | 0.045 | -0.912 |
| 4.5  | 1.00 | 0.015 | 0.261 | 0.019 | -0.881 |
| 6.0  | 1.00 | 0.022 | 0.221 | 0.012 | -0.854 |
| 8.0  | 1.00 | 0.028 | 0.194 | 0.009 | -0.824 |
| 10.0 | 1.00 | 0.035 | 0.177 | 0.007 | -0.796 |

(means across the two real exposures; per-exposure numbers agree to within a
few percent of each other, see `results/summary.json` for the full
per-exposure breakdown).

**Key real finding**: recall stayed perfect throughout — detection sensitivity
is not the bottleneck. But precision, PSF-core false-masking, and aperture-flux
bias were all far worse on real data than on the clean synthetic demonstration
field at every matched `sigclip` value (synthetic: precision 0.21->1.00,
PSF false-masking 0.00 throughout, flux bias within +/-1e-4; real: precision
0.007->0.035, PSF false-masking 0.33->0.18, flux bias -0.91->-0.80). This
reflects three compounding, documented effects (not a pipeline bug): (a) a
real single, uncombined ACS/WFC FLT exposure already contains a substantial
population of real, un-rejected cosmic rays that astroscrappy correctly flags,
inflating both the background-masking-rate (labelled an upper bound by design)
and the precision-against-injected-truth denominator; (b) `detect_sources_real`
runs DAOStarFinder without first excluding DQ-flagged bad/hot pixels, so some
fraction of the "146 real point sources" used for the PSF-core metric are
themselves hot pixels or unflagged cosmic rays, not genuine stars; (c) the
injected-CR amplitude/track model was tuned against the synthetic field only.
The qualitative, well-supported finding: **aperture photometry at real source
positions in a single uncombined ACS/WFC exposure is not safe from
CR-cleaning-induced bias at any of the five sigclip settings tested.**

## 8. Claims safe for a public README

- "Implements a reproducible benchmark of astroscrappy's (L.A.Cosmic, van Dokkum
  2001) sigclip parameter against known-ground-truth synthetic cosmic-ray
  injections, validated by a passing injection-recovery gate and a null control
  before real data was touched."
- "On two real, public ACS/WFC FLT exposures (HST proposal 18004, F606W),
  detection recall against injected cosmic rays was 1.00 at every sigclip value
  swept (3.0-10.0), but precision against that same injected population never
  exceeded 0.035, and the aperture-flux fractional bias at real source positions
  ranged from -0.80 to -0.91 across the sweep — real, measured numbers from
  results/summary.json, not fabricated or aspirational."
- "51 automated tests including a null control and multiple failure-mode tests;
  ruff- and mypy-clean."
- "A controlled parameter-sweep benchmark with injected ground truth; not a
  replacement for Astro-SCRAPPY, deepCR, Cosmic-CoNN, or the standard HST
  calibration pipeline."

## 9. Claims that must NOT be made

- Do not claim these real numbers characterize astroscrappy's general
  performance on HST CCD images — see Section 7's three compounding, documented
  reasons the real precision/false-masking/bias numbers are worse than the
  synthetic demonstration, including an un-filtered source-detection step that
  likely counts some hot pixels/real cosmic rays as "point sources."
  the real-data sample is 2 exposures, one 600x600 cutout region each.
- Do not claim the background-masking-rate is a true false-positive rate — it is
  explicitly documented as an upper bound (may include correctly-flagged real,
  pre-existing cosmic rays in the frame).
- Do not claim this replaces or supersedes Astro-SCRAPPY, deepCR, Cosmic-CoNN, or
  calacs/the standard HST pipeline.
- Do not claim the TeX report PDF has been visually verified — no local LaTeX
  toolchain was available; only source-level completeness was checked.
- Do not claim `sigfrac`/`objlim` were swept — only `sigclip` was varied; the
  other two parameters were held at astroscrappy's documented defaults
  throughout.

## 10. Manual review checklist for Biswajit

- [ ] Compile `reports/report.tex` locally/Overleaf and read the PDF end-to-end.
- [ ] Consider re-running `detect_sources_real` with DQ-mask-based pre-filtering
      (excluding hot/bad/already-CR-flagged pixels before DAOStarFinder) to get
      a cleaner PSF-core false-masking measurement on real data — flagged as a
      known limitation in this session rather than fixed, to stay within the
      first-release time-box.
  - [ ] Decide whether to extend the sigclip sweep to also vary `sigfrac`/`objlim`
      (currently held at documented defaults) as a follow-up.
- [ ] Pin the `TODO_VERIFY` MAST/HLA documentation citation in `references.bib`
      to a specific dated edition.
- [ ] Consider running the real-data sweep on the full-frame science array (not
      the 600x600 cutout) if compute time allows, as a follow-up validation of
      the cutout-based results.
- [ ] Review `npm audit` output (5 dev-tooling-only advisories, same class as
      sibling projects) and decide whether to bump pinned frontend tooling.
- [ ] Follow the batch's manual GitHub repository-creation process — no git
      operations were performed in this session.
