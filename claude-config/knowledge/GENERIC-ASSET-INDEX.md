# Generic Asset Index — everything reusable across Teamz Lab apps, A–Z

**Read this before writing anything you suspect already exists.** Every entry below is
generic: it belongs to no single app and should never be re-derived inside one.

This index exists because reusable work kept getting lost. Not deleted — *lost*: a guide
written for one app, a strategy doc pasted into one repo, a helper built twice because the
first one was three directories away and nobody knew its name. The cost is invisible until
a session re-solves a solved problem and ships a second, subtly different answer.

## What this file is NOT

It does **not** index the automation scripts. There are 111 of them and
[`automation-tool-registry.md`](../../automation-tool-registry.md) already maps every task
to the exact script — **read that one before any ASO/SEO/automation task.** This file
covers everything that registry does not: guides, strategy, skills, commands, memory,
hooks, and generic code still trapped inside app repos.

## Where things live, and why

| Home | Holds | Reaches a project by |
|---|---|---|
| `teamz-company-automation/claude-config/` | Strategy, Claude config, company-wide knowledge | `setup-symlinks.sh` |
| `teamz-company-automation/{py,sh,skills}/` | Scripts and skills | `setup-symlinks.sh` → `scripts/` |
| `team_mvp_kit/prompts/` | Engineering + release guides | The kit is a submodule of every app |
| `team_mvp_kit/lib/` | Shared Flutter code | Dart dependency |

**Two homes for documents is one too many, and it is a known debt.** `team_mvp_kit` is
shared Dart code owned by a teammate and consumed by other apps; strategy documents drifted
into its `prompts/` folder because that folder reaches every app. The automation repo is the
better home (it is not a package, and it is where Claude config already lives), but moving
anything out of the kit needs the kit owner's agreement — never do it unilaterally.

**Live duplicate, tracked deliberately:** the Shipaton knowledge base exists in *both*
`claude-config/knowledge/` and `team_mvp_kit/prompts/shipaton-2026-knowledge-base.md`. The
bodies are byte-identical; the kit's copy carries an extra provenance header. If you edit
one, edit both, or the "locked" plan quietly forks.

---

## A–Z

### Strategy & competition

| Asset | Where | Reach for it when |
|---|---|---|
| **RevenueCat Growth Playbook** | `claude-config/knowledge/RevenueCat_Growth_Playbook.md` | You need the evidence behind a monetization number. Static appendix — it names no app. |
| **Shipaton 2026 Knowledge Base** | `claude-config/knowledge/Shipaton_2026_Knowledge_Base.md` (mirror: `team_mvp_kit/prompts/shipaton-2026-knowledge-base.md`) | **Any** Shipaton question. It is the authority and it OUTRANKS per-app plan files. §9.2 = locked tracks; §9.3 = weekly calendar; §9.6 = Resume Coach is shelved Plan B. |
| **Money Machine 2026–2027** | `MONEY_MACHINE_2026_2027.md` | Long-range revenue plan across properties. |

### Claude configuration

| Asset | Where | Reach for it when |
|---|---|---|
| **`/aso-refresh` command** | `claude-config/commands/aso-refresh.md` | ANY ASO task. Mandatory entry point — never run ASO scripts by hand. |
| **ASO bash guard (hook)** | `claude-config/hooks/aso-bash-guard.sh` | Already active; blocks ASO scripts run outside the skill. |
| **ASO cadence (memory)** | `claude-config/memory/aso_cadence.md` | Deciding SIGNAL_ONLY vs FULL_REWRITE. 14d signal / 28d iOS / 56d Android. |
| **ASO screenshot compliance (memory)** | `claude-config/memory/aso_screenshot_compliance.md` | Before generating or submitting store screenshots. |
| **CLAUDE.md additions** | `claude-config/CLAUDE-md-additions.md` | Setting up a new machine. Paste manually — deliberately not symlinked. |
| **Per-app workflow** | `claude-config/PER-APP-WORKFLOW.md` | Onboarding a NEW app repo into this tooling. |
| **Skill invocation audit (hook)** | `claude-config/hooks/skill-invocation-audit.sh` | Auditing which skills actually fired. Log: `~/.config/teamzlab/audit/skill-invocations.log`. |

### Skills

| Asset | Where | Reach for it when |
|---|---|---|
| **teamz-design-bridge** | `skills/teamz-design-bridge/` | Turning any generic UI advice into Teamz-brand-consistent code. Auto-fires on UI work. |
| **teamz-ux-research** | `skills/teamz-ux-research/` | Research, redesign, audit, journey, persona, usability work. |

### Engineering guides (in `team_mvp_kit/prompts/`)

