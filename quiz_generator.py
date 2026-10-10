"""
ENGLISH QUIZ MASTERCLASS PODCAST - 16:9 FULL HD (1920x1080) VIDEO GENERATOR
Theme: Broadcast Quiz Stage & Grammar Challenge
Visuals: Interactive Holographic Quiz Board + Dual Broadcast Mics + 24-Segment Stereo VU Equalizer + Single-Line Highlighted Subtitles
"""
import os, sys, json, math, subprocess, random, requests, re, asyncio
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from dotenv import load_dotenv
import edge_tts

if sys.platform == 'win32':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except Exception: pass

load_dotenv()

BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
SUBFRAMES_PER_SEC = 2

ROYAL_BLUE = (37, 99, 235)
ELECTRIC_BLUE = (59, 130, 246)
GOLD_ACCENT = (250, 204, 21)
CORRECT_GREEN = (16, 185, 129)
WHITE = (255, 255, 255)
DARK_BG = (10, 15, 30)
CARD_BG = (16, 25, 48)
CARD_BORDER = (45, 65, 110)
MUTED_TEXT = (160, 180, 210)

EMMA_VOICE = "en-US-AvaNeural"
ANDREW_VOICE = "en-US-AndrewNeural"
VOICE_RATE = "-15%"

TOPICS = [
    {
        "topic": "Can You Pass This Present Perfect Grammar Test?",
        "question": "She ________ to Paris three times.",
        "opt_a": "A) has been  [CORRECT]",
        "opt_b": "B) was",
        "correct": "has been",
        "keyword": "EXPERIENCE",
        "sub": "PRESENT PERFECT VS SIMPLE PAST"
    },
    {
        "topic": "Gerund or Infinitive? Look Forward To Challenge",
        "question": "I look forward to ________ you tomorrow.",
        "opt_a": "A) seeing  [CORRECT]",
        "opt_b": "B) see",
        "correct": "seeing",
        "keyword": "GERUND",
        "sub": "PHRASAL VERB PREPOSITIONS"
    },
    {
        "topic": "Tricky Prepositions: In, On, or At Time Challenge",
        "question": "The concert begins ________ seven PM.",
        "opt_a": "A) at  [CORRECT]",
        "opt_b": "B) in",
        "correct": "at",
        "keyword": "PREPOSITION",
        "sub": "TIME AND LOCATION PREPOSITIONS"
    }
]

def load_font(size, bold=True):
    fonts_to_try = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/trebucbd.ttf" if bold else "C:/Windows/Fonts/trebuc.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in fonts_to_try:
        if Path(p).exists():
            try: return ImageFont.truetype(p, size)
            except: continue
    return ImageFont.load_default()

