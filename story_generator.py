import os, json, requests, config

CURRICULUM_CATALOG = [
    [
        "Why We Make Irrational Decisions",
        "Cognitive biases, impulse shopping, and the psychology of choice"
    ],
    [
        "The Art of Meaningful Conversation",
        "Moving past superficial small talk into genuine human connection"
    ],
    [
        "Books That Reshape How We Think",
        "Timeless philosophies, stoic principles, and modern memoirs"
    ],
    [
        "Navigating Uncertainty in Life",
        "How to embrace ambiguity and make peace with the unknown"
    ],
    [
        "The Paradox of Choice in the Digital Era",
        "Why infinite options make us more anxious and how to simplify"
    ],
    [
        "Building Unbreakable Focus",
        "Digital distraction traps, deep work states, and protecting attention"
    ],
    [
        "The Architecture of Good Habits",
        "How identity-based habits create compounding life transformations"
    ],
    [
        "Empathy in an Opinionated World",
        "Listening to understand rather than listening to counter-argue"
    ],
    [
        "The True Definition of Success",
        "Wealth vs peace of mind, societal expectations, and personal freedom"
    ],
    [
        "Overcoming Imposter Syndrome",
        "Why capable people doubt themselves and owning your hard-won growth"
    ]
]

def get_next_topic(history: list, custom_topic: str = None, ep_num: int = 1) -> dict:
    if custom_topic:
        words = custom_topic.split()
        mid = len(words) // 2
        t1 = " ".join(words[:mid]) if mid > 0 else words[0]
        t2 = " ".join(words[mid:]) if mid > 0 else "CONVERSATION"
        return {
            "id": "custom",
            "title": custom_topic,
            "focus": "Engaging conversational discussion on this theme",
            "thumb_1": t1[:18],
            "thumb_2": t2[:18],
            "hook": "20-Minute English Conversation"
        }

    idx = (ep_num - 1) % len(CURRICULUM_CATALOG)
    title, focus = CURRICULUM_CATALOG[idx]
    words = title.split()
    mid = len(words) // 2
    t1 = " ".join(words[:mid])
    t2 = " ".join(words[mid:])
    return {
        "id": f"ep_{ep_num}",
        "title": title,
        "focus": focus,
        "thumb_1": t1[:18],
        "thumb_2": t2[:18],
        "hook": "20-Minute English Conversation"
    }

def generate_act_ai(act_idx: int, act_title: str, topic_title: str, focus: str, target_turns: int = 36) -> list:
    key = config.POLLINATIONS_API_KEY
    if not key:
        return None

    prompt = f"""Write an engaging dialogue for English podcast 'DEEP ENGLISH DIALOGUES'.
Hosts: Elena (female) and Marcus (male).
Niche: intellectual, thought-provoking dialogue examining psychology, decision-making, books, and human perspectives.
Topic: {topic_title}
Act {act_idx + 1}: {act_title}
Focus: {focus}

REQUIREMENTS:
- Exactly {target_turns} dialogue turns alternating Elena and Marcus.
- Keep each turn natural, clear, and conversational (12-22 words per turn).
- Warm, insightful, friendly chemistry between hosts.
- Strictly return valid raw JSON array only:
[
  {{"speaker": "female", "name": "Elena", "text": "..."}},
  {{"speaker": "male", "name": "Marcus", "text": "..."}}
]"""

    try:
        resp = requests.post(
            config.POLLINATIONS_ENDPOINT,
            json={
                "model": config.POLLINATIONS_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a JSON-only API. Return only a raw JSON array of dialogue objects."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.75
            },
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=25
        )
        if resp.status_code == 200:
            content = resp.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:].strip()
                content = content.strip()
            parsed = json.loads(content)
            if isinstance(parsed, list) and len(parsed) >= 15:
                return parsed[:target_turns]
    except Exception as e:
        print(f"  [AI Note] Act {act_idx+1} Pollinations call error ({e}), using curated master script.")
    return None

