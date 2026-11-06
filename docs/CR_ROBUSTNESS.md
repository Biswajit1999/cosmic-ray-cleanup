# Cosmic-ray rejection robustness: synthetic methods

Scope issue: #1. This work does not modify the operational cleaning pipeline or claim new HST observations.

1. **Threshold curve:** precision, recall and F1 from injected truth pixels and detector scores. A threshold with zero predictions receives precision=0 and F1=0 by convention; the dataset must contain at least one injected CR pixel.
2. **Image-cluster bootstrap:** independent exposures are resampled as whole units to estimate uncertainty in a per-image mean photometric bias. It does not falsely count thousands of correlated pixels as independent replicates. The percentile interval assumes independent, exchangeable images; a small number of images makes it unreliable.
3. **Source-preserving threshold cost:** false-negative CR pixels plus an explicit weighted penalty for erroneously masking stellar PSF cores. The weight is illustrative, and truth/core masks must be disjoint. This is a diagnostic trade-off, not a calibrated optimal detection rule.

Reproduce: `pytest tests/test_cr_robustness.py -q`. Tests use deterministic synthetic arrays, check zero-prediction behavior, bootstrap reproducibility and a source-core protection example. No regenerated scientific figures are included because the existing report figures were not altered. Prepared with AI coding assistance; commit identity follows the authenticated GitHub account and repository contribution policy.
