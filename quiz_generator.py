"""
ENGLISH QUIZ MASTERCLASS PODCAST - 16:9 FULL HD (1920x1080)
Format: 1920x1080 Landscape Studio Broadcast (Directly inspired by velocitykorean/fl-eng-std)
Features:
- Studio Host Setting on the left with royal broadcast cobalt grading
- Minimalist, elegant top pills (NO clutter, NO extra boxes)
- HUGE high-contrast subtitle typography with word-by-word karaoke highlighting
- REALISTIC audio equalizer at the bottom reacting directly to actual voice frequencies
- Real-time elapsed timeline progress bar
"""
import os, sys, json, math, subprocess, random, requests, re, asyncio
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
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
FPS = 30

# Colors
GOLD_ACCENT = (250, 204, 21)         # Vivid Gold (#FACC15)
WHITE = (255, 255, 255)
MUTED_WHITE = (220, 225, 235)
DARK_BAR = (16, 24, 45)
EQ_BG = (12, 18, 36, 215)
EQ_BORDER = (45, 65, 105)

CHANNEL_NAME = "ENGLISH QUIZ MASTERCLASS"
EQ_COLORS_FFMPEG = "0xFACC15|0x3B82F6"

EMMA_VOICE = "en-US-AvaNeural"
ANDREW_VOICE = "en-US-AndrewNeural"
VOICE_RATE = "-15%"

