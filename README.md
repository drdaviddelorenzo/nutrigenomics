# Nutrigenomics — Agent Skill

Personalised nutrition reports from consumer genetic data (23andMe, AncestryDNA, VCF),
computed entirely on your own machine. This repository is the **canonical source** for the
skill; the ClawHub and Hermes listings are published from here.

The skill itself lives in **[`skills/nutrigenomics/`](skills/nutrigenomics/)** — see its
[README](skills/nutrigenomics/README.md) for what it does, and
[`SKILL.md`](skills/nutrigenomics/SKILL.md) for the agent-facing instructions.

## Install

**Hermes Agent** — add this repository as a tap, then install:

```bash
hermes skills tap add drdaviddelorenzo/nutrigenomics
hermes skills install nutrigenomics
```

**OpenClaw / ClawHub:**

```bash
openclaw skills install @drdaviddelorenzo/nutrigenomics
```

**Manually** — copy `skills/nutrigenomics/` into your agent's skills directory
(`~/.hermes/skills/` for Hermes, `~/.claude/skills/` for Claude Code).

## Repository layout

```
skills/nutrigenomics/                     the skill (SKILL.md, scripts, SNP panel, tests)
.github/workflows/publish-clawhub.yml     publishes to ClawHub on merge to main
LICENSE.txt                               MIT
```

The `skills/` layout is what **both** registries expect, which is why it is fixed:
`hermes skills tap add` looks for skills under `skills/<skill-name>/` and exposes no option to
point elsewhere, and ClawHub's publish workflow defaults to the same `skills` root. ClawHub also
requires the skill's `name` to match its parent directory. Moving this folder breaks both.

## Keeping the copies in sync

This repository is the only place the skill is edited. Both registries are fed from it:

| Target | How it is fed | Trigger |
|---|---|---|
| **ClawHub** | `.github/workflows/publish-clawhub.yml` | merge to `main` touching `skills/**` |
| **Hermes skills hub** | `hermes skills tap add drdaviddelorenzo/nutrigenomics` | `hermes skills update` |

`SKILL.md` is deliberately **platform-neutral**: it documents commands as paths relative to the
skill's own directory, and names each platform's convention for resolving them
(`${HERMES_SKILL_DIR}` for Hermes, `{baseDir}` for OpenClaw) rather than hard-coding either. A
previous hand-edited Hermes copy drifted from this repository for six weeks precisely because
those tokens were being substituted by hand — do not reintroduce per-platform copies.

**Bump the `version` in `SKILL.md` frontmatter for every published change.** ClawHub publishes
are fingerprinted and versioned; leaving two different file sets on the same version number is
what makes drift invisible.

## Licence

MIT — see [LICENSE.txt](LICENSE.txt). Attribution, citation formats and data-source credits are
in [ATTRIBUTION.md](skills/nutrigenomics/ATTRIBUTION.md).

> **Disclaimer:** educational and research use only. Not medical advice.