| Asset | Reach for it when |
|---|---|
| **ai-agent-instructions** | Setting the house rules for an AI agent on a Teamz project. |
| **ai-fluency-meta-prompt** | Improving how a developer prompts. |
| **aso-store-publish-guide** | Publishing to the stores. Pair with `/aso-refresh`. |
| **behavioral-observability** | Instrumenting real user behaviour, not vanity events. |
| **cloud-kit-setup** | Wiring `@teamzlab/cloud-kit` (Cloud Functions layer). |
| **flutter-development-standards** | The baseline every Flutter app here follows. Read before writing app code. |
| **flutter-project-initial-setup** | Day one of a new Flutter app. |
| **flutter-web-development-guide** | Anything Flutter Web. |
| **full-project-spec-from-research** | Turning research into a full project spec. |
| **fvm-setup-guide** | Pinning the Flutter version. Every app here is FVM-pinned. |
| **iap-bootstrap-guide** | Standing up in-app purchases. |
| **icon-prompt-template** | Generating an app icon. Pair with `tool/build_icons.py` in the app. |
| **ios-release-guide** | An iOS App Store release. |
| **llm-test-runner** | Consuming the Teamz JSON test report. |
| **monetization-settings-guide** | Paywall + settings configuration. |
| **onboarding-test-coverage** | The onboarding test plan any new app must pass. |
| **pre-launch-checklist** | Before ANY launch. Run it in full. |
| **rate-limiting-setup** | Server-side rate limiting. |
| **smart-review-rating-setup** | In-app review prompts, done honestly. |
| **store-app-registration-guide** | First-time app registration on either store. |
| **teamz-lab-api-integration-prompts** | Clean-architecture API integration. |
| **teamz-ui-generation-guide** | Generating UI that matches the design system. |
| **testing-strategy-and-helpers** | Test strategy + the kit's helpers. Read before writing tests. |

### Operations

| Asset | Where | Reach for it when |
|---|---|---|
| **AGENTS.md** | `AGENTS.md` | Agent conventions for the automation repo. |
| **Automation tool registry** | `automation-tool-registry.md` | **MANDATORY before any automation task.** 111 scripts mapped task → script. |
| **ASO script registry** | `claude-config/aso-script-registry.md` | Which ASO *and* leading-indicator SEO scripts feed a refresh. Sections I–N list the SEO ones — skipping them is the known historical failure. |
| **Hostinger VPS deploy** | `HOSTINGER-VPS-DEPLOY.md` | Deploying to the VPS. |
| **How to ASO a new app** | `HOW-TO-ASO-NEW-APP.md` | Registering a new app slug (`.teamz-automation.env`, `TEAMZ_APP_SLUG`). |
| **setup-symlinks.sh** | `setup-symlinks.sh` | Once per app project, and after cloning on a new machine. Links scripts, skills, commands, memory, hooks and knowledge into place. |

---

## Generic code still living inside app repos

Not yet extracted, and therefore easy to miss or rebuild. Listed so the next person finds it
before writing a second version. Extraction into `team_mvp_kit` needs the kit owner's
agreement — do not move these unilaterally.

| What | Currently in | Why it is generic |
|---|---|---|
| **Document pipeline** — tolerant markdown parser → structured document → measured typesetter → PDF / DOCX / plain text | `ai_resume_checker/lib/src/data/services/documents/` + `document_markdown_parser.dart` | Nothing in it knows what a resume is. It word-wraps mixed-weight runs, sets values flush right with real tab stops, paginates with widow/orphan and keep-with-next rules, embeds fonts, and writes valid OOXML by hand using `archive` alone. Any app that turns markdown into a sendable document wants this. ~2,000 lines, ~90 tests. |
| **Paper sheet** — painted-grain document surface | `ai_resume_checker/lib/src/common_ui/paper/paper_sheet.dart` | Deterministic seeded grain, light + dark. No app-specific content. |
| **Motion tokens** — reduce-motion-aware duration set | `ai_resume_checker/lib/src/core/motion/motion.dart` | `Motion.of(context)` collapses to zero durations under the OS reduce-motion flag. Every app needs this and most apps forget it. |
| **Icon builder** | `ai_resume_checker/tool/build_icons.py` | Renders launcher icons from an SVG mark, asserts the Android adaptive safe zone, strips iOS alpha. Only the mark itself is app-specific. |

---

## Keeping this file honest

- Add an entry the moment you create something generic — not "later".
- If an entry stops being true, fix it in the same commit that made it untrue.
- Never duplicate a document to make it easier to find. Add a row here instead; that is
  what this file is for.
