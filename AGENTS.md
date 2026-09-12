# Agent Instructions

## Project Overview

This repository contains the website and publishing infrastructure for the Russian-language podcast **“Катриди заправил”**.

The podcast consists of original stories by Alexey Katridi, read by different guest voices.

The project is intentionally lightweight, portable, and easy to migrate.

## Core Content Model

The primary content hierarchy is:

```text
Podcast
└── Season
    └── Episode
```

The filesystem, URLs, GUID conventions, and audio paths must be based on **season and episode numbers**, not story titles.

Story titles are editorial metadata only.

Do not use titles as stable identifiers.

## Current Architecture

```text
GitHub repository
        ↓
GitHub Pages
        ↓
Website + future RSS feed

Cloudflare R2
        ↓
Podcast audio files
```

The long-term RSS feed may be distributed to:

- Yandex Music
- Spotify
- Apple Podcasts
- YouTube / YouTube Music

Do not introduce additional infrastructure unless clearly necessary.

## Core Principles

Prefer:

- static files;
- simple HTML and CSS;
- minimal JavaScript;
- standard RSS;
- YAML for structured metadata;
- small Python scripts where automation is needed;
- portable formats;
- predictable URLs;
- infrastructure that is easy to migrate.

Avoid unnecessary:

- frontend frameworks;
- databases;
- backend services;
- package managers;
- build systems;
- third-party dependencies;
- usage-based cloud services.

If a task can be solved cleanly with HTML, CSS, YAML, and a small Python script, prefer that solution.

## Repository Structure

The intended structure is:

```text
/
├── seasons/
│   ├── season-01/
│   │   ├── episode-01/
│   │   │   └── episode.yml
│   │   ├── episode-02/
│   │   │   └── episode.yml
│   │   └── ...
│   └── season-02/
│       └── ...
│
├── assets/
│   └── ...
│
├── scripts/
│   └── ...
│
├── index.html
├── style.css
├── README.md
├── AGENTS.md
└── .gitignore
```

Do not create abstractions or directories before they are needed.

## Season and Episode Naming

Directories must use numeric identifiers:

```text
season-01/
episode-01/
```

Do not use:

```text
shchenok/
puppy/
first-story/
```

as stable filesystem identifiers.

Story titles may change. Season and episode identifiers should remain stable.

## Episode Metadata

Each episode should eventually have one canonical metadata file:

```text
seasons/season-01/episode-01/episode.yml
```

Example:

```yaml
title: "Щенок"

season: 1
episode: 1

author: "Алексей Катриди"
reader: "Сергей Глебкин"

guid: "kz-s01e01"

date: "2026-09-20T09:00:00+03:00"

audio:
  url: "https://audio.example.com/s01/e01.mp3"
  type: "audio/mpeg"

description: >
  Первый рассказ мини-сезона «Воспоминания».
  Читает Сергей Глебкин.
```

The title is editorial content.

The following are stable identifiers:

```text
season
episode
guid
```

## GUID Rules

Published GUIDs are permanent.

Preferred convention:

```text
kz-s01e01
kz-s01e02
kz-s02e01
```

Never regenerate a published GUID because of:

- a title change;
- a filename change;
- a publication-date change;
- an audio URL change;
- a website redesign.

Changing a published GUID may cause podcast platforms to treat an existing episode as a new episode.

## Episode URLs

Preferred canonical website URLs:

```text
/s01/e01/
/s01/e02/
/s02/e01/
```

Do not base permanent URLs on story titles.

Avoid:

```text
/episodes/shchenok/
/stories/shchenok/
```

for canonical episode identity.

A title may still be displayed in page headings, metadata, SEO fields, and navigation.

## Audio

Do not store podcast audio in GitHub.

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

Do not silently:

- transcode;
- normalize;
- resample;
- convert stereo/mono;
- alter loudness;
- modify metadata in a way that affects the audio pipeline.

## Audio Storage Structure

Preferred Cloudflare R2 structure:

```text
s01/
├── e01.mp3
├── e02.mp3
└── e03.mp3

s02/
├── e01.mp3
└── ...
```

Preferred URLs:

```text
https://audio.example.com/s01/e01.mp3
https://audio.example.com/s01/e02.mp3
```

Do not include story titles in permanent audio URLs unless explicitly requested.

## Artwork

Main podcast artwork target:

```text
3000 × 3000 px
JPG or PNG
no transparency
```

Placeholder artwork may be used during development.

Do not replace or modify official artwork unless explicitly requested.

## Website

