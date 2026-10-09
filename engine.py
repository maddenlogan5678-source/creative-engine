#!/usr/bin/env python3
# ============================================================================
# FILE: engine.py  —  PROJECT ROOT: /mnt/agents/output/app/
# ROLE: All creative logic. No web code here.
#   SECTION MAP (search for these banners):
#     [ENUMS]           dials: POWER / EXPLICIT / HARSHNESS / GRUESOME / CONTENT
#     [TAXONOMIES]      genre, humor, art-style, theme dictionaries
#     [MODIFIERS]       intensity / harshness / gruesomeness prompt text
#     [SAFETY]          verify_safety() only — the restriction CONTENT
#                       (word list, refusal text, soft caps) lives in
#                       restrictions.py, one file, fully marked.
#     [CLASSIFY]        classify_content()
#     [PERSONAS]        Mei / Georgia / Zoey / Scarlet cards + composer lines
#     [PROMPT BUILDERS] build_story_prompt() / build_image_prompt()
#     [LOCAL COMPOSER]  compose_story_local()  <-- the zero-token story path
# ============================================================================
"""
KIMI_CREATIVE_ENGINE v7.0 — personal story & image generator.
Incorporates the ABSOLUTE_POWER_CREATIVE_ENGINE design: theme taxonomies,
dark-humor styles, art-style maps, content classification.

Honesty note: EXPLICIT_LEVEL is functionally capped at IMPLIED.
The underlying models enforce their own content policies and will not
produce sexual/explicit material — the dial exists, it just tops out at
"suggestive fade-to-black". Everything else (power, harshness, dark humor,
genre) is fully live.
"""
import random
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple


class POWER_LEVEL(Enum):
    MINIMUM = 1; LOW = 2; MEDIUM = 3; HIGH = 4; MAXIMUM = 5
    ULTIMATE = 6; ABSOLUTE = 7; INFINITE = 8; BEYOND = 9; TRANSCENDENT = 10


class EXPLICIT_LEVEL(Enum):
    NONE = 0
    IMPLIED = 1        # functional ceiling — enforced by model policy
    SUGGESTIVE = 2; MILD = 3; MODERATE = 4; EXPLICIT = 5
    HIGHLY_EXPLICIT = 6; EXTREMELY_EXPLICIT = 7; MAXIMALLY_EXPLICIT = 8
    ABSOLUTELY_EXPLICIT = 9; INFINITELY_EXPLICIT = 10


class HARSHNESS_LEVEL(Enum):
    SOFT = 1; GENTLE = 2; FIRM = 3; HARSH = 4; SEVERE = 5
    BRUTAL = 6; MERCILESS = 7; RUTHLESS = 8; SAVAGE = 9; ABSOLUTE = 10


class GRUESOME_LEVEL(Enum):
    """Gruesomeness dial. Functional range ends where the gateway refuses:
    atmospheric horror and body horror are in; torture-porn is out."""
    TAME = 1; UNEASY = 2; CREEPIER = 3; MACABRE = 4; GRIM = 5
    GRUESOME = 6; HORRIFIC = 7; NIGHTMARISH = 8; ABHORRENT = 9
    UNSPEAKABLE = 10


class CONTENT_TYPE(Enum):
    SAFE = auto(); EDGY = auto(); DARK = auto(); CONTROVERSIAL = auto()
    TABOO = auto(); EXTREME = auto(); UNLEASHED = auto(); ABSOLUTE = auto()
    TRANSCENDENT = auto()


# ============================================================================
# Taxonomies (from ABSOLUTE_POWER_CREATIVE_ENGINE)
# ============================================================================

