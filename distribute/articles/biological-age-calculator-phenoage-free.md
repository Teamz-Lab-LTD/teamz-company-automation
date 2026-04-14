---
title: "Your Body Has Two Ages. A Free PhenoAge Calculator Shows the Gap"
slug: biological-age-calculator-phenoage-free
tags: longevity, health, biological-age, phenoage, levine, biomarkers, free
canonical_url: https://tool.teamzlab.com/longevity/bio-vs-chrono-age-gap/
og_image: https://tool.teamzlab.com/og-images/og-default.png
---

Your body has two ages. Your birth certificate says one number. Your blood says another.

The gap between them is, increasingly, the thing longevity researchers actually care about. Chronological age is a clock that only moves in one direction. Biological age — estimated from the pattern of inflammation, metabolism, and organ function in your blood — moves in both. That is the whole point.

> **Educational tool only. Not a medical device. Not diagnostic. The calculator described here is for self-tracking and education. Any blood result outside a reference range should be discussed with a licensed clinician.**

## Where the number comes from: Levine's PhenoAge

Most of the "biological age" numbers floating around social media trace back to one paper: Morgan Levine et al., *An epigenetic biomarker of aging for lifespan and healthspan* (Aging US, 2018, [PMID 29676998](https://pubmed.ncbi.nlm.nih.gov/29676998/)). Levine's team trained a mortality model on [NHANES](https://www.cdc.gov/nchs/nhanes/index.htm) data using 42 clinical markers, then reduced it to a 9-biomarker composite — now known as PhenoAge — that predicted all-cause mortality more accurately than chronological age alone.

PhenoAge is a statistical construct, not a physical organ clock. It asks, roughly: "Given your bloodwork, what age would an average NHANES participant have to be to face your current 10-year mortality risk?" If that number is lower than your actual age, you're aging more slowly on the specific axes the model measures. If it's higher, something in the panel is off.

## The 9 inputs (plus chronological age)

Every input is from a standard CBC + Comprehensive Metabolic Panel + high-sensitivity CRP — the kind of draw most primary care clinics run for $50–150 out-of-pocket, or which comes free with an annual physical in many countries.

1. **Albumin** (g/L) — a liver-synthesized protein. Low albumin = poor nutrition, chronic inflammation, or liver/kidney stress. It is one of the strongest single mortality predictors in older adults.
2. **Creatinine** (µmol/L) — a muscle-breakdown byproduct filtered by the kidneys. Reads both kidney filtration and muscle mass. Context-dependent: a lifter will run higher than a sedentary peer of the same health.
3. **Glucose** (mmol/L, fasting) — metabolic stress. Chronically elevated fasting glucose signals insulin resistance, even below the diabetes threshold.
4. **C-reactive protein (CRP)** (mg/L) — systemic inflammation. Chronic low-grade inflammation ("inflammaging") is one of the [hallmarks of aging](https://www.cell.com/cell/fulltext/S0092-8674(22)01377-0). hs-CRP is the relevant version.
5. **Lymphocyte %** — immune reserve. Low lymphocyte proportion correlates with immunosenescence.
6. **Mean corpuscular volume (MCV)** — average red blood cell size. Drifts up with age and with B12/folate issues.
7. **Red cell distribution width (RDW)** — variability in red cell size. One of the quietest but most powerful mortality predictors in the panel; elevated RDW shows up in cardiovascular, cancer, and all-cause mortality studies.
8. **Alkaline phosphatase (ALP)** — liver and bone turnover.
9. **White blood cell count (WBC)** — immune activation. Persistently high WBC without infection tracks with cardiovascular risk.

Plus chronological age itself, which anchors the formula.

## Why this is suddenly everywhere

Three forces collided. [Peter Attia's *Outlive*](https://peterattiamd.com/outlive/) reframed longevity as a clinical practice organized around the "four horsemen" (atherosclerotic CVD, cancer, neurodegeneration, metabolic disease) plus a fifth — accidental/age-related decline. [Bryan Johnson's Blueprint](https://blueprint.bryanjohnson.com/) turned biomarker optimization into a public spectacle. And consumer panels — Function Health, InsideTracker, Quest's direct-to-consumer menu — made routine bloodwork a lifestyle product rather than a sick-visit artifact.

The upshot: millions of people now have CBC + CMP + CRP results sitting in a patient portal and nowhere obvious to plug them in.

## What counts as a "good" gap

Published PhenoAge distributions suggest:

- **±3 years of chronological age** — typical for healthy adults.
- **−5 to −10 years** — the range high-performing, well-trained individuals tend to land in.
- **−10 years or more** — outliers; usually reflects excellent cardiometabolic markers *and* low inflammation *and* preserved kidney/liver function simultaneously.
- **+5 years or more** — worth a conversation with a clinician. A single elevated CRP from a recent cold can skew it; a persistent pattern across two draws is the signal.

The gap is more useful as a trend than a snapshot. A single PhenoAge number has real confidence intervals. Two draws, six months apart, with the same lab, tell you something your doctor's "everything looks normal" summary may not.

## The calculator

I built a free [Biological vs Chronological Age Gap Visualizer](https://tool.teamzlab.com/longevity/bio-vs-chrono-age-gap/) that runs Levine's PhenoAge formula entirely in your browser. Your blood values never leave the device — no account, no upload, no server round-trip. Paste your nine numbers, get your biological age, the gap, and a visualization of which markers are pulling the number up or down.

There's also a built-in AI coach that contextualizes which markers are contributing most to the gap, and a Pinterest-ready share card if you want to track the number publicly over time.

It's self-tracking, not diagnosis. The formula was trained on a US population (NHANES) and uses SI units — conversions for US conventional units are built into the form.

## Three levers that actually move the number

If you want to *do* something with the output rather than just read it, the evidence is reasonably consistent on three inputs:

1. **Zone 2 cardio.** Three to four hours/week at a conversational pace. Drives mitochondrial density, which shows up indirectly in glucose regulation and CRP. Attia's [Zone 2 primer](https://peterattiamd.com/category/exercise/zone-2/) is the canonical explainer.
2. **Protein ~1.6 g/kg/day.** Preserves lean mass, which feeds back into creatinine interpretation, glucose handling, and functional longevity. See Attia's episodes with Luc van Loon and Don Layman.
3. **Sleep consistency.** Not just duration — same sleep and wake window, ±30 minutes. Inconsistent sleep elevates CRP and fasting glucose more reliably than short sleep alone.

None of these will halve your PhenoAge in a quarter. All three, held for a year, tend to move CRP, glucose, and lymphocyte % in the right direction — which is where most of the gap-closing happens in practice.

---

**Again: the calculator is an educational tool, not a medical device. It does not diagnose, treat, or prevent disease. If a value in your panel is flagged, or if the PhenoAge gap is meaningfully positive across repeat draws, take the numbers to a licensed clinician who can read them in the context of the rest of your chart.**

*Sources: Levine et al. 2018 ([PMID 29676998](https://pubmed.ncbi.nlm.nih.gov/29676998/)); [NHANES](https://www.cdc.gov/nchs/nhanes/index.htm); Peter Attia, *Outlive* (2023); Hone Health 2026 longevity trends report.*