def generate_curated_fallback_act(act_idx: int, act_title: str, topic: str, target_turns: int = 36) -> list:
    base_dialogue = [
        {"speaker": "female", "name": "Elena", "text": f"Welcome back to DEEP ENGLISH DIALOGUES. Today we are discussing {topic}."},
        {"speaker": "male", "name": "Marcus", "text": "It is such an essential theme for anyone looking to feel truly confident speaking English."},
        {"speaker": "female", "name": "Elena", "text": "When you listen to natural conversation, your brain absorbs the rhythm and melody effortlessly."},
        {"speaker": "male", "name": "Marcus", "text": "Exactly. You start noticing the natural pauses and word connections without memorizing dry grammar."},
        {"speaker": "female", "name": "Elena", "text": "Let us take a deep breath and explore how this applies to everyday life."},
        {"speaker": "male", "name": "Marcus", "text": "I love that perspective. The small moments in conversation often carry the deepest meaning."},
        {"speaker": "female", "name": "Elena", "text": "Have you ever found yourself in a situation where you knew what to say, but hesitated?"},
        {"speaker": "male", "name": "Marcus", "text": "All the time! Everyone experiences that hesitation, even in their native tongue."},
        {"speaker": "female", "name": "Elena", "text": "The key is giving yourself permission to speak without demanding absolute perfection."},
        {"speaker": "male", "name": "Marcus", "text": "Communication is about warmth and connection, not about taking an academic exam."},
        {"speaker": "female", "name": "Elena", "text": "Notice how native speakers use comfortable transition words when they want time to think."},
        {"speaker": "male", "name": "Marcus", "text": "Phrases like 'To be honest' or 'Come to think of it' buy you valuable seconds."},
        {"speaker": "female", "name": "Elena", "text": "They make you sound composed and relaxed rather than rushed."},
        {"speaker": "male", "name": "Marcus", "text": "Let us also remember the power of asking open questions during any conversation."},
        {"speaker": "female", "name": "Elena", "text": "Questions that begin with 'How' or 'Why' invite wonderful, rich stories."},
        {"speaker": "male", "name": "Marcus", "text": "And when someone shares a story, simple reactions like 'I hear you' build instant rapport."},
        {"speaker": "female", "name": "Elena", "text": "Repeat these expressions out loud with us as you listen today."},
        {"speaker": "male", "name": "Marcus", "text": "Speaking out loud trains your mouth muscles and tongue to glide smoothly."},
        {"speaker": "female", "name": "Elena", "text": "Every single minute you spend listening brings you closer to your speaking goals."},
        {"speaker": "male", "name": "Marcus", "text": "Be proud of dedicating this time today to your personal growth and English fluency."}
    ]
    # Expand to target turns if needed
    result = []
    while len(result) < target_turns:
        for turn in base_dialogue:
            result.append(dict(turn))
            if len(result) >= target_turns:
                break
    return result

def generate_full_podcast_story(target_minutes: float = 20.0, topic: str = None, ep_num: int = 1) -> dict:
    history = []
    h_file = os.path.join(config.BASE_DIR, "published_videos.json")
    if os.path.exists(h_file):
        try:
            with open(h_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass

    topic_info = get_next_topic(history, custom_topic=topic, ep_num=ep_num)
    selected_topic = topic_info["title"]
    print(f"[StoryGenerator] Episode #{ep_num} Topic: '{selected_topic}'")

    # Plan 5 Acts
    acts_meta = [
        ("Act 1: Setting the Foundation", "Opening thoughts and exploring why this theme matters in modern life"),
        ("Act 2: Escaping the Translation Delay", "Practical examples and shifts in mindset to think directly in English"),
        ("Act 3: Everyday Real-World Dialogues", "Roleplay conversations, natural expressions, and active listening reactions"),
        ("Act 4: Handling Awkward Moments & Blunders", "Mind blanks, rescue phrases, and turning small mistakes into humor"),
        ("Act 5: The Daily Fluency Challenge & Key Takeaways", "Actionable speaking exercises and closing thoughts for the week")
    ]

    # For 20 minutes, ~180-200 turns (~36-40 turns per act)
    turns_per_act = int(max(4, (target_minutes * 60) / (len(acts_meta) * 6.2)))
    if target_minutes <= 1.0:
        turns_per_act = 2
    elif target_minutes <= 3.0:
        turns_per_act = 4

    dialogue = []
    chapters = []

    for act_idx, (act_title, act_focus) in enumerate(acts_meta):
        chapters.append({"title": act_title, "start_turn": len(dialogue)})
        print(f"  [Act {act_idx+1}/5] Generating '{act_title}' ({turns_per_act} turns)...")

        turns = generate_act_ai(act_idx, act_title, selected_topic, act_focus, target_turns=turns_per_act)
        if not turns:
            turns = generate_curated_fallback_act(act_idx, act_title, selected_topic, target_turns=turns_per_act)

        dialogue.extend(turns)

    print(f"[StoryGenerator] Completed {len(dialogue)} total dialogue turns across 5 acts.")
    return {
        "topic": selected_topic,
        "thumbnail_title_1": topic_info["thumb_1"],
        "thumbnail_title_2": topic_info["thumb_2"],
        "thumbnail_hook": topic_info["hook"],
        "chapters": chapters,
        "dialogue": dialogue
    }

def generate_metadata(topic: str, duration_sec: float, chapters: list, ep_num: int = 1) -> dict:
    title = f"{topic} | DEEP ENGLISH DIALOGUES Ep. {ep_num}"
    lines = [
        f"🎙️ Welcome to DEEP ENGLISH DIALOGUES Episode #{ep_num}!",
        f"Today we explore: {topic}.",
        "",
        "🕒 CHAPTERS & TIMESTAMPS:"
    ]
    for ch in chapters:
        m = int(ch.get("start_time", 0) // 60)
        s = int(ch.get("start_time", 0) % 60)
        lines.append(f"{m:02d}:{s:02d} - {ch['title']}")

    lines.extend([
        "",
        "💡 Relax, listen, and immerse yourself in natural English conversation.",
        "👉 Follow our page for daily English podcast episodes!",
        f"#DEEPENGLISHDIALOGUES #LearnEnglish #EnglishPodcast #EnglishConversation"
    ])

    return {
        "title": title[:100],
        "description": "\n".join(lines),
        "tags": ["learn english", "english podcast", "deep english dialogues", "english conversation", "english listening"]
    }