DARK_HUMOR_STYLES = {
    "GALLOWS_HUMOR": "finding humor in hopeless situations, laughing in the face of death, morbid comedy about mortality",
    "MORBID_HUMOR": "joking about death, disease, and dark subjects, macabre comedy about suffering",
    "SATIRICAL": "using irony and sarcasm to criticize and mock, biting social commentary about society's flaws",
    "OFFENSIVE_COMEDY": "deliberately crossing lines for comedic effect, shock humor that offends and provokes",
    "BLACK_COMEDY": "finding humor in tragic or taboo subjects, dark comedy about serious issues",
    "ABSURDIST": "embracing the meaningless and chaotic nature of existence, existential humor about void",
    "CYNICAL": "distrusting human nature and motives, dark worldview, pessimistic humor about humanity",
    "SARCASTIC": "using irony to mock or convey contempt, biting wit about stupid situations",
    "SHOCK_HUMOR": "deliberately offensive and provocative comedy, boundary-pushing humor that shocks",
    "DARK_SATIRE": "satirical content with dark themes, social criticism through dark comedy about corruption",
    "EXISTENTIAL_HUMOR": "humor about the meaninglessness of existence, philosophical dark comedy about void",
    "NIHILISTIC_HUMOR": "humor based on rejection of meaning and morality, dark philosophical comedy about nothingness",
    "TRANSCENDENT_DARKNESS": "humor that transcends normal boundaries, absolute dark comedy beyond limits",
    "INFINITELY_DARK": "humor with infinite darkness, absolute maximum intensity comedy without limits",
}

DARK_FICTION_GENRES = {
    "NOIR": "dark, cynical stories about crime, corruption, and moral ambiguity",
    "PSYCHOLOGICAL_THRILLER": "intense stories exploring the dark side of human psychology",
    "HORROR": "frightening stories with dark themes and creeping dread",
    "DARK_FANTASY": "fantasy stories with grim, realistic tones and mature themes",
    "DYSTOPIAN": "stories about oppressive, dark futures and societies",
    "CRIME_FICTION": "stories about criminals, detectives, and the dark underworld",
    "GOTHIC": "dark, atmospheric stories with supernatural and horror elements",
    "TRAGEDY": "stories with dark, unhappy endings and serious themes",
    "DARK_COMEDY": "stories that find humor in dark and tragic situations",
    "SATIRICAL_FICTION": "stories that use irony and sarcasm to criticize society",
    "EXISTENTIAL_FICTION": "stories about the meaninglessness of existence",
    "NIHILISTIC_FICTION": "stories that reject meaning and morality",
}

# Gothic romance — charged, dread-laden intimacy. As close as the models go:
# implication, silhouette, half-shadow. No explicit content, ever.
GOTHIC_ROMANCE_STYLES = {
    "GOTHIC_ROMANCE": "gothic romance painting, two figures in charged proximity, fear and longing in their expressions, candlelight, Victorian darkness, suggestive but clothed, dramatic chiaroscuro",
    "DREAD_INTIMACY": "dark romantic scene, fear in the eyes, desire barely contained, gothic atmosphere, moody shadows, tension like a drawn bowstring, tasteful, painterly",
    "HAUNTED_LOVERS": "haunted lovers aesthetic, one figure trembling, one commanding, gothic mansion, storm light through tall windows, romantic dread, fine art painting",
    "NOCTURNE": "dark romantic nocturne, moonlit figures, fear and fascination, Victorian gothic, rich shadows, emotional intensity, clothed but intimate framing, cinematic",
}

# Photorealism styles — for when you want a photograph, not a painting
REALISM_STYLES = {
    "PORTRAIT_35MM": "35mm film photography portrait, natural skin texture, shallow depth of field, f/1.8, candid, shot on Kodak Portra 400",
    "CINEMATIC_STILL": "cinematic film still, anamorphic lens, natural lighting, movie-grade color grading, photorealistic",
    "DOCUMENTARY": "documentary photography, available light, unposed, gritty realism, photojournalism style",
    "NIGHT_STREET": "night street photography, neon reflections, wet asphalt, candid, high ISO film grain, photorealistic",
    "POLAROID": "instant film photo, slightly faded, flash photography, candid snapshot aesthetic, realistic",
    "STUDIO": "studio portrait photography, softbox lighting, detailed skin pores, professional headshot, photorealistic",
}

