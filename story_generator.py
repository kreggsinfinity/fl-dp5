import os, sys, json, time, requests, re
import config

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

DEFAULT_5_ACTS = [
    ("Act 1: Setting the Foundation", "Opening thoughts and exploring why this theme matters in modern life"),
    ("Act 2: Escaping the Translation Delay", "Practical examples and shifts in mindset to think directly in English"),
    ("Act 3: Everyday Real-World Dialogues", "Roleplay conversations, natural expressions, and active listening reactions"),
    ("Act 4: Handling Awkward Moments & Blunders", "Mind blanks, rescue phrases, and turning small mistakes into humor"),
    ("Act 5: The Daily Fluency Challenge & Key Takeaways", "Actionable speaking exercises and closing thoughts for the week")
]

def load_history_topics() -> list:
    """Reads all past published topics from published_videos.json and history.json to ensure no repeats."""
    past = []
    for fname in ["published_videos.json", "history.json"]:
        fpath = os.path.join(config.BASE_DIR, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get("topic"):
                                t = item["topic"].strip()
                                if t not in past:
                                    past.append(t)
            except Exception:
                pass
    return past

def generate_dynamic_topic_ai(past_topics: list, ep_num: int = 1) -> dict:
    """Queries Pollinations AI with past topics history to generate a brand new non-repeating topic."""
    key = config.POLLINATIONS_API_KEY
    if not key:
        return None

    past_sample = past_topics[-30:] if len(past_topics) > 30 else past_topics
    prompt = (
        "You are the creative executive producer for '" + config.CHANNEL_NAME + "' English podcast.\n"
        "Channel Tagline: " + config.TAGLINE + "\n"
        "Niche Style: " + config.NICHE_PROMPT + "\n\n"
        "CRITICAL REQUIREMENT:\n"
        "Previously published topics (DO NOT REPEAT OR CLOSELY DUPLICATE ANY OF THESE):\n"
        + json.dumps(past_sample, indent=2) + "\n\n"
        "Generate ONE brand new, highly engaging, practical English learning episode topic tailored specifically for this channel's style and audience.\n"
        "Episode #" + str(ep_num) + ".\n\n"
        "OUTPUT FORMAT: Return ONLY a valid JSON object matching this schema (no markdown, no other text):\n"
        "{\n"
        '  "id": "ep_' + str(ep_num) + '",\n'
        '  "topic": "Catchy Full Episode Title",\n'
        '  "focus": "Brief overview of what listeners will master today",\n'
        '  "thumbnail_title_1": "FIRST 2-3 WORDS (MAX 16 CHARS)",\n'
        '  "thumbnail_title_2": "SECOND 2-3 WORDS (MAX 16 CHARS)",\n'
        '  "thumbnail_hook": "Catchy Subtitle Hook",\n'
        '  "acts": [\n'
        '    ["Act 1: Title", "Detailed focus description..."],\n'
        '    ["Act 2: Title", "Detailed focus description..."],\n'
        '    ["Act 3: Title", "Detailed focus description..."],\n'
        '    ["Act 4: Title", "Detailed focus description..."],\n'
        '    ["Act 5: Title", "Detailed focus description..."]\n'
        '  ]\n'
        "}"
    )

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": config.POLLINATIONS_MODEL,
        "messages": [
            {"role": "system", "content": "You are a professional podcast producer. Return ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.85
    }

    for attempt in range(3):
        try:
            print(f"[StoryGenerator] Synthesizing dynamic topic via AI (attempt {attempt+1}/3)...")
            resp = requests.post(config.POLLINATIONS_ENDPOINT, json=payload, headers=headers, timeout=25)
            if resp.status_code == 200:
                raw = resp.json()["choices"][0]["message"]["content"].strip()
                if raw.startswith("```"):
                    raw = re.sub(r"^```(?:json)?\s*", "", raw)
                    raw = re.sub(r"\s*```$", "", raw)
                data = json.loads(raw)
                topic_val = data.get("topic", "")
                if topic_val and data.get("acts") and len(data["acts"]) >= 4:
                    t_lower = topic_val.lower().strip()
                    past_lowers = [p.lower().strip() for p in past_topics]
                    if t_lower not in past_lowers:
                        print(f"[StoryGenerator] Dynamically generated new topic: '{topic_val}'")
                        return data
        except Exception as e:
            print(f"[StoryGenerator] Dynamic topic attempt {attempt+1} error: {e}")
            time.sleep(1.5)
    return None

def get_next_topic(history: list, custom_topic: str = None, ep_num: int = 1) -> dict:
    if custom_topic:
        words = custom_topic.split()
        mid = len(words) // 2
        t1 = " ".join(words[:mid]) if mid > 0 else words[0]
        t2 = " ".join(words[mid:]) if mid > 0 else "CONVERSATION"
        return {
            "id": "custom",
            "topic": custom_topic,
            "focus": "Engaging conversational discussion on this theme",
            "thumbnail_title_1": t1[:18].upper(),
            "thumbnail_title_2": t2[:18].upper(),
            "thumbnail_hook": "20-Minute English Conversation",
            "acts": DEFAULT_5_ACTS
        }

    past_topics = load_history_topics()

    # 1. Try Dynamic AI topic generation first
    ai_topic = generate_dynamic_topic_ai(past_topics, ep_num=ep_num)
    if ai_topic:
        t1 = ai_topic.get("thumbnail_title_1", "")
        t2 = ai_topic.get("thumbnail_title_2", "")
        if not t1 or not t2:
            words = ai_topic["topic"].split()
            mid = len(words) // 2
            t1 = " ".join(words[:mid])
            t2 = " ".join(words[mid:])
        return {
            "id": ai_topic.get("id", f"ep_{ep_num}"),
            "topic": ai_topic["topic"],
            "focus": ai_topic.get("focus", "Engaging conversational practice"),
            "thumbnail_title_1": t1[:18].upper(),
            "thumbnail_title_2": t2[:18].upper(),
            "thumbnail_hook": ai_topic.get("thumbnail_hook", "20-Minute English Conversation"),
            "acts": ai_topic.get("acts", DEFAULT_5_ACTS)
        }

    # 2. Fallback: Search CURRICULUM_CATALOG for unvisited topic
    past_lowers = [p.lower().strip() for p in past_topics]
    for idx, (title, focus) in enumerate(CURRICULUM_CATALOG):
        if title.lower().strip() not in past_lowers:
            print(f"[StoryGenerator] Selected unvisited curriculum topic: '{title}'")
            words = title.split()
            mid = len(words) // 2
            t1 = " ".join(words[:mid])
            t2 = " ".join(words[mid:])
            return {
                "id": f"ep_{ep_num}",
                "topic": title,
                "focus": focus,
                "thumbnail_title_1": t1[:18].upper(),
                "thumbnail_title_2": t2[:18].upper(),
                "thumbnail_hook": "20-Minute English Conversation",
                "acts": DEFAULT_5_ACTS
            }

    # 3. If all catalog topics used, create advanced cycle variation
    cycle = (ep_num - 1) // len(CURRICULUM_CATALOG) + 1
    cat_idx = (ep_num - 1) % len(CURRICULUM_CATALOG)
    base_title, base_focus = CURRICULUM_CATALOG[cat_idx]
    title = f"{base_title}: Part {cycle} - Advanced Fluency"
    words = title.split()
    mid = len(words) // 2
    t1 = " ".join(words[:mid])
    t2 = " ".join(words[mid:])
    return {
        "id": f"ep_{ep_num}",
        "topic": title,
        "focus": f"Advanced depth on {base_focus}",
        "thumbnail_title_1": t1[:18].upper(),
        "thumbnail_title_2": t2[:18].upper(),
        "thumbnail_hook": f"Masterclass Series Part {cycle}",
        "acts": DEFAULT_5_ACTS
    }

def generate_act_ai(act_idx: int, act_title: str, topic_title: str, focus: str, target_turns: int = 40) -> list:
    key = config.POLLINATIONS_API_KEY
    if not key:
        return None

    prompt = (
        f"Write an engaging dialogue for English podcast '{config.CHANNEL_NAME}'.\n"
        f"Hosts: {config.HOST1_NAME} ({config.HOST1_SPEAKER}) and {config.HOST2_NAME} ({config.HOST2_SPEAKER}).\n"
        f"Niche: {config.NICHE_PROMPT}.\n"
        f"Topic: {topic_title}\n"
        f"Act {act_idx + 1}: {act_title}\n"
        f"Focus: {focus}\n\n"
        f"REQUIREMENTS:\n"
        f"- Exactly {target_turns} dialogue turns alternating {config.HOST1_NAME} and {config.HOST2_NAME}.\n"
        f"- Keep each turn natural, clear, and conversational (12-22 words per turn).\n"
        f"- Warm, insightful, friendly chemistry between hosts.\n"
        f"- Strictly return valid raw JSON array only:\n"
        f"[\n"
        f'  {{"speaker": "{config.HOST1_SPEAKER}", "name": "{config.HOST1_NAME}", "text": "..."}},\n'
        f'  {{"speaker": "{config.HOST2_SPEAKER}", "name": "{config.HOST2_NAME}", "text": "..."}}\n'
        f"]"
    )

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

def generate_curated_fallback_act(act_idx: int, act_title: str, topic: str, target_turns: int = 40) -> list:
    h1 = config.HOST1_NAME
    h2 = config.HOST2_NAME
    s1 = config.HOST1_SPEAKER
    s2 = config.HOST2_SPEAKER
    cname = config.CHANNEL_NAME

    base_dialogue = [
        {"speaker": s1, "name": h1, "text": f"Welcome back to {cname}. Today we are discussing {topic}."},
        {"speaker": s2, "name": h2, "text": "It is such an essential theme for anyone looking to feel truly confident speaking English."},
        {"speaker": s1, "name": h1, "text": "When you listen to natural conversation, your brain absorbs the rhythm and melody effortlessly."},
        {"speaker": s2, "name": h2, "text": "Exactly. You start noticing the natural pauses and word connections without memorizing dry grammar."},
        {"speaker": s1, "name": h1, "text": "Let us take a deep breath and explore how this applies to everyday life."},
        {"speaker": s2, "name": h2, "text": "I love that perspective. The small moments in conversation often carry the deepest meaning."},
        {"speaker": s1, "name": h1, "text": "Have you ever found yourself in a situation where you knew what to say, but hesitated?"},
        {"speaker": s2, "name": h2, "text": "All the time! Everyone experiences that hesitation, even in their native tongue."},
        {"speaker": s1, "name": h1, "text": "The key is giving yourself permission to speak without demanding absolute perfection."},
        {"speaker": s2, "name": h2, "text": "Communication is about warmth and connection, not about taking an academic exam."},
        {"speaker": s1, "name": h1, "text": "Notice how native speakers use comfortable transition words when they want time to think."},
        {"speaker": s2, "name": h2, "text": "Phrases like 'To be honest' or 'Come to think of it' buy you valuable seconds."},
        {"speaker": s1, "name": h1, "text": "They make you sound composed and relaxed rather than rushed."},
        {"speaker": s2, "name": h2, "text": "Let us also remember the power of asking open questions during any conversation."},
        {"speaker": s1, "name": h1, "text": "Questions that begin with 'How' or 'Why' invite wonderful, rich stories."},
        {"speaker": s2, "name": h2, "text": "And when someone shares a story, simple reactions like 'I hear you' build instant rapport."},
        {"speaker": s1, "name": h1, "text": "Repeat these expressions out loud with us as you listen today."},
        {"speaker": s2, "name": h2, "text": "Speaking out loud trains your mouth muscles and tongue to glide smoothly."},
        {"speaker": s1, "name": h1, "text": "Every single minute you spend listening brings you closer to your speaking goals."},
        {"speaker": s2, "name": h2, "text": "Be proud of dedicating this time today to your personal growth and English fluency."}
    ]
    result = []
    while len(result) < target_turns:
        for turn in base_dialogue:
            result.append(dict(turn))
            if len(result) >= target_turns:
                break
    return result

def generate_full_podcast_story(target_minutes: float = 20.0, topic: str = None, ep_num: int = 1) -> dict:
    history = load_history_topics()
    topic_info = get_next_topic(history, custom_topic=topic, ep_num=ep_num)
    selected_topic = topic_info["topic"]
    acts_meta = topic_info.get("acts", DEFAULT_5_ACTS)

    print(f"[StoryGenerator] Episode #{ep_num} Topic: '{selected_topic}'")

    # Target 20 minutes: ~190-200 turns total (~38-40 turns per act)
    turns_per_act = int(max(4, (target_minutes * 60) / (len(acts_meta) * 6.0)))
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

    print(f"[StoryGenerator] Completed {len(dialogue)} total dialogue turns across {len(acts_meta)} acts (~20 minutes).")
    return {
        "topic": selected_topic,
        "thumbnail_title_1": topic_info["thumbnail_title_1"],
        "thumbnail_title_2": topic_info["thumbnail_title_2"],
        "thumbnail_hook": topic_info["thumbnail_hook"],
        "chapters": chapters,
        "dialogue": dialogue
    }

def generate_metadata(topic: str, duration_sec: float, chapters: list, ep_num: int = 1) -> dict:
    title = f"{topic} | {config.CHANNEL_NAME} Ep. {ep_num}"
    lines = [
        f"🎙️ Welcome to {config.CHANNEL_NAME} Episode #{ep_num}!",
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
        f"#{config.CHANNEL_NAME.replace(' ', '')} #LearnEnglish #EnglishPodcast #EnglishConversation"
    ])

    return {
        "title": title[:100],
        "description": "\n".join(lines),
        "tags": ["learn english", "english podcast", config.CHANNEL_NAME.lower(), "english conversation", "english listening"]
    }
