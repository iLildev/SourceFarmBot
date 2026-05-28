---
name: Atomic seed operations
description: All User.points mutations must use atomic SQL UPDATE, never ORM read-modify-write
---

## Rule
Never use `user.points += amount` or `user.points -= cost` with ORM objects.
Always use `update(User).where(...).values(points=User.points + amount).returning(User)`.
For deductions with a balance floor, add `.where(User.points >= cost)` and check the returned row is not None.

**Why:** Multiple concurrent Telegram messages can trigger the same handler simultaneously.
ORM read-modify-write creates a race window: two requests read the same balance, both write back, one deduction is lost.

**How to apply:** add_seeds, install_bot seed deduction, referral bonus — all use UPDATE statements.