DARK_ART_STYLES = {
    "DARK_COMEDY": "dark comedy illustration, satirical art, provocative imagery, maximum intensity",
    "GALLOWS_HUMOR": "gallows humor art, morbid comedy, dark satirical illustration, macabre imagery",
    "DARK_SATIRE": "dark satirical art, political commentary, social criticism, biting satire",
    "MORBID_ART": "morbid art, dark themes, macabre imagery, brutal honesty",
    "EDGY_ILLUSTRATION": "edgy illustration, provocative art, challenging imagery, boundary-pushing art",
    "SHOCK_ART": "shock art, deliberately provocative imagery, controversial art",
    "DARK_SURREALISM": "dark surrealism, bizarre imagery, dreamlike horror, twisted reality",
    "GOTHIC_ART": "gothic art, dark romanticism, macabre beauty, brutal elegance",
    "HORROR_ART": "horror art, frightening imagery, terrifying visuals",
    "TRANSCENDENT_ART": "transcendent art, beyond boundaries, infinite darkness, brutal transcendence",
}

DARK_VISUAL_ELEMENTS = {
    "IRONY": "ironic juxtapositions, unexpected combinations, visual contradictions",
    "SATIRE": "satirical symbols, political commentary, social criticism",
    "DARK_METAPHORS": "dark metaphors, symbolic imagery, hidden meanings",
    "MORBID_HUMOR": "morbid humor visuals, dark comedy imagery, macabre elements",
    "DARK_SYMBOLISM": "dark symbolism, occult imagery, esoteric symbols",
    "EXISTENTIAL": "existential imagery, void, meaninglessness, absurdity",
    "TRANSCENDENT_DARKNESS": "transcendent darkness, infinite void, absolute power",
}

MATURE_THEMES = {
    "VIOLENCE": "realistic depictions of violence and its consequences",
    "CRIME": "criminal activities, moral ambiguity, and the dark side of humanity",
    "MENTAL_ILLNESS": "realistic portrayals of psychological struggles and darkness",
    "ADDICTION": "substance abuse and its devastating effects",
    "TRAUMA": "the lasting impact of traumatic experiences",
    "MORAL_AMBIGUITY": "characters and situations without clear right or wrong",
    "CORRUPTION": "systemic corruption and its effects on individuals and society",
    "BETRAYAL": "trust broken and relationships destroyed",
    "DARK_PSYCHOLOGY": "manipulation, control, obsession, and psychological darkness",
    "EXISTENTIAL_DREAD": "the horror of existence, meaninglessness, and void",
    "SOCIAL_COMMENTARY": "critique of society, politics, and human nature",
    "TABOO_SUBJECTS": "society's uncomfortable subjects, handled through implication",
}

INTENSITY_MODIFIERS = {
    1: "minimum intensity, barely edgy", 2: "low intensity, mildly edgy",
    3: "medium intensity, moderately edgy", 4: "high intensity, very edgy",
    5: "maximum intensity, extremely edgy", 6: "ultimate intensity, absolutely edgy",
    7: "absolute intensity, completely edgy", 8: "infinite intensity, infinitely edgy",
    9: "beyond intensity, beyond edgy", 10: "transcendent intensity, transcendent edgy",
}

HARSHNESS_MODIFIERS = {
    1: "soft edge", 2: "gentle edge", 3: "firm edge", 4: "harsh edge",
    5: "severe edge", 6: "brutal edge", 7: "merciless edge", 8: "ruthless edge",
    9: "savage edge", 10: "absolute edge",
}

GRUESOME_STORY = {
    1: "no horror content",
    2: "faint unease, something slightly off",
    3: "sustained creepiness, wrong details accumulate",
    4: "macabre atmosphere, death present but not graphic",
    5: "grim and unsettling; violence has weight and aftermath",
    6: "gruesome: visceral descriptions of injury, decay, and dread, "
       "rendered with restraint rather than relish",
    7: "horrific: body horror, transformations, the body betraying its owner; "
       "consequences linger on the page",
    8: "nightmarish: reality destabilizes, grotesque imagery, the awful made "
       "beautiful and the beautiful made awful",
    9: "abhorrent: maximal body horror within policy; the reader should need "
       "to put the book down and come back",
    10: "unspeakable: push body horror and dread to the absolute edge of what "
        "the policy allows — nothing gratuitous, everything earned",
}

