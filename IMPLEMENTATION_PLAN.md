# Implementation Plan — HST CCD Cosmic-Ray Rejection Benchmark

This is a local, non-public planning document (not committed to any remote; no git
operations are performed in this repository per `CLAUDE_TASK.md`).

## 1. Scope restatement

Bounded question: how do L.A.Cosmic-family cosmic-ray rejection parameters
(`sigclip`, `sigfrac`, `objlim`) trade detection recall against false masking of
real astrophysical signal (PSF cores) and aperture-flux bias, on real HST CCD
background images with **controlled synthetic cosmic-ray injection** (known ground
truth)? Data mode: real HST cutouts + controlled injection — distinct from the
pure archive-statistics audits in the sibling projects (`hst-acs-two-axis-cte-audit`,
`euclid-q1-vis-psf-astrometry-audit`, `hst-wfc3ir-ramp-linearity-audit`).

## 2. Method design decision

`astroscrappy==1.2.0` (already pinned in `pyproject.toml`) is the real, published,
peer-reviewed L.A.Cosmic implementation (van Dokkum 2001) used here as the
rejection algorithm under test — this is a **benchmark of a real published
algorithm's parameter space**, not a from-scratch reimplementation, matching the
"controlled benchmark with injected ground truth; not a replacement for
Astro-SCRAPPY..." novelty boundary in `CURATION_STATUS.md`.

Real background: a small cutout region of a real, public HST ACS/WFC FLT
(calibrated, not CR-combined) science array, which contains genuine background
noise, real astrophysical point sources, and (honestly disclosed) may already
contain a small number of un-labelled real cosmic-ray hits. Synthetic CR tracks
(short, sharp, few-pixel-wide energy deposits — the real physical CR signature,
distinct from a PSF-convolved point source) are injected at random pixel positions
with known footprint and amplitude, giving exact ground truth for recall/precision
on the *injected* population. This conflation risk (real background may contain
unlabelled real CRs) is documented explicitly in
`docs/ASSUMPTIONS_AND_LIMITATIONS.md` and the report's Limitations section, and is
mitigated by:

- reporting **recall** only against the exactly-known injected pixel population;
- reporting **PSF-core false-masking** against real DAOStarFinder-detected point
  sources (unambiguous — no CR truth needed, just "is real stellar flux getting
  masked");
- reporting a **background masking rate** (non-injected, non-source pixels flagged)
  with an explicit caveat that this is an upper bound on the true false-positive
  rate because it may include correctly-flagged real cosmic rays already present in
  the real frame.

## 3. Literature verification (completed against primary sources this session)

| Seed | Verified against | Result |
|---|---|---|
| van Dokkum 2001, L.A.Cosmic | arXiv:astro-ph/0108003 abstract page | Verified: "Cosmic-Ray Rejection by Laplacian Edge Detection", P. G. van Dokkum, PASP 113, 1420 (2001). |
| Astro-SCRAPPY | github.com/astropy/astroscrappy README | Verified: McCully et al., Zenodo DOI 10.5281/zenodo.1482018, BSD-3-Clause, cites van Dokkum 2001 PASP 113 1420. |
| deepCR | arXiv:1907.09500 + CrossRef (10.3847/1538-4357/ab3fa6) | Verified: Zhang & Bloom, "deepCR: Cosmic Ray Rejection with Deep Learning", ApJ 889, 24 (2020). |
| Cosmic-CoNN | arXiv:2106.14922 abstract page | Verified as an arXiv preprint (v3, 2022): Xu, McCully, Dong, Howell, Sen, "Cosmic-CoNN: A Cosmic Ray Detection Deep-Learning Framework, Dataset, and Toolkit". No traditional journal volume/page found at verification time — cited as an eprint, not marked TODO_VERIFY (the arXiv record itself is the verified primary source). |
| MAST/Hubble Legacy Archive documentation | Not a single citable paper; cited as `@manual` entries pointing to the live STScI documentation URLs, marked `TODO_VERIFY` for a specific dated edition, matching the pattern used in the sibling projects for the same class of citation. |

Additional citation used for the FLT/FLC product structure and DQ conventions:
Anderson & Bedin 2010, PASP 122, 1035 (DOI 10.1086/656399, confirmed resolving via
CrossRef) — reused from the sibling ACS project for describing the ACS/WFC FLT
product convention; included for context, not as a CR-rejection method citation.

## 4. Real-data access plan (verified live against MAST before download)

Reuse the same verified-working pattern as
`hst-acs-two-axis-cte-audit/scripts/fetch_data.py`: `astroquery.mast.Observations`,
`obs_collection="HST"`, `instrument_name="ACS/WFC"`, `calib_level=[2]`
(FLT/FLC), deterministic `.sort("obs_id")` + first-N selection, explicit
`dataRights == "PUBLIC"` check on every selected row before any download. A
distinct HST proposal from the sibling project will be preferred if a public
ACS/WFC FLT/FLC sample is available; if not, the same public proposal 18004
(F606W, PI Hayes) is an acceptable, already-confirmed-PUBLIC fallback since this
project injects synthetic CRs into the background rather than doing an FLT/FLC
CTE comparison, so reusing the same public dataset for a different scientific
question is legitimate and not a duplicate result. Only FLT (not CR-combined)
files are needed. 2 files planned (~170 MB each), well within a "modest real
CCD-imaging sample" per the task brief. Live verification happens in Phase 8
immediately before running `fetch_data.py --i-have-authorization`.

## 5. File-level task list

Foundation (`src/hst_ccd_cosmic_ray_rejection_benchmark/`):
- `config.py` — port from ACS project, renamed.
- `exceptions.py` — extend stub with `ArchiveAccessError`, `ConvergenceError`,
  `InsufficientDataError` (keep existing `DataSchemaError`, `ProvenanceError`).
- `logging_utils.py` — port verbatim.
- `provenance.py` — extend stub `sha256_file` into full module (`ManifestRow`,
  `append_manifest_row`, `read_manifest`, `sha256_bytes`, `sha256_config`,
  `get_git_commit`).
- `results_io.py` — new: `Metric`, `write_summary`, `validate_summary`.
- `uncertainty.py` — new: `bootstrap_statistic`, `check_fit_convergence` (ported).

Data layer:
- `fetch.py` — real MAST query/download logic used by `scripts/fetch_data.py`.
- `synthetic.py` (new) — synthetic CR track + point-source injection primitives
  shared by tests, `--demo`, and the real pipeline's validation gate.
- `inject.py` — thin, image-shape-aware wrapper composing `synthetic.py`
  primitives onto a given background array + returning ground truth.

Scientific modules:
- `metrics.py` — precision/recall/F1, PSF-core false-masking rate, background
  masking-rate, confusion-matrix helpers.
- `photometry.py` — aperture photometry wrapper (photutils) + flux-bias metric.
- `plotting.py` — small shared plotting helpers (kept minimal; most figure code
  lives in `scripts/make_figures.py` per the sibling-project pattern).
- `core.py` — `run_pipeline` orchestrating: load real background → for each
  parameter set in the sweep → inject → detect_cosmics (astroscrappy) → score.

Scripts:
- `scripts/fetch_data.py`, `scripts/run_analysis.py`, `scripts/make_figures.py`,
  `scripts/sync_web_assets.py`.

Tests: `tests/conftest.py` + one test file per module + `test_core_pipeline.py`,
covering the injection-recovery validation gate, null control, and failure modes.

Web: `web-react/eslint.config.js` fix, `package.json` recharts removal,
`web-react/src/App.jsx` rewrite from the WFC3/IR template, `public/project.json`
rewrite.

Report: `reports/report.tex`, `reports/references.bib`.

## 6. Parameter sweep design

Sweep `sigclip` in {3.0, 4.5, 6.0, 8.0, 10.0} (detection significance threshold)
holding `sigfrac=0.3`, `objlim=5.0` fixed (astroscrappy defaults), on a fixed
injected-CR population per trial (multiple independent injection trials per
`sigclip` value for bootstrap uncertainty). This directly produces the
precision-recall tradeoff and flux-bias-vs-aggressiveness curves required by
`docs/VALIDATION_CONTRACT.md`.

## 7. Stop conditions checked

- MAST access: to be live-verified in Phase 8 (not assumed).
- Citations: all verified above except the MAST/HLA documentation manual entries,
  which are marked `TODO_VERIFY` in `references.bib` as instructed.
- Synthetic recovery: validation gate implemented in
  `tests/test_core_pipeline.py`/`test_metrics.py` and must pass before Phase 8.

## 8. Phase 8 execution record (real data)

MAST access live-verified: `astroquery.mast.Observations.query_criteria` for
proposal 18004, ACS/WFC, F606W, `calib_level=[2]` returned confirmed-PUBLIC
rows for `jfnx09u8q`/`jfnx09u9q`. `scripts/fetch_data.py --i-have-authorization
--n-exposures 2` downloaded both FLT files (168,431,040 bytes each,
~336.9 MB total) and recorded checksummed manifest rows.

**Scope reduction (documented, not silent):** the full ACS/WFC FLT science
array is 4096x2048 pixels per chip. Running the full 5-value sigclip x 5-trial
sweep (25 `astroscrappy.detect_cosmics` calls per exposure) on the full frame
was impractically slow for this first-release pass. A central 600x600-pixel
cutout of each chip was used instead (`fetch.cutout`), keeping real background
statistics and real point sources while making the repeated-injection sweep
tractable (~2.5 minutes total for both exposures x 5 sigclip values x 5
trials = 50 `detect_cosmics` calls). This is recorded here and in
`reports/report.tex` Section "Data and provenance"/"Limitations" rather than
silently narrowing scope.

**Real-data finding:** precision-against-injected-truth, PSF-core
false-masking rate, and aperture-flux fractional bias were all substantially
worse on the real cutouts than on the synthetic demonstration field at every
matched `sigclip` value (see `reports/report.tex` Results and Limitations for
the full numbers and the three compounding, documented reasons: real
un-rejected cosmic rays already present in a single uncombined exposure,
DAOStarFinder source detection not excluding DQ-flagged/hot pixels before
scoring the PSF-core metric, and the injected-CR amplitude model being tuned
against the synthetic field only). Recall against the injected population
remained 1.00 throughout on both real exposures, confirming detection
sensitivity itself is not the limiting factor — genuine over-flagging and
its photometric consequences are.