def clean_text(text):
    text = re.sub(r'\b(mm+|um+|uh+|ah+)\b', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def generate_script_ai(topic_item, target_turns=6):
    prompt = f"""Write {target_turns} turns of a slow, clear English podcast between Emma and Andrew.
Topic: {topic_item['topic']}
Quiz Question: {topic_item['question']}
Correct Answer: {topic_item['correct']}

RULES:
- Dialogue alternating between Host1 (Emma) and Host2 (Andrew)
- Each turn MUST be 2-3 short, clear sentences (18-28 words)
- Present the question, discuss why many learners get confused, and reveal the grammar explanation
- Wrap exactly 1 key learning word per turn in **asterisks**
- Return as clean JSON array only:
[{{"speaker":"Host1","text":"..."}},{{"speaker":"Host2","text":"..."}}]"""

    key = os.getenv("POLLINATIONS_API_KEY")
    if key:
        try:
            resp = requests.post("https://gen.pollinations.ai/v1/chat/completions", json={
                "model": "gemini-fast",
                "messages": [
                    {"role": "system", "content": "You write interactive, natural English quiz podcast dialogue. Wrap 1 key word per turn in **asterisks**."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8
            }, headers={"Authorization": f"Bearer {key}"}, timeout=60)
            if resp.status_code == 200:
                raw = resp.json()["choices"][0]["message"]["content"].strip()
                if "```json" in raw: raw = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw: raw = raw.split("```")[1].split("```")[0].strip()
                script = json.loads(raw)
                if isinstance(script, list) and len(script) > 0:
                    for i, turn in enumerate(script):
                        turn["speaker"] = "Host1" if i % 2 == 0 else "Host2"
                        turn["text"] = clean_text(turn["text"])
                        if "**" not in turn["text"]:
                            words = turn["text"].split()
                            if len(words) > 2:
                                idx = len(words) // 2
                                words[idx] = f"**{words[idx]}**"
                                turn["text"] = " ".join(words)
                    return script[:target_turns]
        except Exception as e:
            print(f"[script] AI note: {e}, using curated fallback.")

    return [
        {"speaker": "Host1", "text": f"Welcome back listeners! Today we have an exciting challenge for your **English** skills."},
        {"speaker": "Host2", "text": f"Here is the question: {topic_item['question']} Think about whether we use past tense or present **perfect**."},
        {"speaker": "Host1", "text": f"The correct answer is '{topic_item['correct']}', because we are talking about life **experiences** at unspecified times."},
        {"speaker": "Host2", "text": f"Great job if you got that right! Comment your score below to test your **mastery**!"}
    ][:target_turns]

async def generate_audio_files(turns, run_dir):
    audio_dir = run_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_list = []
    for i, turn in enumerate(turns):
        mp3_p = audio_dir / f"turn_{i:03d}.mp3"
        spoken = re.sub(r'\*\*(.*?)\*\*', r'\1', turn["text"])
        voice = EMMA_VOICE if turn["speaker"] == "Host1" else ANDREW_VOICE
        comm = edge_tts.Communicate(spoken, voice, rate=VOICE_RATE)
        await comm.save(str(mp3_p))

        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(mp3_p)],
                capture_output=True, text=True, check=True
            )
            duration = float(r.stdout.strip())
        except:
            duration = 5.0
        audio_list.append({"path": str(mp3_p), "duration": duration, "speaker": turn["speaker"]})
    return audio_list

def draw_broadcast_mic(draw, center_x, center_y, is_active, host_label):
    # Stand plate
    border_c = GOLD_ACCENT if is_active else (50, 70, 110)
    draw.ellipse([(center_x - 65, center_y + 110), (center_x + 65, center_y + 130)], fill=(20, 30, 55), outline=border_c, width=3)
    # Pole
    draw.rectangle([(center_x - 7, center_y - 10), (center_x + 7, center_y + 115)], fill=(45, 60, 95))

    # Tally Light Ring
    tally_c = (239, 68, 68) if is_active else (60, 20, 25)
    draw.rounded_rectangle([(center_x - 22, center_y - 20), (center_x + 22, center_y - 8)], radius=4, fill=tally_c)

    # Condenser Capsule
    capsule_c = (25, 40, 75) if not is_active else (40, 65, 120)
    draw.rounded_rectangle([(center_x - 30, center_y - 95), (center_x + 30, center_y - 20)], radius=16, fill=capsule_c, outline=GOLD_ACCENT if is_active else (60, 85, 130), width=3)

    # Grille lines
    for gy in range(center_y - 85, center_y - 30, 9):
        draw.line([(center_x - 22, gy), (center_x + 22, gy)], fill=ELECTRIC_BLUE if is_active else (50, 70, 105), width=2)

    # Host Badge
    f_p = load_font(22, bold=True)
    box_c = ROYAL_BLUE if is_active else (20, 30, 55)
    draw.rounded_rectangle([(center_x - 85, center_y + 145), (center_x + 85, center_y + 180)], radius=8, fill=box_c, outline=GOLD_ACCENT, width=2)
    tag = f"🎙️ {host_label}" + (" (LIVE)" if is_active else "")
    draw.text((center_x, center_y + 162), tag, fill=WHITE if is_active else MUTED_TEXT, font=f_p, anchor="mm")

def draw_broadcast_equalizer(draw, center_x, center_y, width, height, sub_idx, is_speaking):
    num_bars = 24
    bar_w = 9
    gap = (width - (num_bars * bar_w)) // (num_bars - 1)

    draw.rounded_rectangle([(center_x - width//2 - 18, center_y - height//2 - 12),
                            (center_x + width//2 + 18, center_y + height//2 + 12)],
                           radius=16, fill=(12, 20, 42), outline=ROYAL_BLUE, width=2)

    f_hud = load_font(18, bold=True)
    draw.text((center_x, center_y - height//2 - 1), "• STUDIO BROADCAST VU EQUALIZER •", fill=ELECTRIC_BLUE, font=f_hud, anchor="mm")

    start_x = center_x - width//2
    for b in range(num_bars):
        if is_speaking:
            phase = sub_idx * 0.9 + b * 0.44
            wave = abs(math.sin(phase)) * 0.7 + abs(math.cos(phase * 1.5)) * 0.3
            bar_h = int(12 + wave * (height - 28))
        else:
            bar_h = 8

        bx = start_x + b * (bar_w + gap)
        by = center_y + height//2 - 8 - bar_h

        # Segmented styling (peak turns gold)
        fill_c = GOLD_ACCENT if (bar_h > height * 0.6) else ELECTRIC_BLUE
        draw.rounded_rectangle([(bx, by), (bx + bar_w, center_y + height//2 - 8)], radius=3, fill=fill_c)

def render_podcast_subframe(topic_item, turn, turn_idx, sub_idx, total_subframes, elapsed, total_dur, out_path):
    canvas = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), DARK_BG)
    draw = ImageDraw.Draw(canvas)

    # Television Studio Backdrop Gradient
    for y in range(VIDEO_HEIGHT):
        ratio = y / VIDEO_HEIGHT
        r = int(10 + ratio * 12)
        g = int(16 + ratio * 20)
        b = int(36 + ratio * 32)
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(r, g, b, 255))

    # Ambient Studio Spotlights in top background
    for sx, sy, sr in [(350, 100, 160), (960, 80, 220), (1570, 100, 160)]:
        draw.ellipse([(sx - sr, sy - sr), (sx + sr, sy + sr)], fill=(20, 45, 95, 90))

    # Top Header Deck
    # Left: Channel badge
    draw.rounded_rectangle([(60, 36), (560, 106)], radius=16, fill=CARD_BG, outline=ROYAL_BLUE, width=2)
    f_brand = load_font(28, bold=True)
    draw.text((310, 71), "🏆 QUIZ MASTERCLASS", fill=WHITE, font=f_brand, anchor="mm")

    # Center: Challenge Topic
    draw.rounded_rectangle([(590, 36), (1450, 106)], radius=16, fill=(18, 32, 65), outline=GOLD_ACCENT, width=2)
    f_scen = load_font(26, bold=True)
    draw.text((1020, 71), f"⚡ CHALLENGE: {topic_item['sub']}", fill=GOLD_ACCENT, font=f_scen, anchor="mm")

    # Right: Live Game Show Pill
    draw.rounded_rectangle([(1480, 36), (1860, 106)], radius=16, fill=(45, 18, 24), outline=(239, 68, 68), width=3)
    f_air = load_font(26, bold=True)
    dot_color = (239, 68, 68) if (sub_idx % 2 == 0) else (120, 20, 30)
    draw.ellipse([(1515, 61), (1535, 81)], fill=dot_color)
    draw.text((1685, 71), "INTERACTIVE QUIZ", fill=WHITE, font=f_air, anchor="mm")

    # Visual Studio Centerpiece: Broadcast Stage with Interactive Quiz Card & VU Equalizer
    is_emma = (turn["speaker"] == "Host1")
    is_andrew = not is_emma

    # Left Mic: Emma
    draw_broadcast_mic(draw, center_x=320, center_y=370, is_active=is_emma, host_label="EMMA")

    # Center Screen: Digital Holographic Quiz Stage Card
    draw.rounded_rectangle([(520, 160), (1400, 370)], radius=20, fill=(18, 30, 60), outline=ELECTRIC_BLUE, width=3)
    f_qtitle = load_font(22, bold=True)
    draw.text((960, 195), "🎯 LISTEN & SOLVE THE CHALLENGE:", fill=MUTED_TEXT, font=f_qtitle, anchor="mm")

    # The actual Quiz Question
    f_q = load_font(38, bold=True)
    draw.text((960, 255), f"\"{topic_item['question']}\"", fill=GOLD_ACCENT, font=f_q, anchor="mm")

    # Option Badges: Option A vs Option B
    draw.rounded_rectangle([(550, 310), (940, 355)], radius=10, fill=(20, 65, 45), outline=CORRECT_GREEN, width=2)
    f_opt = load_font(22, bold=True)
    draw.text((745, 332), topic_item.get("opt_a", "A) has been"), fill=WHITE, font=f_opt, anchor="mm")

    draw.rounded_rectangle([(980, 310), (1370, 355)], radius=10, fill=(25, 35, 60), outline=CARD_BORDER, width=2)
    draw.text((1175, 332), topic_item.get("opt_b", "B) was"), fill=MUTED_TEXT, font=f_opt, anchor="mm")

    # Center Equalizer Deck (Below the Quiz Screen)
    draw_broadcast_equalizer(draw, center_x=960, center_y=490, width=540, height=130, sub_idx=sub_idx, is_speaking=True)

    # Right Mic: Andrew
    draw_broadcast_mic(draw, center_x=1600, center_y=370, is_active=is_andrew, host_label="ANDREW")

    # LOWER THIRD: SLEEK SINGLE-LINE SUBTITLE DISPLAY WITH WORD-BY-WORD HIGHLIGHTING
    draw.rounded_rectangle([(100, 680), (1820, 930)], radius=24, fill=(14, 22, 45, 240), outline=ROYAL_BLUE, width=3)

    # Speaker Tag Pill
    active_name = "EMMA (Host)" if is_emma else "ANDREW (Host)"
    draw.rounded_rectangle([(140, 650), (450, 705)], radius=12, fill=ROYAL_BLUE)
    f_spk = load_font(26, bold=True)
    draw.text((295, 677), f"🎙️ {active_name}", fill=WHITE, font=f_spk, anchor="mm")

    # Sentence & Spoken Word Highlighting
    raw_text = turn["text"]
    words_clean = [re.sub(r'[\*\*\.]', '', w).strip() for w in raw_text.split() if w.strip()]
    if not words_clean:
        words_clean = ["Listen", "carefully"]

    active_word_idx = min(len(words_clean) - 1, int((sub_idx / max(1, total_subframes)) * len(words_clean)))

    f_sub = load_font(42, bold=True)
    rendered_words = raw_text.split()

    line_words = []
    lines = []
    max_w = 1600
    curr_w = 0

    for w_i, w in enumerate(rendered_words):
        clean_w = re.sub(r'\*\*(.*?)\*\*', r'\1', w)
        wb = draw.textbbox((0, 0), clean_w + " ", font=f_sub)
        w_len = wb[2] - wb[0]
        if curr_w + w_len > max_w and line_words:
            lines.append(line_words)
            line_words = [(w_i, w, clean_w, w_len)]
            curr_w = w_len
        else:
            line_words.append((w_i, w, clean_w, w_len))
            curr_w += w_len
    if line_words:
        lines.append(line_words)

    y_start = 740 if len(lines) == 1 else 725
    line_h = 55
    for l_idx, line in enumerate(lines[:2]):
        total_line_w = sum(item[3] for item in line)
        start_x = 960 - total_line_w // 2
        curr_x = start_x
        y_pos = y_start + l_idx * line_h

        for (w_i, raw_w, clean_w, w_len) in line:
            is_active_word = (w_i == active_word_idx)
            is_key_word = ("**" in raw_w)

            if is_active_word:
                # Golden active karaoke pill
                draw.rounded_rectangle([(curr_x - 4, y_pos - 6), (curr_x + w_len - 2, y_pos + 46)], radius=8, fill=GOLD_ACCENT)
                draw.text((curr_x, y_pos), clean_w, fill=(10, 16, 32), font=f_sub)
            elif is_key_word:
                draw.text((curr_x, y_pos), clean_w, fill=ELECTRIC_BLUE, font=f_sub)
            else:
                draw.text((curr_x, y_pos), clean_w, fill=WHITE, font=f_sub)
            curr_x += w_len

    # Tip Ribbon inside the Lower Third
    f_tip = load_font(22, bold=False)
    draw.text((960, 885), "💡 Quiz Strategy: Notice time expressions (three times, never, already) to choose the right tense!", fill=MUTED_TEXT, font=f_tip, anchor="mm")

    # Bottom Progress Deck
    draw.line([(0, 1020), (VIDEO_WIDTH, 1020)], fill=(30, 48, 85), width=3)
    ratio = min(1.0, elapsed / max(1.0, total_dur))
    draw.line([(0, 1020), (int(VIDEO_WIDTH * ratio), 1020)], fill=GOLD_ACCENT, width=6)

    f_bot = load_font(24, bold=False)
    draw.text((70, 1050), "English Quiz Masterclass • Grammar In Use • Test Your English", fill=MUTED_TEXT, font=f_bot, anchor="lm")
    time_str = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d} / {int(total_dur // 60):02d}:{int(total_dur % 60):02d}"
    draw.text((1850, 1050), time_str, fill=GOLD_ACCENT, font=f_bot, anchor="rm")

    canvas.convert("RGB").save(out_path, quality=90)

def assemble_video(topic_item, turns, audio_list, run_dir):
    frames_dir = run_dir / "frames"
    clips_dir = run_dir / "clips"
    frames_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)

    total_dur = sum(a["duration"] for a in audio_list)
    elapsed = 0.0
    clips = []

    for i, (turn, audio) in enumerate(zip(turns, audio_list)):
        dur = audio["duration"]
        subframes_count = max(8, int(dur * SUBFRAMES_PER_SEC))

        turn_frames_dir = frames_dir / f"turn_{i:03d}"
        turn_frames_dir.mkdir(parents=True, exist_ok=True)

        for s_idx in range(subframes_count):
            frame_p = turn_frames_dir / f"frame_{s_idx:04d}.png"
            sub_elapsed = elapsed + (s_idx / subframes_count) * dur
            render_podcast_subframe(
                topic_item, turn, i, s_idx, subframes_count,
                sub_elapsed, total_dur, str(frame_p)
            )

        clip_p = clips_dir / f"clip_{i:03d}.mp4"
        input_pattern = str(turn_frames_dir / "frame_%04d.png")

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(SUBFRAMES_PER_SEC),
            "-i", input_pattern,
            "-i", audio["path"],
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-preset", "veryfast",
            str(clip_p)
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        clips.append(clip_p)
        elapsed += dur

    concat_txt = run_dir / "concat.txt"
    with open(concat_txt, "w") as f:
        for c in clips:
            f.write(f"file '{c.resolve().as_posix()}'\n")

    final_video = run_dir / "quiz_masterclass_podcast_final.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(final_video)], check=True, capture_output=True)
    return final_video, total_dur

async def run_quiz_generation(topic_idx=0, turns_count=4):
    topic_item = TOPICS[topic_idx % len(TOPICS)]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUTPUT_DIR / f"run_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"[Quiz Podcast] Generating 16:9 Broadcast Stage: '{topic_item['topic']}' ({turns_count} turns)...")
    turns = generate_script_ai(topic_item, target_turns=turns_count)
    audio_list = await generate_audio_files(turns, run_dir)
    video_p, dur = assemble_video(topic_item, turns, audio_list, run_dir)

    meta = {
        "title": f"English Quiz Challenge: {topic_item['topic']} 🎙️ Slow English Podcast",
        "description": f"Test your grammar with our interactive quiz! Can you solve: '{topic_item['question']}'? Watch and learn with Emma & Andrew! 🏆🎯",
        "question": topic_item["question"],
        "duration_seconds": dur
    }
    with open(run_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"[Quiz Podcast] Video ready: {video_p}")
    return video_p, meta

if __name__ == "__main__":
    asyncio.run(run_quiz_generation(topic_idx=0, turns_count=2))