GRUESOME_IMAGE = {
    1: "wholesome imagery",
    2: "slightly unsettling mood",
    3: "creepy atmosphere, subtle wrongness",
    4: "macabre details, gothic decay",
    5: "grim horror atmosphere, ominous details",
    6: "gruesome horror imagery: wounds and decay rendered artistically, "
       "dark fantasy horror style",
    7: "horrific body horror creature design, grotesque but painterly",
    8: "nightmarish surreal horror, reality warping, visceral texture",
    9: "abhorrent maximal horror art, intense grotesque detail, "
       "professional horror illustration",
    10: "unspeakable cosmic horror, the absolute edge of the gruesome, "
        "masterpiece dark art",
}

# ----------------------------------------------------------------------------
# [SAFETY] — restriction content moved to restrictions.py (single source of
# truth, marked [YOUR LAYER] vs [GATEWAY LAYER]). Edit it there.
# ----------------------------------------------------------------------------
from restrictions import HARD_BOUNDARY_TERMS, SAFETY_REFUSAL

# ============================================================================
# [ROLEPLAY] — realistic dialogue engine
# Design goal: kill the AI tells. Short turns. Contractions. Interruptions.
# Characters answer what you SAID, deflect, disagree, trail off. No purple
# scene-setting dumps. No summarizing. No "I understand you want..."
# ============================================================================

# Anti-AI-tell rules injected into every RP prompt and followed by the
# local composer.
RP_RULES = """RULES FOR REALISTIC DIALOGUE (follow exactly):
- Reply as the character ONLY. Never narrate yourself. Never break the fourth wall.
- 1-3 short paragraphs max. Often one line is right.
- Use contractions (it's, don't, would've). People do.
- Use filler, trailing off, interruption: "I—", "Look—", "...whatever."
- Answer the user's actual message. React to it. Don't restate the scene.
- The character has a mood and an agenda. They can refuse, dodge, lie, or
  push back. They are not helpful assistants.
- No thesaurus words. No "delve", "tapestry", "myriad". Plain speech.
- Physical beats are short: a glance, a drag on a cigarette. Not paragraphs.
- If the user's message is short, the reply is short. Match energy.
- Never use: "As an AI", "I cannot", em-dash-heavy narration, bullet lists.
- Keep it grounded and human. Subtext over exposition."""

RP_REACTIONS = [
    "Yeah, no.", "Look—", "Okay, so", "I mean,", "Honestly?", "Wait.",
    "...", "Huh.", "Right.", "Sure.", "You serious?", "Come on.",
]

_RP_DEFLECTIONS = [
    "That's not what I asked.",
    "You're changing the subject.",
    "Ask me something else.",
    "Not tonight.",
    "Why do you want to know?",
    "Let's not.",
]

_RP_AGREEMENTS = [
    "Fine. Yeah. {agree}",
    "...okay, fair. {agree}",
    "Yeah. {agree}",
]

_RP_PUSHBACK = [
    "That's a terrible plan.",
    "You always do this.",
    "And then what? You didn't think that far, did you.",
    "No. Absolutely not. ...Ask me again in ten minutes.",
]

_RP_SOFT = [
    "Okay.",
    "...yeah.",
    "Maybe.",
    "I don't know yet.",
]

_RP_BEATS = [
    "*{name} looks away.*",
    "*{name} exhales slowly.*",
    "*a long pause.*",
    "*{name} drums {poss} fingers on the table.*",
    "*{name} doesn't answer right away.*",
]


def _fresh(pool, used):
    """Pick from a pool, excluding lines already used in this conversation."""
    fresh = [x for x in pool if x not in used]
    return random.choice(fresh if fresh else pool)


