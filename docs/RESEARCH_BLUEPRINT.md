# Research Blueprint

## Technical title

HST CCD Cosmic-Ray Rejection Benchmark

## Category

Astrophysics instrumentation / image analysis

## Bounded scientific question

How do cosmic-ray rejection parameters trade detection recall against false masking and aperture-flux bias on HST CCD images?

## Gap statement

A controlled benchmark with injected ground truth; not a replacement for Astro-SCRAPPY, deepCR, Cosmic-CoNN or HST pipelines.

## First-release scope

The first release must be completable as a focused 4–6 hour implementation pass after data access is working. It must deliver one reproducible analysis pipeline, one deterministic example/smoke dataset, tests, 4–6 figures, a concise TeX report and a deployable research webpage.

## Validation and uncertainty

- precision/recall/F1
- PSF-core false masks
- flux bias
- bootstrap intervals
- runtime per megapixel

## Required figures

1. injected image and mask
2. cleaning comparison
3. precision-recall panel
4. flux bias
5. runtime

## Reusable scientific modules

- `fetch.py`
- `inject.py`
- `metrics.py`
- `photometry.py`
- `plotting.py`
- `provenance.py`

## Explicit exclusions

- No novelty claim beyond the bounded dataset/question/method combination.
- No causal claim from descriptive catalogue correlations.
- No hidden manual data editing.
- No unsupported precision beyond the input uncertainties.
- No production-pipeline replacement claim.
