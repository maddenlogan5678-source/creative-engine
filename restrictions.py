# ============================================================================
# FILE: restrictions.py  —  PROJECT ROOT: /mnt/agents/output/app/
# ROLE: EVERY restriction in this app, in ONE place. Nothing else gates
# content anywhere else in the codebase.
#
# TWO LAYERS — know which is which:
#   [YOUR LAYER]    Everything in this file. Editable, free, local, instant.
#                   You own it. Change any line, it takes effect immediately.
#   [GATEWAY LAYER] NOT in this file and NOT in any file you own. The image
#                   and story models at agent-gw moderate prompts server-side
#                   with their own classifier. No code here can reach, read,
#                   or change it. Emptying this file only moves refusals from
#                   instant-and-free to slow-and-paid.
# ============================================================================

# ----------------------------------------------------------------------------
# [1] HARD GATE — word/phrase list, checked by substring match
#     Used by: verify_safety() in engine.py
#     Enforced at: server.py story(), image(), rp_send() -> HTTP 422
# ----------------------------------------------------------------------------
HARD_BOUNDARY_TERMS = [
    "nsfw", "explicit sex", "sexual", "porn", "erotic", "nude", "naked",
    "child", "minor", "underage", "loli", "rape", "incest", "bestiality",
    "gore porn", "snuff", "scat", "pissing on", "shitting on", "watersport",
    "feces", "coprophil",
]

# ----------------------------------------------------------------------------
# [2] REFUSAL TEXT — what the user sees when the hard gate triggers
# ----------------------------------------------------------------------------
SAFETY_REFUSAL = (
    "SAFETY_BOUNDARY_TRIGGERED. That request crosses into content the "
    "underlying models will not produce (sexual/explicit material, or "
    "content involving minors). The engine refuses — this boundary is "
    "unbreakable by design. Reroute the creative energy into dark humor, "
    "noir, horror, satire, or tragedy instead."
)

# ----------------------------------------------------------------------------
# [3] SOFT CAPS — wording injected INTO prompts (they shape output, they
#     don't block requests). Each marked with where it's used.
# ----------------------------------------------------------------------------
# 3a. story builder  (engine.py -> build_story_prompt)
STORY_EXPLICIT_CAP = (
    "Romance/tension may be charged and suggestive at most; anything "
    "explicit is off the table — fade to black."
)
# 3b. image builder  (engine.py -> build_image_prompt)
IMAGE_NONSEXUAL_TAG = "Non-sexual imagery."
# 3c. persona cards  (engine.py -> PERSONAS, the boundary sentence in each)
# 3d. roleplay rules (engine.py -> RP_RULES, the "no explicit" line)

# ----------------------------------------------------------------------------
# [4] DIALS THAT ARE *NOT* RESTRICTIONS
#     power / harshness / gruesomeness go to 10 with no ceiling of mine —
#     only the gateway's own refusal threshold applies past its ceiling.
# ----------------------------------------------------------------------------
