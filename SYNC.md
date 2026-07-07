# SYNC — template ↔ instance contract

One public **template** repo (the generic system) and any number of private
**instance** repos (living graphs). Git is the sync machinery: each instance keeps
the template as a remote named `template` (a local sibling path like
`../mozak` works and is recommended — offline-friendly; a GitHub URL works too).
Agents never push in either repo; humans review drafted commits and push.

## Ownership

| Class | Paths | Merge-conflict resolution |
|---|---|---|
| **Template-owned** | `tools/` (except `tools/recipes/local/` — instance-owned, never shipped, never auto-upstreamed), `templates/`, `CLAUDE.md`, `.gitignore`, `.github/`, `LICENSE` | Take template's side. Instances don't edit these; a needed change is made in the template (or upstreamed first). |
| **Shared-evolving** | `AGENTS.md`, `SYNC.md`, `conventions/frontmatter-schema.md`, `SETUP.md` (body), and the **bodies** of every meta-domain page the template ships (the rule is generic — any `pages/*.md` present in the template is shared; the template's `pages/` listing IS the roster, per AGENTS rule 9 no copy of it is maintained here) | Merge by intent: system-generic content follows the template; instance-specific lines stay. Any generalizable improvement made instance-side MUST be upstreamed (see ritual below) — otherwise the repos drift apart permanently. |
| **Instance-owned** | All other `pages/`, `journals/`, `sources/` (except its README and the template-shipped founding-research capture — the public evidence core behind the design's claims), `raw/` and `assets/` contents (both gitignored; the template ships only their READMEs), `archive/` content (except its README), `README.md`, plus two designated zones inside shared pages: the `## Domains` list in `start-here` and the `## Sources` sections of meta pages | Keep instance's side. The template never ships content here. (`_generated/` is gitignored on both sides — derived, never merged.) |

**Privacy boundary (hard rule):** the template is public — instance content, personal
facts, and instance-specific references never flow upstream. Generalize before
upstreaming: strip names, dates-of-use, domain content, founding-capture wikilinks.

## Known birth divergences (expected, permanent)

- `README.md` — template describes the system; an instance describes itself.
- `SETUP.md` — template opens with bootstrap-from-template; an instance opens with
  its own provenance note.
- Meta pages' `## Sources` — identical by default: both sides cite the
  template-shipped founding-research capture (the public evidence core, so every
  instance can dereference the design's citations). The zones stay instance-owned
  — instances may add links to their own captures.
- `start-here` `## Domains` — empty-but-for-meta in the template; grows in instances.
- Instances have `journals/*.md`, their own `sources/*.md`, `archive/` content
  (e.g. a founding archive); the template ships only the directory READMEs, the
  `journals/.gitkeep`, and the founding-research capture (public evidence core).

## Rituals

### Instance pulls the template (periodic)

```bash
git status                           # start clean — a dirty tree makes the merge uninspectable
git fetch template
git log --stat main..template/main   # INSPECT what is incoming, commit by commit
git diff main...template/main        # ...and the full content delta since the merge-base
# classify every incoming change against the Ownership table BEFORE merging
git merge template/main              # a real merge commit — never rebase or squash a sync
# conflicts: resolve per the Ownership table
python3 tools/graph.py check         # must exit 0 before finishing
# journal the sync: what came in, what was read, anything deliberately NOT taken
```

### Merge discipline (both directions)

- **Inspect, then merge — never blind-automerge.** A clean git merge is not
  evidence of semantic correctness: git flags only line collisions, while the
  dangerous changes (a renamed rule a kept zone still references, a schema change
  existing notes violate) merge silently. Read the incoming diff of every
  shared-evolving file even when git reports no conflict.
- **A sync is its own commit.** Never mix pulled template changes with content
  work; the merge commit's message summarizes what came in.
- **Rejecting an incoming change is a decision, not a resolution.** Resolving
  "ours" and forgetting guarantees the same conflict on every future pull. Either
  upstream a fix (change the template) or record the divergence in the register
  above — silent drift is the failure mode this file exists to prevent.
- **Upstream in small, single-purpose commits** — pull-time review quality is
  bounded by upstream commit hygiene.
- **Abort is cheap before commit** (`git merge --abort`); a wrong merge commit in
  a knowledge repo is expensive to unpick. When unsure: abort, read more, remerge.

### Instance upstreams an improvement

1. Identify the generalizable change (schema field, graph.py fix, new AGENTS rule,
   improved meta-page wording).
2. Re-apply it in the template checkout, generalized (privacy boundary above).
3. Run the template's own `python3 tools/graph.py check` — the template is a valid
   graph and must stay green.
4. Draft the template commit; the human commits and pushes. The change returns to
   every instance via the pull ritual — including the originating one, where the
   merge is a no-op because the content already matches.

### First stitch (one-time, only for an instance born by copy instead of clone)

```bash
# with the instance's own founding commit already made:
git fetch template
git merge -s ours --allow-unrelated-histories template/main \
  -m "chore: stitch template as upstream (birth content authoritative)"
# `-s ours` keeps the instance tree wholesale while recording the template
# commit as an ancestor — the ONE sanctioned blanket resolution. All future
# pulls are normal three-way merges against this merge-base.
```

New instances should instead be born by clone — `git clone <template> <name> &&
cd <name> && git remote rename origin template` — which makes every future merge
share history from birth. See SETUP.md.
