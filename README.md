# skills

Agent skills in the open [SKILL.md](https://agentskills.io) format.

| Skill | What it does |
|---|---|
| [unifi-repair](skills/unifi-repair/SKILL.md) | Board-level repair and diagnostics for Ubiquiti UniFi hardware: annotated board photos, interactive bench worksheets, DigiKey part lookups, console and boot-log diagnostics. |

## Install

```bash
npx skills add alxgmpr/skills
```

Add `-s unifi-repair` to pick one skill, `-a <agent>` to pick the agent, `-g` to install for your user instead of the current project.

## unifi-repair requirements

- [uv](https://docs.astral.sh/uv/) to run the bundled Python scripts (`annotate.py` pulls in Pillow on its own; `dk.py` is stdlib only).
- For DigiKey lookups: a DigiKey production API app, with `DIGIKEY_CLIENT_ID` and `DIGIKEY_CLIENT_SECRET` in the environment or in `~/.config/secrets.env`.
- The device notes and bench assumptions come from one person's repairs. Treat `references/devices.md` as a starting point and add your own units.

## Repo layout

- `skills/<name>/` is what gets installed.
- `evals/<name>/` holds test cases (prompt, expected outcome, graders, input files). They are not installed with the skill.
