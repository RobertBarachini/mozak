---
title: "Research: keyless reads of X and Reddit for an agent, checked 2026-11-10"
type: source
domain: [meta]
medium: report
author: interactive agent session (Claude Opus 5.5), probes from the harness's built-in fetch and web-fetch.py
retrieved: 2026-11-10
created: 2026-11-10
updated: 2026-11-10
tags: [founding, tooling]
---

# Research: keyless reads of X and Reddit for an agent, checked 2026-11-10

Internal agent-generated research, so no `url:` (schema exception for `medium: report`). The
question: when an agent needs an X post, an account's recent posts, or a subreddit's recent
activity, which routes answer with no key, no login and no challenge, as of 2026-11-10. Both
platforms closed most logged-out reading during 2026, and an instance's research run that day
found the no-login frontends walled off from scripts; this capture re-measures only what a
ladder row needs. Every probe was one request, first through the harness's built-in fetch and,
where that client was refused, through `web-fetch.py` at T1, per the default-client rule in
[[mozak-web-acquisition-ladder]]. No probe was retried, and no challenge was attempted.
Distilled into the ladder's social-platforms row of the T0 roster.

## 1. Routes that answered with JSON, no key, no login, no challenge

Probed between 09:58 and 10:10 UTC with the built-in fetch.

| Endpoint | Result |
|---|---|
| `https://api.fxtwitter.com/2/profile/NASA/statuses` | 200 JSON, top-level keys `code`, `results`, `cursor`; newest post id `2119846862286930036`, created 2026-11-09 17:37:31 UTC |
| `https://api.fxtwitter.com/2/profile/NASA` | 200 JSON, keys `code`, `message`, `user`; `user.screen_name` "NASA" |
| `https://api.fxtwitter.com/NASA/status/2119846862286930036` | 200 JSON, keys `code`, `message`, `tweet`; same id and creation time |
| `https://cdn.syndication.twimg.com/tweet-result?id=2119846862286930036&token=a` | 200 JSON from X's own embed endpoint, with an arbitrary `token` value; keys include `id_str`, `created_at`, `text`, `user`, `mediaDetails` |
| `https://arctic-shift.photon-reddit.com/api/posts/search?subreddit=linux&limit=5` | 200 JSON, a `data` list; newest post created 2026-11-10 09:58:03 UTC, its record retrieved by the archive at 09:58:24 UTC |
| `https://arctic-shift.photon-reddit.com/api/comments/search?subreddit=linux&limit=5` | 200 JSON, a `data` list; newest comment created 2026-11-10 09:58:08 UTC |

FxTwitter (the FxEmbed project) and X's syndication endpoint serve embeds; Arctic Shift is a
Reddit archive, so it trailed the live site by seconds here, not zero.

## 2. Routes that refused

| Endpoint | Built-in fetch | `web-fetch.py` T1 (10:09 UTC) |
|---|---|---|
| `https://api.vxtwitter.com/NASA/status/2119846862286930036` | 403 | 403, Cloudflare "Just a moment..." interstitial; its `robots.txt` also 403 |
| `https://www.reddit.com/r/linux/.json` | refused by the harness ("unable to fetch from www.reddit.com") | 403 |
| `https://old.reddit.com/r/linux/` | refused by the harness, same message | 200, title "Welcome to Reddit", 340,795 bytes of HTML with no extractable text: a script shell |
| `https://nitter.tiekoetter.com/NASA` (a Nitter instance) | 200, Anubis "Access Denied" challenge page | not sent: the row needed no further probe |
| `https://nitter.catsarch.com/NASA` (a Nitter instance) | 429 | not sent, as above |
| `https://redlib.catsarch.com/r/linux`, `https://redlib.freedit.eu/r/linux` (Redlib instances) | refused by the harness's permission classifier, as walled content read through a copy | not sent: a harness refusal is not routed around through another client |

## Stop record

Stopped at decision sufficiency for one roster row: each route in section 1 answered a single
request with structured JSON, and each route in section 2 answered in a way the ladder treats as
final (a challenge, a 403, a rate limit) or was refused by the harness itself. Not checked: the
rate limits of FxTwitter, the syndication endpoint and Arctic Shift; Arctic Shift's query scope
(whether one search can span subreddits); terms of use beyond the absence of a key; and whether
the frontend instances serve content in a human's own browser, which their challenges are built
to allow.

## Distilled into

- [[mozak-web-acquisition-ladder]] — the social-platforms row of the T0 roster.
