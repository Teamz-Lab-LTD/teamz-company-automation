# skills/ — Claude skills that travel with this submodule

Two self-contained Claude Code skills, symlinked into `~/.claude/skills/` by `setup-symlinks.sh`: **teamz-design-bridge** (rewrites generic UI advice into Teamz brand-token-compliant code) and **teamz-ux-research** (evidence-based UX research with rigor rules). They auto-activate on UI / research requests — an intern never invokes them manually.

| File | What it does | Typical command |
|---|---|---|
| [`teamz-design-bridge/SKILL.md`](./teamz-design-bridge/SKILL.md) | Skill that rewrites generic UI suggestions into Teamz Lab brand-token-compliant code. | — |
| [`teamz-design-bridge/platforms/flutter.md`](./teamz-design-bridge/platforms/flutter.md) | Maps abstract design tokens to team_mvp_kit Flutter widgets and context accessors. | — |
| [`teamz-design-bridge/platforms/nextjs-tw.md`](./teamz-design-bridge/platforms/nextjs-tw.md) | Maps design tokens to Next.js plus Tailwind CSS custom properties and config. | — |
| [`teamz-design-bridge/platforms/plain-css.md`](./teamz-design-bridge/platforms/plain-css.md) | Maps design tokens to vanilla HTML/CSS custom properties without Tailwind. | — |
| [`teamz-design-bridge/platforms/wordpress.md`](./teamz-design-bridge/platforms/wordpress.md) | Maps design tokens to WordPress theme.json palette and typography slugs. | — |
| [`teamz-design-bridge/rules/a11y.md`](./teamz-design-bridge/rules/a11y.md) | WCAG 2.1 AA rules for contrast, touch targets, and states every generated UI must meet. | — |
| [`teamz-design-bridge/rules/banned.md`](./teamz-design-bridge/rules/banned.md) | Lists color/UI patterns that produce illegible or off-brand output and must never be emitted. | — |
| [`teamz-design-bridge/rules/contrast.md`](./teamz-design-bridge/rules/contrast.md) | Core rule: always pair every background with its matching foreground on-token. | — |
| [`teamz-design-bridge/tokens.json`](./teamz-design-bridge/tokens.json) | Stack-agnostic design tokens (colors, typography) with their roles and contrast pairings. | — |
| [`teamz-ux-research/SKILL.md`](./teamz-ux-research/SKILL.md) | Skill conducting rigorous UX research: planning, discovery, testing, synthesis, recommendations. | — |
| [`teamz-ux-research/methods/01-planning.md`](./teamz-ux-research/methods/01-planning.md) | How to write a research plan before any observation; cites the research-plan template. | — |
| [`teamz-ux-research/methods/02-interviews.md`](./teamz-ux-research/methods/02-interviews.md) | Generative and JTBD interview method with a 30-minute session structure. | — |
| [`teamz-ux-research/methods/03-usability-testing.md`](./teamz-ux-research/methods/03-usability-testing.md) | When and how to run usability tests watching real users attempt real tasks. | — |
| [`teamz-ux-research/methods/04-thematic-analysis.md`](./teamz-ux-research/methods/04-thematic-analysis.md) | Braun and Clarke thematic analysis plus affinity mapping to turn observations into findings. | — |
| [`teamz-ux-research/methods/05-severity-rubric.md`](./teamz-ux-research/methods/05-severity-rubric.md) | Nielsen 0-4 severity scale for scoring and prioritizing usability issues. | — |
| [`teamz-ux-research/methods/06-personas.md`](./teamz-ux-research/methods/06-personas.md) | JTBD-flavored persona format anchoring design decisions to a real user job. | — |
| [`teamz-ux-research/methods/07-journey-maps.md`](./teamz-ux-research/methods/07-journey-maps.md) | Journey map format walking a persona through a goal to surface experience breaks. | — |
| [`teamz-ux-research/methods/08-competitive-audit.md`](./teamz-ux-research/methods/08-competitive-audit.md) | Structured competitor and Nielsen-heuristic audit to find patterns without user sessions. | — |
| [`teamz-ux-research/methods/09-accessibility.md`](./teamz-ux-research/methods/09-accessibility.md) | Accessibility as a research method; minimum pre-launch audit per surface. | — |
| [`teamz-ux-research/rules/no-fabrication.md`](./teamz-ux-research/rules/no-fabrication.md) | Never invent quotes, metrics, or findings; every claim cites evidence or is labeled hypothesis. | — |
| [`teamz-ux-research/rules/reflexivity.md`](./teamz-ux-research/rules/reflexivity.md) | Every research plan must declare the researcher's biases before collecting data. | — |
| [`teamz-ux-research/rules/triangulation.md`](./teamz-ux-research/rules/triangulation.md) | No recommendation ships unless the finding appears across two-plus independent sources. | — |
| [`teamz-ux-research/templates/ab-test-plan.md`](./teamz-ux-research/templates/ab-test-plan.md) | Template for A/B test plans on any recommendation with severity two or higher. | — |
| [`teamz-ux-research/templates/discussion-guide.md`](./teamz-ux-research/templates/discussion-guide.md) | Fill-in moderated session discussion guide with pre-session moderator checklist. | — |
| [`teamz-ux-research/templates/persona-card.md`](./teamz-ux-research/templates/persona-card.md) | One-card-per-persona template storing JTBD and validation status. | — |
| [`teamz-ux-research/templates/recommendation-matrix.md`](./teamz-ux-research/templates/recommendation-matrix.md) | Matrix template scoring each recommendation by severity, effort, and priority. | — |
| [`teamz-ux-research/templates/research-plan.md`](./teamz-ux-research/templates/research-plan.md) | Fill-in research plan template covering objectives and research questions. | — |
| [`teamz-ux-research/templates/tree-test.md`](./teamz-ux-research/templates/tree-test.md) | Tree-test plan template to validate navigation labels and hierarchy before build. | — |

---
**Lost?** The repo-wide index lives in [`../README.md`](../README.md) (root README, section 5) and the agent rulebook in [`../CLAUDE.md`](../CLAUDE.md). This folder's table above is the complete list — every file here is in it.
