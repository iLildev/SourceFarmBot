---
name: Install FSM source_id guard
description: Must validate source_id > 0 after reading FSM state in receive_token handler
---

## Rule
After `data = await state.get_data()`, check `source_id = data.get("source_id", 0)`.
If `source_id == 0`, clear state and show an error — do NOT proceed to install_bot.
Also, `install_service.install_bot` raises `InstallError("invalid_source")` if source_id is falsy.

**Why:** FSM state can expire (aiogram default TTL) or a user can send a token message
without going through start_install first (e.g. forwarded message, state mismatch).
Passing source_id=0 to install_bot would create a Bot record with an invalid source reference.