The website is static and must remain compatible with GitHub Pages.

Requirements:

- responsive;
- readable on mobile;
- semantic HTML;
- basic navigation must work without JavaScript;
- avoid unnecessary animations;
- avoid generic SaaS-style visual patterns;
- use relative paths where appropriate;
- preserve stable episode URLs.

The visual direction should remain restrained and editorial.

## RSS

The project may eventually generate its own RSS feed.

Target compatibility:

1. Yandex Music
2. Spotify
3. Apple Podcasts
4. YouTube / YouTube Music

RSS rules:

- every published episode must have a stable GUID;
- enclosure URLs must be public;
- publication dates must be preserved;
- episode ordering must remain correct;
- RSS must be accessible without authentication;
- use standard podcast RSS conventions;
- avoid proprietary platform-specific behavior when a standard alternative exists.

Do not manually modify generated RSS once a generator becomes the source of truth.

## Publishing Model

A typical new episode should eventually require only:

1. upload MP3 to R2;
2. create:

```text
seasons/season-XX/episode-YY/episode.yml
```

3. commit;
4. push to `main`;
5. let automation rebuild the website and RSS.

Do not make publishing depend on manually editing multiple duplicated metadata files.

## GitHub Pages

The site is published from GitHub.

Keep deployment simple.

A normal update should remain approximately:

```bash
git add .
git commit -m "Describe the change"
git push origin main
```

Do not introduce a custom deployment stack without a concrete reason.

## Secrets

Never commit:

- API tokens;
- Cloudflare credentials;
- passwords;
- private keys;
- billing credentials;
- secret `.env` values.

Use GitHub Secrets if automation requires credentials.

Never expose secrets in:

- HTML;
- RSS;
- logs;
- GitHub Actions output;
- generated files.

## Cloudflare

Cloudflare R2 may host public audio.

Preferred architecture:

```text
Custom domain
     ↓
Cloudflare cache
     ↓
R2 Standard
```

Avoid introducing:

- Workers;
- D1;
- KV;
- Queues;
- R2 SQL;
- other usage-based Cloudflare services

unless explicitly required.

Do not use `r2.dev` as the permanent production audio URL.

## Cost Awareness

This is an independent podcast project.

Prefer:

- predictable costs;
- free static hosting where appropriate;
- minimal recurring infrastructure;
- no unnecessary subscriptions;
- no unnecessary usage-based services.

Before introducing a paid dependency, explain:

1. why it is needed;
2. recurring cost;
3. usage-based costs;
4. whether a hard spending cap exists;
5. migration difficulty.

## Migration Safety

The system must remain easy to migrate to a managed podcast host.

Possible future hosts include:

- mave+;
- Castos;
- Captivate;
- other standards-based podcast hosts.

Migration invariants:

- preserve episode GUIDs;
- preserve original audio masters;
- retain control over the project domain;
- use standard RSS;
- keep metadata portable;
- maintain season/episode numbering;
- avoid title-based identifiers;
- avoid unnecessary proprietary metadata.

If the RSS URL changes, use a permanent HTTP `301` redirect where appropriate.

## Git Practices

Make small, focused changes.

Before committing:

- inspect `git status`;
- do not commit audio;
- do not commit secrets;
- do not include local/generated junk;
- avoid unrelated formatting changes.

Use descriptive commit messages, for example:

```text
Add season and episode structure
Add metadata for season 1 episode 1
Add initial podcast homepage
Generate RSS from episode metadata
Add platform links
```

Do not rewrite published Git history unless explicitly requested.

## Change Policy

Before significant architectural changes, explain:

- what problem is being solved;
- new dependencies;
- GitHub Pages impact;
- RSS compatibility impact;
- cost impact;
- migration impact.

For small HTML/CSS/content changes, proceed directly.

## Validation

### Website changes

Check:

- desktop layout;
- mobile layout;
- relative URLs;
- missing assets;
- stable canonical URLs;
- accessibility basics.

### Episode metadata changes

Check:

- season number;
- episode number;
- stable GUID;
- audio URL;
- publication date;
- title;
- reader;
- description.

### RSS changes

Check:

- valid XML;
- required channel metadata;
- unique and stable GUIDs;
- correct enclosure URLs;
- correct MIME types;
- publication dates;
- episode ordering.

### Infrastructure changes

Check:

- no secrets;
- no unexpected paid services;
- reproducible deployment;
- migration remains possible.

## Priority

When choosing between a clever solution and a boring, portable, understandable solution, choose the boring one.