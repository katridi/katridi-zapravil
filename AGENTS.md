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
podcast.yml
+
seasons/**/episode.yml
+
static site source
        ↓
Python build
        ↓
dist/
        ↓
GitHub Actions
        ↓
GitHub Pages

Cloudflare R2
        ↓
Podcast audio files
```

RSS is part of the production build.

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
├── podcast.yml
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
│   ├── build.py
│   └── build_feed.py
│
├── tests/
│   └── ...
│
├── .github/
│   └── workflows/
│       └── pages.yml
│
├── index.html
├── style.css
├── requirements.txt
├── README.md
├── AGENTS.md
└── .gitignore
```

Do not create abstractions or directories before they are needed.

`dist/` is generated build output and is not the source of truth.

`feed.xml` is generated during build and should not be edited manually.

Podcast MP3 files are not stored in GitHub.

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
season_title: "Воспоминания"
episode: 1
episode_type: "full"

author: "Алексей Катриди"
reader: "Сергей Глебкин"

guid: "kz-s01e01"

status: "draft"
published_at: null

audio:
  url: null
  type: "audio/mpeg"
  duration: null
  length: null

description: >
  Рассказ Алексея Катриди.
  Читает Сергей Глебкин.
```

The title is editorial content.

The following are stable identifiers:

```text
season
episode
guid
```

Draft episodes may have:

```yaml
published_at: null
audio:
  url: null
```

Only episodes with `status: "published"` appear in RSS.

Published episodes require valid `published_at` and `audio.url`.

`published_at` must include a timezone offset.

`audio.length` is the audio file size in bytes. If `audio.length` is absent for a published episode, the build may obtain it with an HTTP `HEAD` request. Do not download the full MP3 to calculate length.

Episode identity is based on `season`, `episode`, and `guid`, not on `title`.

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

## Podcast Metadata

Show-level metadata lives in:

```text
podcast.yml
```

`podcast.yml` is the source of truth for podcast title, description, language, author, site URL, feed URL, artwork metadata, owner metadata, iTunes category, explicit flag, and platform distribution URLs.

The current iTunes metadata shape is:

```yaml
itunes:
  category: "Fiction"
  explicit: false
