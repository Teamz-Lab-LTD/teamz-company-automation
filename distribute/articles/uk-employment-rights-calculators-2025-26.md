---
title: "UK Employment Rights Calculators 2025/26 — Redundancy, Holiday, SSP, Notice Period"
slug: uk-employment-rights-calculators-2025-26
tags: uk, employment-rights, redundancy, holiday-entitlement, ssp, notice-period, calculator, free-tools, work, hr
canonical_url: https://tool.teamzlab.com/uk/
og_image: https://tool.teamzlab.com/og-images/uk.png
language: en
---

If you work in the UK, the rules around redundancy pay, holiday entitlement, statutory sick pay (SSP), and notice periods change almost every April — and 2025/26 brought a big one: the statutory weekly pay cap jumped from £700 to **£719**, lifting the maximum statutory redundancy payout to **£21,570** for 20 years of service in the over-41 age band.

I built (and recently refreshed) a small set of free, browser-based calculators that handle these rules correctly for the 2025/26 tax year. No signup, no data collection — everything runs locally in your browser. Here are the five most useful ones, with the gotchas that trip people up.

## 1. UK Redundancy Pay Calculator 2025/26

Statutory redundancy pay in the UK depends on three things: your age, your gross weekly pay (capped at **£719** from 6 April 2025), and your years of continuous service (max 20). The age-based multiplier is the part most people get wrong:

- **Under 22:** 0.5 weeks' pay per year of service
- **Age 22–40:** 1 week's pay per year of service
- **Age 41+:** 1.5 weeks' pay per year of service

So 12 years of service at the £719 cap gives you between £4,314 (under 22) and £12,942 (over 41) statutory entitlement. Anything your employer pays above that is "enhanced redundancy" and may follow different tax rules.

**The £30,000 tax-free threshold:** statutory redundancy is always tax-free; enhanced redundancy is tax-free up to a combined £30,000. Above that, income tax kicks in (but no NI). Payments in lieu of notice (PILON) are taxed as normal earnings.

**Try the calculator:** https://tool.teamzlab.com/uk/redundancy-pay-calculator/

It includes a quick-reference table for service lengths from 2 to 20 years across all three age bands, and answers the most common search query — "how much redundancy pay do I get after 12 years?" — directly.

## 2. UK Holiday Entitlement Calculator 2025/26

The UK statutory minimum is 5.6 weeks of paid annual leave per year under the Working Time Regulations 1998. For a 5-day-per-week worker, that caps at **28 days** (which can include bank holidays — they aren't automatically extra).

For part-time workers the formula is `5.6 × days per week`. For irregular-hours and zero-hours workers, the entitlement is the famous **12.07% method**: every hour worked accrues approximately 7.24 minutes of paid leave. The 12.07% comes from `5.6 ÷ 46.4` (working weeks after subtracting leave weeks).

A worker doing 16 hours per week gets 89.6 hours of statutory leave per year — about 11.2 days at an 8-hour day length.

Following the 2024 amendments, employers can either accrue leave for irregular-hours workers or pay rolled-up holiday pay at 12.07% on top of normal pay (clearly itemised on the payslip). For fixed-hours part-timers, do **not** use 12.07% — use the days-per-week formula.

**Try the calculator:** https://tool.teamzlab.com/uk/holiday-entitlement-calculator/

It supports full-time, part-time, and irregular-hours workers, and shows entitlement in days, hours, and pro-rata if you started mid-year.

## 3. UK Statutory Sick Pay (SSP) Calculator

SSP is paid by your employer when you are off sick for four or more consecutive days (including weekends and non-working days). The first three days are unpaid "waiting days" — SSP only kicks in from day four. SSP runs for up to 28 weeks per period of incapacity for work.

To qualify you must be earning at least the lower earnings limit (£123/week from 6 April 2024, expected to rise April 2026). Workers on zero-hours contracts can qualify if they meet the LEL averaged across the eight weeks before sickness started.

**Try the calculator:** https://tool.teamzlab.com/uk/ssp-calculator/

Common questions answered: "how is SSP calculated?", "do I get paid for the first three days off sick?", and "what is the SSP rate for 2025/26?".

## 4. Notice Period Calculator

Statutory minimum notice depends on length of service:

- Less than 1 month: no statutory notice required
- 1 month to 2 years: 1 week
- 2+ years to 12 years: 1 week per complete year of service
- 12+ years: 12 weeks (capped)

Your contract may specify longer notice — but never less than the statutory minimum. The calculator handles the maximum-of-contractual-vs-statutory rule and returns your **last working day** for any start date.

**Try the calculator:** https://tool.teamzlab.com/work/notice-period-calculator/

Useful when planning a resignation date around bonus payments, holiday accrual, or the end of a probation period.

## 5. UK Universal Credit Calculator 2025/26

If you are in or expecting redundancy, this is the next-step calculator. Universal Credit phases in based on standard allowance, housing element, child element, and earnings taper (currently 55% — meaning every £1 you earn above the work allowance reduces UC by 55p).

The 2025/26 standard allowance is £400.14/month for a single person aged 25+, £628.10 for a couple. Housing costs are capped to the local LHA rate.

**Try the calculator:** https://tool.teamzlab.com/uk/universal-credit-calculator/

Particularly relevant for anyone being made redundant who needs to understand how the £21,570 statutory redundancy interacts with the UC capital limit (£16,000 cuts off UC entirely; £6,000–£16,000 reduces it).

## Why I built these

I work as a solo developer building privacy-first browser tools. UK employment law changes every April but the official gov.uk calculators are clunky on mobile and don't show the formula breakdown. I wanted tools that:

1. Work on any device, no signup
2. Show the formula (not just the answer)
3. Reference the actual legislation (Working Time Regs 1998, ERA 1996)
4. Handle 2025/26 rates correctly

If you spot a calculation that's off, the source code is fully visible (view source) and I take fixes seriously — the £719 cap update went live the same week the rate changed.

## Quick reference: 2025/26 UK statutory rates

| Item | 2024/25 | 2025/26 |
|------|---------|---------|
| Redundancy weekly pay cap | £700 | **£719** |
| Max statutory redundancy (20 yrs, age 41+) | £21,000 | **£21,570** |
| Tax-free redundancy threshold | £30,000 | £30,000 |
| Statutory holiday entitlement (full-time) | 5.6 weeks | 5.6 weeks |
| 12.07% method (irregular hours) | unchanged | unchanged |
| SSP weekly rate | £116.75 | £118.75 |
| Lower earnings limit (SSP qualifying) | £123 | £125 |

(Source: gov.uk, ACAS, HMRC employer bulletins.)

## Bookmark the cluster

If you found one of these useful, the full list of UK calculators (income tax, NI, child benefit, ISA, pension allowance, etc.) is at:

→ **https://tool.teamzlab.com/uk/**

All free, all browser-based, no email required. If you want updates when the April 2026 rates land, the homepage has a quiet RSS feed at https://tool.teamzlab.com/feed.xml.
