# Video Transcript Agent Research

Created: 2026-05-27

## Why This Should Be A Shared Agent

Video and interview transcripts should not live only inside the Business Model / Moat Agent. The same capability will be useful for:

- Business model / moat: founder strategy, marketplace design, product philosophy, competitive claims.
- Leadership / people: founder values, management style, organization design, capital allocation language.
- Customer happiness: product review videos, complaint videos, creator incentives, user comments when collected separately.
- Merchant sustainability: seller education videos, merchant interviews, platform-rule explanations.
- Competitor comparison: executive interviews and investor-event videos from competitors.

The right design is a reusable `Video Transcript Agent` that collects and audits transcript evidence, then downstream agents consume its normalized transcript records.

## Video Manifest Trace Spine

Every video/interview source should be registered in a manifest before downstream agents use it. `source_id` identifies one registry row; `video_uid` identifies the underlying media or content item. This matters because the same YouTube/Bilibili/interview source may later feed the business-model, leadership, customer-happiness, merchant-sustainability, earnings-call, and competitor agents.

Current implementation:

- Manifest code: `src/stock_research/qualitative/video_manifest.py`.
- Run artifact: `video_manifest.json`.
- Data-linkage section: `Video Manifest Linkage`.
- Stable IDs prefer native platform ids:
  - YouTube: `video:youtube:<youtube_video_id>`.
  - Bilibili: `video:bilibili:<bvid>`.
  - Official webcast: `video:edge_media_server:<player_hash>`.
  - Web interview pages: `content:<platform>:<canonical_url_hash>`.
- Each manifest record stores platform, native id, canonical URL, source ids, agent ids, source family, event period/type when available, rights/allowed-use labels, collection attempts, transcript segment counts, evidence counts, cache paths, and errors.

Traceability rule: all extracted video/interview evidence should carry either `video_uid` directly or enough source metadata to resolve to `video_uid` through the manifest.

## Current V1 Capability

Current code: `src/stock_research/qualitative/executive_transcripts.py`

What already works:

- Curated source registry for PDD executive/interview videos and interview pages.
- YouTube caption-track parser for watch-page caption metadata.
- Bilibili subtitle JSON parser using video `bvid`, `cid`, `x/player/v2`, and `subtitle_url`.
- Web interview-page reader for public written interview pages.
- Video manifest generation and per-run manifest cache.
- Normalized transcript segments with timestamps where available.
- Evidence extraction by configured topic terms.
- Shared business-model question pack over collected video/interview transcripts, with English and Chinese matching terms.
- Manual transcript-file intake for Bilibili/BibiGPT/ASR exports when a video has no exposed platform subtitles.
- Controlled web-interview fallback sources can now opt into direct HTML article parsing when the reader service only returns navigation noise.
- Audit behavior: if captions/subtitles are missing or blocked, the agent records that state and does not invent transcript text.

Official earnings-call extension:

- Current code: `src/stock_research/qualitative/official_events.py`.
- Registry: `config/qualitative/pdd_official_event_sources.v1.json`.
- The official-event reader now includes a business-model question pack for earnings-call / investor-day sources.
- The first manually seeded YouTube source is `https://www.youtube.com/watch?v=42LEstZIskM` for PDD Q4 2025.
- If a YouTube source has no public caption track, the reader can now try Gemini video understanding when `GEMINI_API_KEY` or `GOOGLE_API_KEY` is set.
- Gemini answers are labeled `gemini_video_understanding_non_verbatim`; they are not stored as transcript evidence.
- For long YouTube videos, the reader uses Gemini clipping windows and merges question answers across chunks. This avoids relying on a single full-video request.
- If no key is configured, the source is still registered in the manifest and every question is marked as queued with the missing-key status.
- Future source discovery should populate all available PDD earnings-call videos through YouTube Data API, curated URLs, or user-provided links, then reuse the same question pack.

Main limitation:

- It is currently PDD-specific and executive-material-specific.
- It does not yet have robust video discovery.
- It does not yet use optional `yt-dlp`.
- It does not yet use speech-to-text fallback when platform captions are missing.
- It can use Gemini for public YouTube video understanding, but only when a Gemini API key is configured.

## Current Recommendation

Use Gemini API as an optional video-understanding adapter, especially for public YouTube interviews and long videos where we need timestamped claims quickly. Do not make Gemini the transcript source of record.

For auditable investment research, the best architecture is two-track:

- Transcript track: official written transcripts, platform captions, `yt-dlp` subtitles, Bilibili subtitle JSON, or ASR. This track provides exact wording and evidence linkage.
- Understanding track: Gemini video understanding. This track produces timestamped claim summaries, visual/context observations, and triage notes that downstream agents can verify against the transcript track.

For Bilibili, Gemini should not be the first path unless we have a permissible local/user-provided video file. Start with Bilibili subtitle metadata or written interview pages, then use ASR or Gemini File API only when policy allows.

## Review Of Gemini Research Input

The user supplied a Gemini research report on YouTube/Bilibili ingestion for investment research. The useful design direction matches our current plan:

- Keep this as a shared `Video Transcript Agent`, not a business-model-only feature.
- Use metadata-first, transcript-second, evidence-preserving ingestion.
- Use native captions/subtitles when available and permitted.
- Add ASR only behind an explicit policy gate.
- Preserve timestamps, language, speaker labels when available, source URLs, and confidence.
- Route extracted claims to business model, leadership, customer happiness, merchant sustainability, earnings-call, and competitor agents.

Implementation choices accepted from that report:

- Add optional Gemini video-understanding for public YouTube URLs and policy-approved local media.
- Add optional `yt-dlp` only as a controlled adapter for metadata/subtitle extraction, with version logging and source-status recording.
- Keep Bilibili as curated URL intake plus subtitle metadata first, not broad automated scraping.
- Use structured extraction prompts that require timestamped evidence and contradiction/risk checks.

Implementation choices rejected or deferred:

- Do not make unauthorized audio/video downloading the default fallback.
- Do not archive full third-party transcripts or copied captions unless the source/license/user-provided file permits it.
- Do not treat Gemini's generated answer as a verbatim transcript.
- Do not rely on sample LangChain code from research reports without adapting it to our source policy and current package versions.

## Source Hierarchy

Preferred source order:

1. Official written transcript from company IR, exchange filing, earnings-call provider, or event page.
2. Official YouTube or Bilibili channel video with creator-provided captions.
3. Official or high-provenance media interview page with full text.
4. Public platform captions from YouTube/Bilibili when available.
5. Machine transcription from audio, only when enabled by policy and logged as ASR.
6. Reposted clips, third-party summaries, creator commentary, or AI summaries. These are lead evidence only.

Rule: video transcripts can explain management or user framing, but they must not override filings, audited financials, or official numeric sources.

## YouTube Findings

Official YouTube Data API:

- `captions.list` can list caption tracks for a video, but the response does not include the actual caption text. It requires authorization and costs 50 quota units.
- `captions.download` downloads a caption track, but the official docs say the user needs permission to edit the video. It costs 200 quota units.
- `search.list` can find videos and has a `videoCaption=closedCaption` filter. It costs 100 quota units per call.
- Default YouTube API quota is 10,000 units per day; quota extensions require compliance review.

Practical implication:

- The official YouTube Data API is good for discovery and metadata.
- It is not enough for downloading captions from arbitrary public videos unless we own or are authorized for the video.
- For public videos, practical collection usually needs either the public watch-page caption tracks or a tool such as `yt-dlp`.

`yt-dlp`:

- The official project supports subtitle operations such as listing subtitles, writing uploaded subtitles, writing auto-generated subtitles, choosing subtitle languages, and selecting subtitle formats.
- It is more robust than hand-parsing YouTube watch HTML, but it is still an extractor that can break when platforms change.
- It should be an optional adapter, not the only path.

Recommended YouTube strategy:

1. Use official YouTube API for search and metadata when we have an API key.
2. For a curated video URL, try public caption track extraction or optional `yt-dlp`.
3. Prefer creator-uploaded captions over auto captions.
4. Record `caption_source=creator_uploaded`, `auto_generated`, `unknown`, or `asr_fallback`.
5. If no caption exists, record `metadata_collected_no_caption_tracks`.
6. Only use ASR fallback if enabled by a clear system policy.

## Gemini Video Understanding Adapter

Gemini is a strong candidate for YouTube video understanding, but it should be treated as a separate adapter from transcript extraction.

Official Gemini API video-understanding docs say Gemini can process video, answer questions about video content, extract information, and refer to timestamps. Supported input methods include:

- File API upload.
- Cloud Storage registration.
- Inline video data.
- Public YouTube URLs.

Important YouTube-specific details:

- Gemini API can accept public YouTube URLs directly as `file_data.file_uri`.
- The YouTube URL feature is currently in preview and available at no charge; pricing and rate limits are likely to change.
- Free tier has an 8-hour-per-day YouTube video upload limit.
- Paid tier has no limit based on video length.
- Gemini 2.5+ can accept up to 10 videos per request, but the docs still recommend one video per prompt for best results.
- Only public videos are supported, not private or unlisted videos.

Important video-processing details:

- Gemini samples video frames, defaulting to 1 frame per second.
- It processes audio as part of video understanding.
- Models with a 1M context window can process videos up to 1 hour at default media resolution or 3 hours at low media resolution.
- It supports timestamp-focused prompts such as asking about `MM:SS`.

How this should fit our system:

- Use Gemini for interpretive video understanding: "What does the executive say about the business model?", "What changed in tone?", "What are the key claims with timestamps?"
- Do not treat Gemini's generated answer as a verbatim transcript unless it is cross-checked against captions, ASR, or a written transcript.
- Store Gemini outputs as `video_understanding_summary` or `video_claim_extraction`, not as `official_transcript`.
- If Gemini produces timestamped claims, downstream agents can use them as leads and then ask the transcript layer to verify the exact wording.

Recommended Gemini adapter output:

- `adapter`: `gemini_video_understanding`
- `input_method`: `youtube_url`, `file_api_upload`, or `inline_video`
- `model`
- `prompt`
- `video_url`
- `video_metadata`
- `claim_items`
- `timestamped_observations`
- `limitations`
- `raw_response_cache_path`

Best use:

- YouTube executive interviews and investor-event videos where captions are missing or insufficient.
- Video content where visual context matters, such as factory tours, product demos, app walkthroughs, customer complaint videos, and merchant tutorials.
- Fast first-pass triage of long videos before deciding whether to spend effort on exact transcript extraction.

Not best use:

- Official financial numbers.
- Verbatim quotation without cross-checking.
- Non-public videos.
- Bilibili URLs directly, unless Gemini explicitly supports that URL type later.

## Bilibili Findings

Official status:

- Bilibili has an open platform, but I did not find official public subtitle-download documentation for normal video pages in the accessible docs.

Community-documented practical path:

- Community documentation records `https://api.bilibili.com/x/player/v2` with `bvid` and `cid`.
- The response can expose `data.subtitle.subtitles[]`, and each subtitle entry can include `subtitle_url`.
- The subtitle URL returns JSON-style timed subtitle content.
- The same community source explicitly frames this as web-captured / undocumented behavior, not an official stable API.
- Community docs also warn about authentication, risk control, and anti-abuse behavior across Bilibili APIs.

Practical implication:

- Bilibili subtitle collection should stay lower confidence than official transcripts.
- We should use it cautiously, rate limit it, cache raw responses, and never bypass login, captcha, risk controls, or paywalls.
- If no subtitle is exposed, record `metadata_collected_no_subtitles`.

Recommended Bilibili strategy:

1. Fetch video metadata and `cid` from public metadata endpoints.
2. Fetch player metadata with `x/player/v2`.
3. Select preferred subtitle language.
4. Fetch `subtitle_url` if present.
5. Normalize subtitle body into transcript segments.
6. Run the shared business-model question pack over the collected segments, using Chinese and English terms.
7. Cache pagelist, player metadata, subtitle JSON, normalized transcript, and question results.
8. If no subtitles are exposed, record `metadata_collected_no_subtitles` and mark each question as `not_answered_no_transcript`. Do not invent a transcript.

Important limitation:

- This path can answer questions only when transcript/subtitle text exists. It is not the same as Gemini's direct YouTube video understanding. For Bilibili videos without subtitles, the next safe inputs are a user-provided transcript export, a clearly permitted ASR transcript, or an external service such as BibiGPT when its source/cost/rights posture is accepted and logged.
- The V1 registry includes `manual_bilibili_transcript_export_intake`. Once `local_transcript_path` points to a `.txt`, `.md`, or `.json` transcript export, the same business-model question pack runs without code changes.
- For the PDD People interview Bilibili target, the public Bilibili page exposes no subtitle track, so the registry also records a related People/Huanqiu text page as a separate lower-tier web interview source. This source is not labeled as a Bilibili transcript.

## Gemini For Bilibili

Current read:

- Gemini video-understanding docs explicitly support YouTube URLs, but I did not find equivalent direct support for Bilibili URLs.
- Gemini URL Context supports web pages, PDFs, images, and text-like resources, but its limitations explicitly list YouTube videos, video files, and audio files as unsupported through URL Context. YouTube videos instead use the special video-understanding path.
- Therefore, for Bilibili the practical Gemini route is not "paste Bilibili URL directly" unless Google later adds that support.

Recommended Bilibili hierarchy:

1. Use official/written transcript if available.
2. Use Bilibili subtitle metadata and subtitle JSON when exposed.
3. Use written media/interview pages.
4. If no transcript exists, use ASR or Gemini File API only when we have a permissible local audio/video file or user-provided file.
5. If using Gemini File API on a Bilibili video file, treat it as video understanding / ASR-derived evidence, not official transcript evidence.

For Bilibili interviews, a two-track approach is best:

- Transcript track: subtitle JSON or ASR for exact wording.
- Understanding track: Gemini File API on the video/audio file if visual/tone/context matters.

This avoids depending on undocumented Bilibili access for all analysis while still giving us a path when captions are missing.

## Speech-To-Text Fallback

When platform captions do not exist, the only reliable content path is ASR from audio.

OpenAI Speech-to-Text supports:

- `transcriptions` and `translations` endpoints.
- Models including `gpt-4o-mini-transcribe`, `gpt-4o-transcribe`, and `gpt-4o-transcribe-diarize`.
- Input formats including mp3, mp4, mpeg, mpga, m4a, wav, and webm.
- Current upload limit of 25 MB; longer audio must be chunked.
- `gpt-4o-transcribe-diarize` can produce speaker-aware transcript segments.

Recommended ASR policy:

- ASR is a fallback, not first choice.
- It requires explicit configuration because it has cost, copyright, and transcript-quality implications.
- Store model name, language hint, prompt, chunking method, audio source, file checksum, and cost estimate.
- Mark ASR evidence as lower confidence than official captions or written transcripts.
- For interviews, use diarization when speaker separation matters.

## Proposed Shared Agent Design

Agent name: `Video Transcript Agent`

Inputs:

- Company identity.
- Source registry entries.
- Optional search/discovery queries.
- Preferred languages.
- Use-case tags: `business_model`, `leadership`, `customer_happiness`, `merchant_sustainability`, `competitor_comparison`.
- Collection policy: `captions_only`, `captions_plus_public_tools`, or `captions_plus_asr`.

Output:

- `video_transcript_findings`.
- Normalized transcript JSON files.
- Per-source collection status.
- Evidence items by use-case tags.
- Audit notes and source-quality labels.

Normalized source schema:

- `source_id`
- `company_id`
- `platform`
- `url`
- `source_owner`
- `source_type`
- `source_quality_tier`
- `language`
- `preferred_languages`
- `collection_policy`
- `allowed_methods`
- `speaker_names`
- `use_case_tags`
- `notes`