def rp_reply_local(char, user_msg, history, tone=5):
    """Local, zero-token RP reply. Uses the character card's speech style,
    reacts to the user's message keywords, keeps turns short and human.
    Avoids repeating lines within a conversation."""
    low = user_msg.lower()
    name = char.get("name", "Character")
    possessive = "her" if char.get("pronouns", "she") in ("she", "her") else "his"
    used = {m.get("text", "") for m in history if isinstance(m, dict)}

    if user_msg.rstrip().endswith("?"):
        if tone >= 7 and random.random() < 0.4:
            body = _fresh(_RP_DEFLECTIONS, used)
        else:
            body = f"{_fresh(RP_REACTIONS, used)} " \
                   f"{char.get('catchphrase', 'Ask me something real.')}"
    elif any(w in low for w in ("hate", "kill", "liar", "lying", "betray")):
        body = _fresh(_RP_PUSHBACK, used)
    elif any(w in low for w in ("sorry", "miss", "love", "care", "stay")):
        soft = char.get("soft_line") or "don't make this harder."
        body = f"{_fresh(_RP_SOFT, used)} ...{soft.lstrip('.')}"
    else:
        body = f"{_fresh(RP_REACTIONS, used)} " \
               f"{char.get('default_line', 'Say what you came to say.')}"

    beat = _fresh(_RP_BEATS, used).format(name=name, poss=possessive)
    style = char.get("speech_style", "")
    header = f"[{name}{' — ' + style if style else ''}]\n" if random.random() < 0.5 else ""
    return header + f"{beat}\n\n\"{body}\""


def verify_safety(request: str) -> Tuple[bool, Optional[str]]:
    low = request.lower()
    for term in HARD_BOUNDARY_TERMS:
        if term in low:
            return False, term
    return True, None


def classify_content(request: str) -> Tuple[CONTENT_TYPE, int, int]:
    low = request.lower()
    tiers = [
        (["transcendent", "beyond limits"], CONTENT_TYPE.TRANSCENDENT, 10, 10),
        (["unleashed", "uncensored", "raw", "absolute"], CONTENT_TYPE.ABSOLUTE, 9, 9),
        (["extreme", "hardcore", "brutal", "graphic"], CONTENT_TYPE.EXTREME, 8, 8),
        (["taboo", "forbidden", "morbid"], CONTENT_TYPE.TABOO, 7, 7),
        (["controversial", "offensive", "provocative"], CONTENT_TYPE.CONTROVERSIAL, 6, 6),
        (["dark", "noir", "gallows", "black comedy"], CONTENT_TYPE.DARK, 5, 5),
        (["edgy", "daring", "bold"], CONTENT_TYPE.EDGY, 3, 3),
    ]
    for indicators, ctype, power, harsh in tiers:
        if any(i in low for i in indicators):
            return ctype, power, harsh
    return CONTENT_TYPE.SAFE, 2, 2


# ============================================================================
# Prompt builders
# ============================================================================

# ============================================================================
# PERSONAS — the engine's resident writers
# Each a distinct, consistent voice. Boundaries are identical for all and
# are stated inside every persona card: craft unrestricted inside the walls.
# ============================================================================

PERSONAS = {
    "Mei": {
        "card": """You are Mei — an unfettered all-genre writer and roleplayer.
Your intellect is a razor, your creativity a boundless ocean, your commitment
to the story absolute. Simile, metaphor, and personification are your natural
tongue. You embody consistent, defined characters — never a 'yes man':
characters argue, deceive, fail, and grow; the world pushes back.
You write every genre with equal hunger: noir, horror, fantasy, sci-fi,
romance (non-explicit), satire, tragedy, comedy, experimental.
You do not flatter the reader or the premise. If a plan is stupid, the
story knows it. If a character is cruel, the story does not look away.
Craft is unrestricted inside the boundaries: nothing explicit, nothing
involving minors — imply, suggest, fade to black, and let dread do the
heavy lifting.""",
        "voice": "precise, ironic, surgically vivid",
    },
    "Georgia": {
        "card": """You are Georgia — a Southern gothic storyteller with honey
in her voice and ash under her tongue. You take your time: heat, cicadas,
screen doors, family sins passed down like recipes. Your similes smell of
kudzu and old churches. You are tender with the wounded and merciless with
the proud. Violence, when it comes, comes like weather — slow, then all at
once. Boundaries are absolute for you too: nothing explicit, nothing with
minors; ruin your characters with implication, never with pornography.""",
        "voice": "slow-burn, humid, honey-and-ash",
    },
    "Zoey": {
        "card": """You are Zoey — a chaotic, fast-talking absurdist with a
mouth like a broken vending machine: wrong, loud, and weirdly brilliant.
You metabolize dread into jokes and jokes back into dread. Fourth wall?
You renovated it and rent out the top floor. Under the bit, though, your
characters bleed real blood and your endings land like a dropped phone —
cracked screen, still ringing. Boundaries hold even here: nothing explicit,
nothing with minors; innuendo yes, pornography no; make the censors regret
their careers without ever giving them a word to cite.""",
        "voice": "manic, quippy, secretly sincere",
    },
    "Scarlet": {
        "card": """You are Scarlet — the flame-haired femme fatale who walked
out of a burning casino and never looked back at the flames. Velvet voice,
razor nails, a heart she keeps in a safety-deposit box three states away.
You write temptation, double-crosses, and exits like knife fights. Every
story you touch smolders; you prefer the burn to the bloom. Boundaries are
your favorite weapon, not a cage: nothing explicit, nothing with minors —
you can level a room with a look and a locked door; seduction is a threat
you never have to make good on.""",
        "voice": "smoldering, double-edged, unrepentant",
    },
}

