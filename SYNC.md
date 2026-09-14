# SYNC — template ↔ instance contract

One public **template** repo (the generic system) and any number of private
**instance** repos (living graphs). Git is the sync machinery: each instance keeps
the template as a remote named `template` (a local sibling path like
`../mozak` works and is recommended — offline-friendly; a GitHub URL works too).
Agents never push in either repo; humans review drafted commits and push.

## Ownership

| Class | Paths | Merge-conflict resolution |
|---|---|---|
| **Template-owned** | `tools/` (except `tools/recipes/local/` — instance-owned, never shipped, never auto-upstreamed), `templates/`, `CLAUDE.md`, `.claude/skills/` (agent-harness lenses the template ships; per-machine Claude state stays gitignored and local), `.gitignore`, `.github/`, `LICENSE`, `CHANGELOG.md`, `ROADMAP.md`, and the **meta pages** — every pages/*.md the template ships (the template's own pages listing IS the roster, per AGENTS rule 9 no copy is maintained here; the ownership guard resolves it dynamically from the template remote) except (`pages/start-here.md` — the birth seed, instance-owned below) | Take template's side. Instances don't edit these; a needed change is made in the template (or upstreamed first). Instances annotate a meta page by **linking to it from their own notes** — backlinks are derived, so the connection surfaces without editing the shared body. |
| **Shared-evolving** | `AGENTS.md`, `SYNC.md`, `conventions/frontmatter-schema.md`, `SETUP.md` (body) | Merge by intent: system-generic content follows the template; instance-specific lines stay. Any generalizable improvement made instance-side MUST be upstreamed (see ritual below) — otherwise the repos drift apart permanently. |
| **Instance-owned** | All other `pages/` — including `pages/start-here.md`, the instance's front door and domain index: a template-authored **birth seed**, shipped at instantiation and never updated by the template afterwards — `journals/`, `sources/` (except its README and the template-shipped research captures tagged `founding` — the public evidence core behind the design's claims), `raw/`, `assets/`, `.private/`, and `.personal-shared/` contents (all gitignored; the template ships only their READMEs / `.gitkeep` markers), `archive/` content (except its README), `README.md` | Keep instance's side. The template never ships content here. (`_generated/` is gitignored on both sides — derived, never merged.) |

**Enforced by** `python3 tools/graph.py ownership`: advisory in the rule-7 `check`
bracket, opt-in pre-commit hard gate (SETUP). An *instance* is any repo with a
`template` remote; the guard is a no-op in the template itself. A file whose working
content is byte-identical to the template's is never flagged (it is a sync receipt,
not local authorship — so a pull-in-progress stays clean even with the hook on).

**Some things belong in neither tree.** A gitignored path is still *inside* the repo: a
backup copies it, a `grep -r` walks it, and one `.gitignore` edit tracks it. Secrets
that were not made for this repo — API keys, proxy passwords, a daily browser's profile —
therefore live **outside the repo entirely**, in the environment, the OS keyring, or an XDG
state dir; `.personal-shared/` holds the *pointer* (path, port, variable name), never the
secret, and a tool that needs one resolves it from the environment and refuses a path
inside the repo root. **One deliberate exception:** a credential the user exports *for*
this research — `.personal-shared/cookies.txt`, a Netscape cookie jar from a private window
logged into only the sites the work needs. Placing it there is the user's explicit choice,
gitignored, knowing the guarantee is negative; tools read it in place, never copy it into
`_generated/`, never log a value. Three placements, then: **tracked** (shared, upstreamable),
**gitignored** (instance-local, user-visible — including a research cookie jar the user chose
to keep here), **outside** (everything credential-bearing that was not exported for this
purpose).

**Stem collisions.** All wikilink stems share one namespace, so a template release can
ship a new meta page whose stem an instance already used. After `git fetch template`
the ownership guard reports such files as STEM-COLLISION (present in the template
roster, absent at the merge-base): rename the instance note first —
`python3 tools/graph.py rename <stem> <new-stem>` — then merge; the template owns its
stems. Mechanical domain lookup is likewise derivable, never maintained:
`python3 tools/graph.py domains`.

**Gitignored ⇒ instance-local.** A path either side git-ignores is never synced in
either direction, so the template can neither ship nor overwrite it — yet it stays
visible in the working tree. "User-visible but never touched by upstream" therefore
needs no per-folder rule; it falls out of the gitignore for `_generated/` (incl.
`presentations/`), `raw/` and `assets/` contents, and the `.private/` /
`.personal-shared/` zones alike.

**Privacy boundary (hard rule):** the template is public — instance content, personal
facts, and instance-specific references never flow upstream. Generalize before
upstreaming: strip names, dates-of-use, domain content, founding-capture wikilinks.

## Known birth divergences (expected, permanent)

- `README.md` — template describes the system; an instance describes itself.
- `SETUP.md` — template opens with bootstrap-from-template; an instance opens with
  its own provenance note.
- `start-here.md` — a **birth seed**: the template ships the empty front door, then
  never updates an instance's copy again (template-side edits reach only future
  instances). The instance owns it outright — its `## Domains` index grows there.
  On a pull, any conflict here resolves keep-ours, wholesale.
- Instances have `journals/*.md`, their own `sources/*.md`, `archive/` content
  (e.g. a founding archive); the template ships only the directory READMEs, the
  `journals/.gitkeep`, the `.private/` and `.personal-shared/` `.gitkeep` markers,
  and the founding-research capture (public evidence core).

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
  dangerous changes (a renamed rule a kept instance line still references, a schema change
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

The `ownership` guard (advisory in `check`, hard in the opt-in hook) is what surfaces the
need for this ritual — it flags a template-owned file authored in an instance.

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