Normalized transcript segment schema:

- `source_id`
- `platform`
- `transcript_method`
- `language`
- `segment_index`
- `start_seconds`
- `end_seconds`
- `speaker`
- `text`
- `confidence`
- `source_url`
- `cache_path`

Status vocabulary:

- `official_transcript_collected`
- `youtube_caption_collected`
- `youtube_metadata_collected_no_caption_tracks`
- `bilibili_subtitle_collected`
- `bilibili_metadata_collected_no_subtitles`
- `web_interview_text_collected`
- `asr_transcribed`
- `blocked_or_failed`
- `manual_review_required`

## Recommended Implementation Path

Phase 1: Refactor current PDD code into a generic reusable module.

- Move source-agnostic pieces from `executive_transcripts.py` into `video_transcripts.py`.
- Keep PDD registry as a company-specific config.
- Make executive-material agent consume `video_transcript_findings`.
- Keep current parsers and tests.

Phase 2: Improve YouTube adapter.

- Add optional `yt-dlp` adapter if installed.
- Add official YouTube metadata/search adapter if API key is configured.
- Keep direct caption-track parser as a lightweight fallback.
- Add optional Gemini YouTube URL adapter for video understanding and timestamped claim extraction.

Phase 3: Improve Bilibili adapter.

- Strengthen metadata capture and error classification.
- Record whether subtitles are official, AI-generated, user-generated, or unknown when exposed.
- Add conservative retry/rate-limit behavior.

Phase 4: Add ASR fallback behind a policy gate.

- Extract or accept audio only when policy allows.
- Chunk audio under 25 MB.
- Use `gpt-4o-transcribe` or `gpt-4o-mini-transcribe` for plain transcript.
- Use `gpt-4o-transcribe-diarize` for interviews where speaker attribution matters.

Phase 4b: Add Gemini File API / YouTube understanding fallback.

- Use Gemini direct YouTube URL input for public YouTube videos when we want video understanding, not just transcript text.
- Use Gemini File API for local/user-provided video files, including Bilibili files only when policy allows.
- Label all outputs as generated video understanding unless verified against transcript text.

Phase 5: Add cross-agent dispatch.

- Business Model / Moat Agent reads strategy and moat claims.
- Leadership / People Agent reads values, incentives, organization, capital allocation.
- Customer Happiness Agent reads customer-review videos, but marks creator bias.
- Merchant Agent reads seller interviews and seller education videos.
- Competitor Agent compares management claims across companies.

## Key Design Principle

The transcript agent should collect evidence, not decide the investment conclusion. Its job is to make video evidence auditable:

- What source was used?
- Was the transcript official, platform caption, public subtitle, ASR, or summary?
- What exactly was said?
- Where in the video/page did it appear?
- How reliable is the transcript?
- Which downstream agents are allowed to use it?

## Sources Checked

- YouTube Data API `captions.list`: https://developers.google.com/youtube/v3/docs/captions/list
- YouTube Data API `captions.download`: https://developers.google.com/youtube/v3/docs/captions/download
- YouTube Data API `search.list`: https://developers.google.com/youtube/v3/docs/search/list
- YouTube quota and compliance: https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits
- yt-dlp README: https://github.com/yt-dlp/yt-dlp/blob/master/README.md
- yt-dlp supported sites note: https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/supportedsites.md
- Bilibili open platform: https://open.bilibili.com/platform
- Community Bilibili subtitle endpoint note: https://github.com/SocialSisterYi/bilibili-API-collect/issues/323
- Community Bilibili API overview and cautions: https://deepwiki.com/SocialSisterYi/bilibili-API-collect/1-bilibili-api-overview
- OpenAI speech-to-text guide: https://developers.openai.com/api/docs/guides/speech-to-text
- Gemini video understanding: https://ai.google.dev/gemini-api/docs/video-understanding
- Gemini URL Context: https://ai.google.dev/gemini-api/docs/url-context