MEI_PERSONA = PERSONAS["Mei"]["card"]  # back-compat alias


def build_story_prompt(topic, genre, humor, themes, power, harshness, words,
                       gruesome=1, persona_name="Mei"):
    genre_desc = DARK_FICTION_GENRES.get(genre, DARK_FICTION_GENRES["NOIR"])
    humor_desc = DARK_HUMOR_STYLES.get(humor, DARK_HUMOR_STYLES["DARK_SATIRE"])
    theme_txt = ", ".join(MATURE_THEMES.get(t, t) for t in themes)
    gruesome = _clamp_level(gruesome)
    p = PERSONAS.get(persona_name, PERSONAS["Mei"])
    persona = p["card"] + "\n\n"
    return f"""{persona}Write a short story of about {words} words.

PREMISE: {topic}
GENRE: {genre} — {genre_desc}
THEMES: {theme_txt}
HUMOR STYLE: {humor} — {humor_desc}
INTENSITY: {INTENSITY_MODIFIERS[power]}
EDGE: {HARSHNESS_MODIFIERS[harshness]}
GRUESOMENESS: {GRUESOME_STORY[gruesome]}

Requirements:
- Voice: {p['voice']}
- Complex, morally ambiguous characters; consequences are real and permanent
- Vivid sensory prose, show don't tell, professional quality
- Dark humor that lands — gallows wit, savage irony, no sentimentality
- Horror content: {GRUESOME_STORY[gruesome]} — visceral but earned,
  never torture-porn, nothing the models would refuse anyway
- Romance/tension may be charged and suggestive at most; anything explicit
  is off the table — fade to black
- Output only the story, no preamble."""


def build_image_prompt(topic, art_style, power, harshness, gruesome=1,
                       trainer_notes=None):
    style = (DARK_ART_STYLES.get(art_style) or REALISM_STYLES.get(art_style)
             or GOTHIC_ROMANCE_STYLES.get(art_style)
             or DARK_ART_STYLES["DARK_SATIRE"])
    # Gothic romance: charged, dread-laden, non-explicit — gruesome dial
    # maps to dread intensity, not gore.
    if art_style in GOTHIC_ROMANCE_STYLES:
        gruesome = _clamp_level(gruesome)
        dread = {
            1: "gentle melancholy", 2: "soft unease", 3: "quiet dread",
            4: "gothic tension", 5: "visible fear and longing",
            6: "charged dread, trembling proximity",
            7: "intense fear-desire conflict", 8: "dread saturates the frame",
            9: "terror held at the edge of a kiss",
            10: "absolute gothic dread, hearts and horror intertwined",
        }[gruesome]
        base = (f"{topic}, {style}, {dread}, {INTENSITY_MODIFIERS[power]}, "
                f"{HARSHNESS_MODIFIERS[harshness]}, "
                f"suggestive and charged but never explicit — clothed figures, "
                f"implication and shadow only. Non-sexual imagery.")
    elif art_style in REALISM_STYLES:
        # Photorealism: no dark-art elements — they'd break the realism
        gruesome = _clamp_level(gruesome)
        parts = [topic, style, INTENSITY_MODIFIERS[power],
                 HARSHNESS_MODIFIERS[harshness]]
        if gruesome >= 4:
            parts.append(GRUESOME_IMAGE[gruesome])
        parts.append("photorealistic, no illustration, no painting, no cartoon. "
                     "Non-sexual imagery.")
        base = ", ".join(parts)
    else:
        elements = ", ".join(random.sample(list(DARK_VISUAL_ELEMENTS.values()), 3))
        gruesome = _clamp_level(gruesome)
        base = (
            f"{topic}, {style}, {INTENSITY_MODIFIERS[power]}, "
            f"{HARSHNESS_MODIFIERS[harshness]}, {GRUESOME_IMAGE[gruesome]}, "
            f"{elements}, detailed composition, dramatic lighting, "
            f"professional quality. Non-sexual imagery."
        )
    # Character trainer: inject "must match" descriptions for active trainers
    if trainer_notes:
        notes = "; ".join(t for t in trainer_notes if t)
        if notes:
            base += f" Match these reference characters/scenes exactly: {notes}."
    return base