TOPICS = [
    {
        "topic": "Can You Pass This Present Perfect Grammar Test?",
        "question": "She ________ to Paris three times.",
        "correct": "has been",
        "keyword": "EXPERIENCE",
        "sub": "PRESENT PERFECT VS SIMPLE PAST"
    },
    {
        "topic": "Gerund or Infinitive? Look Forward To Challenge",
        "question": "I look forward to ________ you tomorrow.",
        "correct": "seeing",
        "keyword": "GERUND",
        "sub": "PHRASAL VERB PREPOSITIONS"
    },
    {
        "topic": "Tricky Prepositions: In, On, or At Time Challenge",
        "question": "The concert begins ________ seven PM.",
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
    prompt = f"""Write {target_turns} turns of a slow, clear English podcast between Emma and Andrew discussing: {topic_item['topic']}.

RULES:
- Dialogue alternating between Host1 (Emma) and Host2 (Andrew)
- Each turn MUST be 2-3 short, clear sentences (18-28 words)
- Present the challenge question, discuss common errors, and explain the correct grammar rule clearly
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

def load_base_studio_canvas():
    woman_path = ASSETS_DIR / "woman_base.png"
    if woman_path.exists():
        img = Image.open(woman_path).convert("RGB")
        # Royal broadcast cobalt & gold studio grade
        r, g, b = img.split()
        b = b.point(lambda i: min(255, int(i * 1.16)))
        g = g.point(lambda i: min(255, int(i * 1.02)))
        r = r.point(lambda i: int(i * 0.94))
        graded = Image.merge("RGB", (r, g, b))
        graded = ImageEnhance.Contrast(graded).enhance(1.08)
        return graded.convert("RGBA").resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.Resampling.LANCZOS)
    else:
        canvas = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (12, 18, 36, 255))
        return canvas

def render_podcast_frame(base_canvas, turn, s_idx, total_subframes, elapsed, total_dur, out_path):
    canvas = base_canvas.copy()
    draw = ImageDraw.Draw(canvas)

    # 1. Clean Top Left Pill (NO clutter)
    font_tab = load_font(30, bold=True)
    draw.rounded_rectangle([(60, 40), (580, 105)], radius=18, fill=DARK_BAR, outline=GOLD_ACCENT, width=3)
    # Wave icon
    for b in range(6):
        bh = int(12 + 10 * abs(math.sin(s_idx * 0.5 + b * 1.2)))
        bx = 90 + b * 12
        draw.line([(bx, 72 - bh//2), (bx, 72 + bh//2)], fill=GOLD_ACCENT, width=3)
    draw.text((180, 72), CHANNEL_NAME, fill=WHITE, font=font_tab, anchor="lm")

    # 2. Clean Top Right Speaker Pill
    speaker_name = "EMMA" if turn["speaker"] == "Host1" else "ANDREW"
    font_spk = load_font(30, bold=True)
    draw.rounded_rectangle([(1520, 40), (1880, 105)], radius=18, fill=DARK_BAR, outline=GOLD_ACCENT, width=3)
    # Vector microphone icon
    draw.rounded_rectangle([(1555, 62), (1567, 78)], radius=4, fill=GOLD_ACCENT)
    draw.arc([(1551, 70), (1571, 84)], start=0, end=180, fill=GOLD_ACCENT, width=3)
    draw.line([(1561, 84), (1561, 90)], fill=GOLD_ACCENT, width=3)
    draw.line([(1555, 90), (1567, 90)], fill=GOLD_ACCENT, width=3)
    draw.text((1585, 72), f"HOST: {speaker_name}", fill=GOLD_ACCENT, font=font_spk, anchor="lm")

    # 3. Huge Subtitle Typography in Safe Zone (x: 800 to 1800)
    raw_text = turn["text"]
    words_raw = raw_text.split()
    clean_words = [re.sub(r'[\*\*\.]', '', w).strip() for w in words_raw if w.strip()]
    if not clean_words: clean_words = ["Listen", "carefully"]

    active_idx = min(len(clean_words) - 1, int((s_idx / max(1, total_subframes)) * len(clean_words)))

    font_main = load_font(78, bold=True)
    max_w = 980
    lines = []
    curr_line = []
    curr_w = 0

    for w_i, raw_w in enumerate(words_raw):
        clean_w = re.sub(r'\*\*(.*?)\*\*', r'\1', raw_w)
        wb = draw.textbbox((0, 0), clean_w + " ", font=font_main)
        wl = wb[2] - wb[0]
        if curr_w + wl > max_w and curr_line:
            lines.append(curr_line)
            curr_line = [(w_i, clean_w, wl)]
            curr_w = wl
        else:
            curr_line.append((w_i, clean_w, wl))
            curr_w += wl
    if curr_line:
        lines.append(curr_line)

    line_h = 108
    total_h = len(lines) * line_h
    start_y = 500 - total_h // 2
    text_center_x = 1320

    # Gaussian blur drop shadow
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    for l_idx, line in enumerate(lines):
        lw = sum(item[2] for item in line)
        lx = text_center_x - lw // 2
        ly = start_y + l_idx * line_h
        for (w_i, clean_w, wl) in line:
            sdraw.text((lx + 4, ly + 4), clean_w, fill=(0, 0, 0, 240), font=font_main)
            lx += wl
    shadow = shadow.filter(ImageFilter.GaussianBlur(5))
    canvas.paste(shadow, (0, 0), shadow)

    # Foreground text with active spoken word highlighted in Gold
    draw = ImageDraw.Draw(canvas)
    for l_idx, line in enumerate(lines):
        lw = sum(item[2] for item in line)
        lx = text_center_x - lw // 2
        ly = start_y + l_idx * line_h
        for (w_i, clean_w, wl) in line:
            is_active = (w_i == active_idx)
            col = GOLD_ACCENT if is_active else WHITE
            draw.text((lx, ly), clean_w, fill=col, font=font_main)
            lx += wl

    # 4. Realistic Sound Equalizer Plate at the Bottom Right
    draw.rounded_rectangle([(840, 885), (1800, 965)], radius=14, fill=EQ_BG, outline=EQ_BORDER, width=2)
    f_eq_lbl = load_font(18, bold=True)
    draw.text((865, 925), "AUDIO SPECTRUM", fill=(190, 205, 235), font=f_eq_lbl, anchor="lm")

    # 5. Bottom Timeline & Progress Bar
    draw.line([(0, 1025), (VIDEO_WIDTH, 1025)], fill=(35, 50, 80), width=2)
    ratio = min(1.0, elapsed / max(1.0, total_dur))
    draw.line([(0, 1025), (int(VIDEO_WIDTH * ratio), 1025)], fill=GOLD_ACCENT, width=5)

    f_bot = load_font(26, bold=False)
    draw.text((70, 1052), "English Quiz Masterclass • Test & Elevate Your English", fill=MUTED_WHITE, font=f_bot, anchor="lm")
    time_str = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d} / {int(total_dur // 60):02d}:{int(total_dur % 60):02d}"
    draw.text((1850, 1052), time_str, fill=GOLD_ACCENT, font=f_bot, anchor="rm")

    canvas.convert("RGB").save(out_path, quality=92)

def assemble_video(topic_item, turns, audio_list, run_dir):
    frames_dir = run_dir / "frames"
    clips_dir = run_dir / "clips"
    frames_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)

    base_canvas = load_base_studio_canvas()
    total_dur = sum(a["duration"] for a in audio_list)
    elapsed = 0.0
    clips = []

    for i, (turn, audio) in enumerate(zip(turns, audio_list)):
        dur = audio["duration"]
        words_count = len(turn["text"].split())
        subframes_count = max(words_count, int(dur * 2))
        fps_sub = subframes_count / dur

        turn_frames_dir = frames_dir / f"turn_{i:03d}"
        turn_frames_dir.mkdir(parents=True, exist_ok=True)

        for s in range(subframes_count):
            frame_p = turn_frames_dir / f"frame_{s:04d}.png"
            sub_elapsed = elapsed + (s / subframes_count) * dur
            render_podcast_frame(base_canvas, turn, s, subframes_count, sub_elapsed, total_dur, str(frame_p))

        clip_p = clips_dir / f"clip_{i:03d}.mp4"
        input_pattern = str(turn_frames_dir / "frame_%04d.png")

        filter_str = (
            f"[1:a]showfreqs=s=740x55:mode=bar:ascale=log:fscale=log:colors={EQ_COLORS_FFMPEG}:win_size=1024[eq];"
            f"[0:v][eq]overlay=x=1030:y=895:shortest=1[v]"
        )

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps_sub),
            "-i", input_pattern,
            "-i", audio["path"],
            "-filter_complex", filter_str,
            "-map", "[v]", "-map", "1:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-preset", "fast", "-shortest",
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

    print(f"[Quiz Podcast] Generating 16:9 Broadcast: '{topic_item['topic']}' ({turns_count} turns)...")
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

    print(f"[Quiz Podcast] Final Video ready: {video_p}")
    return video_p, meta

if __name__ == "__main__":
    asyncio.run(run_quiz_generation(topic_idx=0, turns_count=2))
