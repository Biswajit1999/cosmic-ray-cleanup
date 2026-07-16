# Claude Code Task — HST CCD Cosmic-Ray Rejection Benchmark

## Non-negotiable restrictions

- Work only inside this local project folder.
- **Do not run `git commit`, `git push`, `gh repo create`, `gh pr create`, or modify any remote.**
- Do not add `Co-authored-by`, Claude, Anthropic or AI attribution to public files.
- Keep Biswajit Jana as the sole project author in `CITATION.cff` unless he explicitly adds collaborators.
- Do not fabricate mission data, literature metadata, benchmarks or research findings.

## Objective

Implement the first publication-grade release for:

**How do cosmic-ray rejection parameters trade detection recall against false masking and aperture-flux bias on HST CCD images?**

## Required implementation order

1. Read all files in `docs/` and `CURATION_STATUS.md`.
2. Audit the current tree and write `IMPLEMENTATION_PLAN.md` with file-level tasks.
3. Complete configuration, exceptions, schema validation and provenance first.
4. Implement data acquisition/ingestion without committing large raw files.
5. Implement reusable scientific modules under `src/hst_ccd_cosmic_ray_rejection_benchmark/`; notebooks must only orchestrate imported functions.
6. Implement synthetic/injection validation before interpreting real data.
7. Add quantitative uncertainty, null/failure tests and benchmarks.
8. Generate all figures from scripts.
9. Replace the React/Tailwind demo cards with real generated JSON outputs.
10. Complete the TeX report and references, using `TODO_VERIFY` for any unverified citation.
11. Run pytest, ruff, mypy, Python smoke commands and the web build.
12. Write `LOCAL_COMPLETION_REPORT.md` listing completed files, commands, results, unresolved limitations and manual review points.

## Scientific acceptance criteria

- precision/recall/F1
- PSF-core false masks
- flux bias
- bootstrap intervals
- runtime per megapixel

## Required web experience

A restrained instrument/science dashboard, not a decorative portfolio page. Use real metrics, uncertainty intervals, provenance and limitations. Ensure mobile responsiveness, accessible labels, keyboard navigation and no fake live-data language.

## Stop conditions

Stop and document the issue instead of guessing when:

- archive access or licence terms are unclear;
- expected columns/extensions are absent;
- a citation cannot be verified;
- synthetic recovery fails;
- final results depend on undocumented manual choices.