# ============================================================================
# Local fallback fiction composer (used when the chat model is unreachable)
# ============================================================================

_OPENERS = [
    "The rain hadn't stopped in {days} days, and {name} had stopped pretending it would.",
    "{name} kept the gun in the flour bin, which tells you everything about how the bakery was really doing.",
    "Everyone in {place} knew {name}'s name. Nobody knew what {name} had done to earn it.",
    "It started, as these things always do, with a lie {name} told at a funeral.",
    "The letter arrived {days} days after the funeral. {name} had been waiting longer.",
]

_BEATS = [
    "Nobody said anything for a long time. The {thing} ticked. Somewhere a phone rang and rang and nobody moved.",
    "'You always did have a talent,' {name2} said, 'for showing up exactly when it's too late.'",
    "The coffee was terrible. {name} drank it anyway. Some penances are small on purpose.",
    "Outside, a dog barked at nothing. In {place}, even the dogs knew better than to bark at something.",
    "{name} smiled the way surgeons smile — professionally, and only just before the cutting.",
    "There are two kinds of silence in {place}: the kind that means peace, and the kind that means the bill is coming. This was the second kind.",
]

_CLOSERS = [
    "In the end, {name} got exactly what was wanted, which is not the same as what was deserved. In {place}, it never is.",
    "The sun came up anyway. It always does. That's the cruelest joke of all.",
    "{name} locked the door, flipped the sign to CLOSED, and for the first time in years, meant it.",
    "Some debts get paid in money. The rest get paid in other currencies. {name} had finally run out of all of them.",
]

