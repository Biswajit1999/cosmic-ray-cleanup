# Dataset Plan

## Mode

**real HST cutouts + controlled injection**

## Official sources and literature seeds

- van Dokkum 2001, L.A.Cosmic
- Astro-SCRAPPY official package
- deepCR paper/software
- Cosmic-CoNN paper/software
- MAST/Hubble Legacy Archive documentation

## Acquisition rules

- Prefer official mission/archive endpoints and author-maintained catalogue deposits.
- Record product identifier, query, retrieval UTC, source URL, file size, checksum and licence/terms.
- Do not commit large raw FITS, HDF5 or catalogue files.
- Store a deterministic manifest under `data/manifest.csv`.
- Store only a tiny, clearly labelled synthetic/example dataset in `data/example/`.
- Never replace inaccessible real data with fabricated values while presenting them as observations.

## Required manifest columns

`product_id, source, source_url, retrieved_utc, sha256, file_size_bytes, selection_reason, licence_or_terms`

## FAIR contract

Every derived product must point to the raw product ID, software commit, configuration hash and transformation script.
