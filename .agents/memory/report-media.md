---
name: Report handler media types
description: _extract_media signature and _notify_admins branching on media_type
---

## Rule
`_extract_media(message)` returns `(description: str, file_id: str | None, media_type: str | None)`.
`media_type` is one of: `'photo'` | `'video'` | `'document'` | `None`.

`_notify_admins` must branch:
- photo → `bot.send_photo()`
- video → `bot.send_video()`
- document → `bot.send_document()`
- None → `bot.send_message()`

**Why:** Calling `send_photo` with a video file_id raises a Telegram API 400 error.
Previously, video/document file_ids were silently dropped (returned None), losing evidence in reports.