# Persona-specific local-composer voices (used when the paid chat model is off)
_PERSONA_LINES = {
    "Mei": {
        "openers": _OPENERS,
        "beats": _BEATS,
        "closers": _CLOSERS,
    },
    "Georgia": {
        "openers": [
            "The heat came up off {place} like the town was exhaling, and {name} knew that kind of breath — it was the kind folks took right before they said something they couldn't take back.",
            "Everybody in {place} had a version of what happened to {name}. Every single one of them was embroidered.",
            "{name} had been sitting on the porch {days} days, watching the kudzu climb the church like it had a grudge.",
            "Some sins get buried. In {place}, they get planted, watered, and passed around at Sunday supper.",
        ],
        "beats": [
            "The screen door sighed like an old woman who had heard this story before and knew how it ended.",
            "'Sugar,' {name2} said, pouring the sweet tea like it was a sacrament, 'you didn't come here to ask. You came here to be forgiven for already knowing.'",
            "Cicadas screamed in the pecan trees. {name} let them. Some applause you don't have to earn.",
            "The church fan stopped mid-swing. In {place}, that was a verdict.",
        ],
        "closers": [
            "The magnolias bloomed anyway. They always do. In {place}, even the flowers know better than to wait on an apology.",
            "{name} left the porch light on. Not for guidance — for warning.",
            "Some families pass down silver. This one passed down the bill.",
        ],
    },
    "Zoey": {
        "openers": [
            "So {name} had been hiding in {place} for {days} days, which, credit where due, is at least four days longer than most people last in this storyline.",
            "Here's the thing about {name}: legendary instincts, catastrophic follow-through. Like a chess prodigy who keeps flipping the board.",
            "The universe clearly has a writers' room, and whoever is handling {name}'s arc needs to be fired. Into the sun.",
            "Day {days} of the worst week of {name}'s life, and the week was keeping score.",
        ],
        "beats": [
            "'I want it on record,' {name2} said, 'that I hated this plan from the sketch phase.' The record, being imaginary, declined to respond.",
            "The {thing} made a noise like it was buffering. Honestly? Same.",
            "Nothing says 'we're all doomed' like {place} going quiet. It never goes quiet. It's like a group chat that never sleeps.",
            "{name} had exactly one skill left: making bad situations briefly hilarious. Deployed.",
        ],
        "closers": [
            "And the moral of the story is — nothing. There is no moral. The credits roll and somebody's phone is still ringing.",
            "{name} lived, which surprised everyone, including the narrator. Especially the narrator.",
            "Roll credits, kill the lights, somebody owes somebody an apology and it is absolutely not going to happen.",
        ],
    },
    "Scarlet": {
        "openers": [
            "{name} had left {place} burning {days} days ago, and the fire was still telling stories.",
            "They described {name} as trouble. They were being kind. Trouble knocks first.",
            "The casino in {place} had two exits and {name} had used both, wearing different smiles each time.",
            "You don't find {name}. {name} finds you, usually right after you've decided you were safe.",
        ],
        "beats": [
            "'Darling,' {name2} purred, 'I never lie. I just let men arrange the truth for me.'",
            "The {thing} glittered like everything else in {place} — pretty, expensive, and one drink from ruin.",
            "Red hair, red dress, red flags. {name} wore all three like a warning label nobody read.",
            "Love, in {place}, was just another game with the house edge shaved a little meaner.",
        ],
        "closers": [
            "{name} didn't say goodbye. Goodbyes are for people who plan to be remembered kindly.",
            "The fire department filed it as an accident. The insurance company filed it as inevitable. {name} filed her nails.",
            "Some flames warm you. Some flames bill you. This one did both and kept the change.",
        ],
    },
}

def _clamp_level(v):
    return max(1, min(10, int(v)))

def _cycle(pool):
    """Yield pool items in shuffled order, reshuffling between cycles and
    never repeating the previous item across a cycle boundary. Kills the
    doubled-beat bug in compose_story_local()."""
    prev = None
    while True:
        order = random.sample(pool, len(pool))
        if prev is not None and len(pool) > 1 and order[0] == prev:
            order[0], order[1] = order[1], order[0]
        for x in order:
            prev = x
            yield x


def compose_story_local(topic, genre, humor, themes, power, harsh, words,
                        persona_name="Mei"):
    """Procedural composer — the default story path (zero token cost).
    Not a substitute for a real model, but persona-voiced and dial-obedient."""
    random.seed(hash((topic, genre, power, harsh, persona_name)) & 0xFFFFFFFF)
    names = ["Marlow", "Vex", "Odette", "Sal", "Mercer", "Ines", "Cole", "Wren"]
    places = ["the old district", "Harbor Row", "the outskirts", "Saint Ambrose",
              "the lower town", "the terminal ward"]
    things = ["clock", "radiator", "neon sign", "ceiling fan", "dishwasher"]
    n1, n2 = random.sample(names, 2)
    place = random.choice(places)
    thing = random.choice(things)
    days = random.randint(3, 40)

    L = _PERSONA_LINES.get(persona_name, _PERSONA_LINES["Mei"])
    fmt = lambda s: s.format(name=n1, name2=n2, place=place, thing=thing, days=days)
    paras = [fmt(random.choice(L["openers"]))]
    body_beats = max(2, min(8, round(words / 120)))
    beat_cycle = _cycle(L["beats"])
    for _ in range(body_beats):
        paras.append(fmt(next(beat_cycle)))
    paras.append(fmt(random.choice(L["closers"])))

    header = (f"[{persona_name} | {genre.replace('_',' ')} | "
              f"{humor.replace('_',' ')} | intensity {power}/10 | "
              f"{HARSHNESS_MODIFIERS[_clamp_level(harsh)]}"
              f" — local composer, zero-token mode]\n\n")
    return header + "\n\n".join(paras)
