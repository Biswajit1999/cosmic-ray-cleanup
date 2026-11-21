# Conditional cosmic-ray threshold audit — 2026-11-21

Issue: #1. Three diagnostics: pixel precision/recall versus a supplied threshold, false masking of supplied non-cosmic source-core pixels, and image-level clustered bootstrap of an image-associated scalar. No HST truth masks were accessed. Pixel-level independent bootstrap would underestimate uncertainty when pixels share image effects.

Run `python -m unittest discover -s research/2026-11-21 -p 'test_*.py'`. Requirements: NumPy. Tests are synthetic, not observational validation. To produce a figure run `python research/2026-11-21/plot_conditional_audit.py` (Matplotlib required); it writes a labelled synthetic PNG to the current directory.

Limitations: threshold calibration requires labelled independent images, the source-core mask must be independently defined, and cluster resampling requires representative independent images. The bootstrap quantiles are conditional on the supplied image sample.

Scientific author: Biswajit Jana. AI-assisted implementation disclosed; no fabricated co-authors.