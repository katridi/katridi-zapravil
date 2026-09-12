# Agent Instructions

## Project Overview

This repository contains the website and publishing infrastructure for the Russian-language podcast **“Катриди заправил”**.

The podcast consists of original stories by Alexey Katridi, read by different guest voices.

The project is intentionally lightweight and should remain easy to understand, maintain, and migrate.

## Current Architecture

The repository is public.

The website is a static site published with GitHub Pages.

Current publishing model:

```text
GitHub repository
        ↓
GitHub Pages
        ↓
Podcast website

Cloudflare R2
        ↓
Podcast audio files
```

The long-term architecture may also include a self-generated podcast RSS feed distributed to:

- Yandex Music
- Spotify
- Apple Podcasts
- YouTube / YouTube Music

Do not introduce additional infrastructure unless it is clearly necessary.

## Core Principles

Prefer:

- static files;
- simple HTML and CSS;
- minimal JavaScript;
- explicit configuration;
- portable formats;
- standard RSS;
- infrastructure that can be migrated easily;
- solutions that remain understandable without specialized tooling.

Avoid unnecessary frameworks, databases, backend services, package managers, build systems, or third-party dependencies.

If something can be implemented cleanly with plain HTML, CSS, YAML, and a small Python script, prefer that approach.

## Repository Structure

The intended structure is approximately:

```text
/
├── index.html
├── style.css
├── assets/
│   └── ...
├── episodes/
│   └── ...
├── scripts/
│   └── ...
├── README.md
├── AGENTS.md
└── .gitignore
```

Not all directories may exist yet.

Do not create directories or abstractions before they are needed.

## Website

The website is static and should work correctly on GitHub Pages.

Requirements:

- responsive layout;
- readable on mobile;
- no required JavaScript for basic navigation or content;
- no external framework unless explicitly requested;
- use relative paths where appropriate so GitHub Pages deployment continues to work;
- preserve good semantic HTML;
- maintain accessible contrast and labels;
- avoid unnecessary animations or visual effects.

The visual style should remain restrained and editorial rather than looking like a generic SaaS landing page.

## Podcast Content

The podcast language is Russian.

Repository documentation and developer-facing instructions may be written in English or Russian.

Public-facing podcast titles, descriptions, episode names, reader names, and other editorial content should preserve the original Russian spelling.

Do not translate podcast content unless explicitly requested.

## Episode Metadata

Eventually, episode metadata may be stored as YAML files under:

```text
episodes/
```

A possible episode structure:

```yaml
title: "Щенок"
season: 1
episode: 1

author: "Алексей Катриди"
reader: "Сергей Глебкин"

guid: "kz-s01e01"

date: "2026-09-20T09:00:00+03:00"

audio:
  url: "https://audio.example.com/s01/s01e01-shchenok.mp3"
  type: "audio/mpeg"

description: >
  Рассказ Алексея Катриди.
  Читает Сергей Глебкин.
```

### GUID Rule

Once an episode is publicly released, its GUID is permanent.

Never change the GUID of a published episode.

Do not automatically regenerate GUIDs from titles, filenames, dates, or URLs.

Changing a published GUID may cause podcast platforms to interpret an existing episode as a new episode.

## Audio

Do not store podcast audio files in GitHub.

The `.gitignore` intentionally excludes common audio formats.

Archive master:

```text
WAV
mono
48 kHz
24-bit
```

Current distribution target:

```text
MP3
mono
48 kHz
CBR 192 kbps
```

The 192 kbps value is a project preference, not a universal platform requirement.

Audio files should eventually be served from Cloudflare R2 or another dedicated audio host.

Do not silently transcode, normalize, resample, or otherwise modify podcast audio.

## Artwork

Main podcast artwork target:

```text
3000 × 3000 px
JPG or PNG
no transparency
```

Do not replace or modify official artwork unless explicitly requested.

Placeholder artwork may be used during development but should be clearly identifiable as a placeholder.

## RSS

The project may eventually generate its own RSS feed.