```

Do not move `itunes.category` or `itunes.explicit` to top-level fields without a real architectural reason.

`distribution` is website/project metadata. Do not automatically turn `distribution` values into RSS tags.

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

### Homepage source and generated output

The repository-root `index.html` is the editable source template for the homepage.

It may contain build placeholders such as:

```text
{{EPISODES}}
```

The root `index.html` is not the final deployed page. Never delete the root template merely because GitHub Pages deploys `dist/`.

The deployable homepage is generated at:

```text
dist/index.html
```

by running:

```bash
python3 scripts/build.py
```

`dist/index.html` must not contain unresolved placeholders such as `{{EPISODES}}`.

Homepage content should be changed through:

- root `index.html`;
- `style.css`;
- `podcast.yml`;
- `seasons/**/episode.yml`;
- build/rendering code where appropriate.

Do not edit `dist/index.html` instead of editing the source template or generator.

Generated files in `dist/` are not sources of truth and should remain ignored by Git. Do not commit generated `dist/` files unless the architecture explicitly changes in the future.

To preview the real built homepage locally, run `python3 scripts/build.py` and open `dist/index.html`. The repository-root `index.html` may look incomplete if opened directly because it is a template.

If `{{EPISODES}}` appears in a browser:

1. check whether root `index.html` was opened directly;
2. check `dist/index.html`;
3. check the build;
4. check the GitHub Pages workflow artifact.

Do not "fix" this by removing the placeholder from the source template.

## RSS

The project generates its own RSS feed during the production build.

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

A typical new episode should require:

1. upload MP3 to audio hosting;
2. create or edit:

```text
seasons/season-XX/episode-YY/episode.yml
```

3. keep `status: "draft"` while preparing;
4. fill final metadata and audio URL;
5. change `status` to `published` when ready;
6. commit;
7. push to `main`;
8. let GitHub Actions validate metadata, build `dist/`, and deploy GitHub Pages;
9. let podcast platforms later poll the public RSS feed.

Platforms do not receive episodes via a separate API push from this repository workflow.

Do not make publishing depend on manually editing multiple duplicated metadata files.

## GitHub Pages

GitHub Pages uses GitHub Actions-based deployment:

```text
Settings
→ Pages
→ Source
→ GitHub Actions
```

The deployment artifact is:

```text
dist/
```

The GitHub Actions workflow must deploy `dist/`, not the repository root.

Do not describe publishing directly from `main` root as the current architecture.

Keep deployment simple and do not introduce a custom deployment stack without a concrete reason.

## GitHub Actions

The publishing pipeline is:

```text
push to main
→ tests
→ build
→ Pages artifact
→ deploy
```

Build or test failure must prevent a new deploy.

The workflow must not commit or push generated `feed.xml` back into `main`.

## Build Model

The canonical production build command is:

```bash
python3 scripts/build.py
```

The build must:

- clean `dist/`;
- validate metadata;
- generate RSS;
- copy static site files;
- copy required assets;
- create a complete deployable `dist/`.

Generated files must not be edited instead of source files.

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

For build and site tasks, completion means checking the whole chain:

```text
source
→ tests
→ build
→ dist/
→ deployment configuration
```

Do not report success solely because source files were edited.

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


## Source of truth and deployment parity

The repository source files are the source of truth.

For the website, the intended local source version is authoritative unless the user explicitly requests a redesign.

If the local version and the deployed GitHub Pages version differ:

1. do not redesign the local UI;
2. inspect the source files;
3. inspect the build output;
4. inspect the GitHub Actions workflow;
5. identify where the divergence occurs;
6. fix the build/deploy pipeline rather than changing the intended design.

If local source is correct but production differs, diagnose build/deploy parity instead of editing generated files.

The deployment pipeline is:

source files
→ build
→ dist/
→ GitHub Pages artifact
→ production site

`dist/` is generated output, not the primary editing target.

Do not manually patch generated files as a substitute for fixing their source or generator.


## UI change discipline

Preserve existing layout, typography, spacing, wording, and visual hierarchy unless the task explicitly asks to change them.

A narrowly scoped UI request must not become a redesign.

Examples:

- adding one Telegram link must not change the layout of unrelated platform buttons;
- replacing one asset must not change typography;
- fixing production deployment must not change the intended local UI;
- changing link behavior must not change editorial copy.

When screenshots or an existing local implementation are provided as the desired result, treat them as the visual source of truth.

Do not "improve", simplify, modernize, or normalize the design unless explicitly requested.


## Static assets

Before referencing an asset in HTML or CSS, verify that the file actually exists in the repository.

Before finishing a task involving assets:

- verify the expected file path;
- verify filename casing;
- verify that the file is tracked by Git;
- verify that the build copies it into `dist/`;
- verify that the generated HTML points to the deployed path.

Do not silently substitute:

- text for a missing image;
- another image for a missing image;
- an externally downloaded asset;
- an icon library.

Do not crop, recolor, stretch, convert, or redraw supplied brand assets unless explicitly requested.

Preserve image aspect ratio.


## Platform links

Platform URLs live in `podcast.yml` under `distribution`.

Example:

```yaml
distribution:
  yandex_music: null
  spotify: null
  apple_podcasts: null
  youtube: null
  telegram: "https://t.me/katridi_writes"
```

The current intended homepage UI is:

```text
[ Яндекс Музыка ] [ Spotify ]
[ Apple Podcasts ] [ YouTube ]

[ Telegram icon  Читать Катриди заправил ]
```

Rules:

- Yandex Music, Spotify, Apple Podcasts, and YouTube are text-only controls;
- those four controls use the current 2x2 layout;
- do not add icons to those four services unless explicitly requested;
- Telegram is a separate full-width row below them;
- Telegram uses `assets/icons/telegram.png`;
- Telegram visible text is `Читать Катриди заправил`;
- Telegram URL is `https://t.me/katridi_writes`;
- do not move Telegram into the 2x2 grid unless explicitly requested;
- null distribution URLs must not use `href="#"`.

Treat the current local implementation and screenshots approved by the user as the visual source of truth.


## Scope rule

Make the smallest change that fully satisfies the request.

Do not modify adjacent behavior, layout, metadata, or architecture unless the task requires it.

When the requested end state is already correct locally, diagnose why it is not reaching production instead of interpreting the task as a redesign.