When working on RSS, prioritize compatibility with:

1. Yandex Music
2. Spotify
3. Apple Podcasts
4. YouTube / YouTube Music

The RSS feed must remain standards-based and portable.

Important rules:

- every published episode must have a stable GUID;
- enclosure URLs must be publicly accessible;
- published episode URLs should not change unnecessarily;
- preserve publication dates;
- preserve metadata when rebuilding the feed;
- RSS must be accessible without authentication;
- do not introduce platform-specific behavior that breaks standard RSS readers.

Do not manually edit generated RSS if a generator becomes the source of truth.

## Deployment

GitHub Pages currently deploys the website from the `main` branch.

A normal website update should require only:

```bash
git add .
git commit -m "Describe the change"
git push origin main
```

Do not introduce a custom deployment system unless there is a concrete need.

If GitHub Actions are later added, keep workflows small and understandable.

## Secrets and Credentials

Never commit:

- API tokens;
- Cloudflare credentials;
- passwords;
- private keys;
- billing credentials;
- `.env` files containing secrets.

Use GitHub Secrets if automation later requires credentials.

Never print secrets into generated files, logs, HTML, RSS, or GitHub Actions output.

## Cloudflare

Cloudflare R2 may eventually host public podcast audio.

The preferred design is deliberately simple:

```text
Custom domain
     ↓
Cloudflare cache
     ↓
R2 Standard bucket
```

Avoid introducing Workers, D1, KV, Queues, R2 SQL, or other usage-based Cloudflare products unless explicitly required.

The goal is to minimize both operational complexity and unexpected usage-based billing.

Do not expose a development `r2.dev` endpoint as the permanent production audio URL.

## Cost Awareness

This is an independent podcast project.

Prefer solutions with:

- predictable costs;
- free static hosting where appropriate;
- minimal recurring infrastructure;
- no unnecessary SaaS subscriptions;
- no usage-based services unless their billing behavior is understood.

Before introducing a paid dependency, explain:

1. why it is needed;
2. its recurring cost;
3. whether pricing is usage-based;
4. whether there is a hard spending limit;
5. how difficult it would be to remove later.

## Migration Safety

The project should remain easy to migrate to a managed podcast host such as mave+, Castos, Captivate, or another standard RSS host.

Do not design the system in a way that prevents future migration.

Important migration invariants:

- preserve episode GUIDs;
- preserve original masters;
- retain control over the project domain;
- use standard RSS;
- keep episode metadata in portable files;
- avoid proprietary metadata when a standard alternative exists.

If the RSS URL ever changes, use a permanent HTTP 301 redirect where appropriate.

## Git Practices

Make small, focused changes.

Before committing:

- inspect `git status`;
- do not include generated junk or local files;
- do not commit audio files;
- do not commit secrets;
- avoid unrelated formatting changes.

Use descriptive commit messages, for example:

```text
Add initial podcast homepage
Add episode metadata structure
Generate RSS feed from episode YAML
Update podcast artwork
Add platform links
```

Do not rewrite published Git history unless explicitly requested.

## Change Policy

Before making a significant architectural change, first explain:

- what problem it solves;
- what new dependency it introduces;
- whether it affects GitHub Pages;
- whether it affects podcast RSS compatibility;
- whether it changes ongoing costs;
- whether it makes future migration harder.

For small HTML/CSS/content changes, proceed directly.

## Validation

Before considering a change complete:

### Website changes

Check:

- desktop layout;
- mobile layout;
- relative URLs;
- missing assets;
- obvious accessibility issues.

### RSS changes

Check:

- valid XML;
- required channel metadata;
- unique and stable episode GUIDs;
- valid enclosure URLs;
- correct MIME types;
- correct publication dates;
- correct episode ordering.

### Infrastructure changes

Check:

- no secrets were introduced;
- no unexpected paid service was enabled;
- deployment remains reproducible;
- migration remains possible.

## Priority

When there is a choice between a clever solution and a boring, portable, understandable solution, choose the boring one.