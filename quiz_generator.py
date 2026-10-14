"""
ENGLISH QUIZ MASTERCLASS PODCAST - 16:9 FULL HD (1920x1080)
Format: 1920x1080 Landscape Studio Broadcast
Features:
- Photorealistic quiz studio setting: Elena on the left, Marcus on the right
- Professional adult neural voices (Elena: en-US-MichelleNeural & Marcus: en-US-ChristopherNeural)
- Dynamic host badges with live speaker indicator (Elena vs Marcus)
- SentenceBoundary frame-synchronized subtitles with active gold word karaoke
- Physically reactive 16-band audio equalizer responsive to speech acoustics
- Permanent bottom branding ribbon with smooth progress line
"""
import os, sys, json, math, subprocess, random, requests, re, asyncio
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from dotenv import load_dotenv
import edge_tts
import numpy as np
from pydub import AudioSegment

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

# Color Palette
GOLD_ACCENT = (255, 215, 0)         # Radiant Gold (#FFD700)
WHITE = (255, 255, 255)
MUTED_WHITE = (210, 218, 230)
DARK_BAR_ACTIVE = (16, 20, 32, 235)
DARK_BAR_INACTIVE = (12, 16, 24, 170)
BORDER_INACTIVE = (60, 75, 95, 160)
MUTED_TEXT = (160, 175, 195)
LIVE_GREEN = (34, 197, 94)
MUTED_GOLD = (235, 225, 200)

CHANNEL_NAME = "ENGLISH QUIZ MASTERCLASS"
TAGLINE = "Test Your Grammar  •  Avoid Common Traps  •  Daily Quiz Podcast"

# Two Adult Hosts Configuration
ELENA_VOICE = "en-US-MichelleNeural"       # Articulate, engaging female host
MARCUS_VOICE = "en-US-ChristopherNeural"  # Clear, authoritative male co-host
VOICE_RATE = "-10%"

TOPICS = [
    {
        "topic": "Present Perfect vs Simple Past: Have You Ever or Did You Ever?",
        "question": "She ________ to Paris three times in her life.",
        "correct": "has been",
        "turns": [
            {"speaker": "Host1", "text": "Welcome to the English Quiz Masterclass! Here is today's challenge: She has been, or she was to **Paris**?"},
            {"speaker": "Host2", "text": "Take five seconds to think. Are we talking about a specific past moment, or overall life **experience**?"},
            {"speaker": "Host1", "text": "The correct answer is: She has been to Paris! We use present perfect for experiences up to **now**."},
            {"speaker": "Host2", "text": "Never say she was to Paris. Well done if you solved that correctly, and keep **practicing**!"}
        ]
    },
    {
        "topic": "Look Forward To: Infinitive or Gerund Trap?",
        "question": "I look forward to ________ you tomorrow.",
        "correct": "seeing",
        "turns": [
            {"speaker": "Host1", "text": "Welcome back! Today's quiz question trips up even advanced learners: look forward to see, or look forward to **seeing**?"},
            {"speaker": "Host2", "text": "Notice the word to. Is it part of the infinitive, or is it a **preposition**?"},
            {"speaker": "Host1", "text": "Here, to is a preposition! That means it must be followed by a gerund: I look forward to **seeing** you."},
            {"speaker": "Host2", "text": "Always write I look forward to hearing from you or seeing you. Never use the base **verb**!"}
        ]
    },
    {
        "topic": "Time Prepositions: In, On, or At?",
        "question": "The team meeting begins ________ nine o'clock on Monday.",
        "correct": "at",
        "turns": [
            {"speaker": "Host1", "text": "Ready for a rapid-fire preposition check? Should you say at nine o'clock, on nine o'clock, or in nine **o'clock**?"},
            {"speaker": "Host2", "text": "Think about our rule for exact clock times versus general days and **months**."},
            {"speaker": "Host1", "text": "We always use at for specific clock times! So the meeting starts at nine **o'clock**."},
            {"speaker": "Host2", "text": "Remember: at for precise times, on for calendar days, and in for months and **years**!"}
        ]
    }
]


def configure_edge_tts():
    """Ensure edge_tts connects to Microsoft's active Cognitive Services endpoint to avoid 403 Forbidden."""
    try:
        import edge_tts.constants
        import edge_tts.communicate
        token = getattr(edge_tts.constants, "TRUSTED_CLIENT_TOKEN", "6A5AA1D4EAFF4E9FB37E23D68491D6F4")
        new_url = (
            "wss://api.msedgeservices.com/tts/cognitiveservices/websocket/v1"
            f"?Ocp-Apim-Subscription-Key={token}"
        )
        edge_tts.constants.WSS_URL = new_url
        edge_tts.communicate.WSS_URL = new_url
    except Exception as e:
        print(f"[edge_tts] configure warning: {e}")

async def synthesize_turn_speech(spoken, voice, rate, pitch=None, max_retries=3):
    """Synthesizes speech with active endpoint, 3x self-healing retries, and gTTS fallback."""
    configure_edge_tts()
    for attempt in range(max_retries):
        try:
            kwargs = {"rate": rate}
            if pitch:
                kwargs["pitch"] = pitch
            comm = edge_tts.Communicate(spoken, voice, **kwargs)
            sentences = []
            audio_bytes = bytearray()
            async for chunk in comm.stream():
                if chunk.get("type") == "SentenceBoundary":
                    start_s = chunk["offset"] / 10_000_000.0
                    dur_s = chunk["duration"] / 10_000_000.0
                    sentences.append({
                        "text": chunk["text"],
                        "start": start_s,
                        "duration": dur_s,
                        "end": start_s + dur_s
                    })
                elif chunk.get("type") == "audio":
                    audio_bytes.extend(chunk["data"])
            
            if len(audio_bytes) > 500:
                return audio_bytes, sentences
            else:
                print(f"    [TTS] Attempt {attempt+1}: bytes too small ({len(audio_bytes)}), retrying...")
        except Exception as e:
            print(f"    [TTS] Attempt {attempt+1} error: {e}")
        await asyncio.sleep(2 * (attempt + 1))
    
    # Fallback to gTTS if Edge TTS drops out
    try:
        from gtts import gTTS
        import io
        print(f"    [TTS] Active endpoint exhausted. Using gTTS fallback...")
        tts = gTTS(text=spoken, lang="en")
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        return bytearray(buf.getvalue()), []
    except Exception as fb_err:
        print(f"    [TTS] Fallback error: {fb_err}")
        return None, []

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

def generate_script_ai(topic_item, target_turns=4):
    prompt = f"""Write {target_turns} turns of a natural, engaging English quiz podcast dialogue between Elena (female host) and Marcus (male host) discussing: {topic_item['topic']}.

RULES:
- Dialogue alternating between Host1 (Elena) and Host2 (Marcus)
- Each turn MUST be 2 short, clear sentences (16-24 words)
- Present the question, guide the listener, reveal the rule and answer
- Wrap exactly 1 key learning word per turn in **asterisks**
- Return as clean JSON array only:
[{{"speaker":"Host1","text":"..."}},{{"speaker":"Host2","text":"..."}}]"""

    key = os.getenv("POLLINATIONS_API_KEY")
    if key:
        try:
            resp = requests.post("https://gen.pollinations.ai/v1/chat/completions", json={
                "model": "gemini-fast",
                "messages": [
                    {"role": "system", "content": "You write educational, engaging English quiz podcast dialogue. Wrap 1 key word per turn in **asterisks**."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.8
            }, headers={"Authorization": f"Bearer {key}"}, timeout=20)
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

    return topic_item.get("turns", [
        {"speaker": "Host1", "text": f"Welcome to the English Quiz Masterclass! Today's challenge is about: {topic_item['topic']}."},
        {"speaker": "Host2", "text": "Listen carefully to find the correct answer and avoid the common **mistake**."},
        {"speaker": "Host1", "text": f"The correct answer is '{topic_item['correct']}', because it matches standard grammatical **structure**."},
        {"speaker": "Host2", "text": "Great job if you got that right, and keep following us for daily English **practice**!"}
    ])[:target_turns]

async def generate_audio_files(turns, run_dir):
    audio_dir = run_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    audio_list = []

    for i, turn in enumerate(turns):
        mp3_p = audio_dir / f"turn_{i:03d}.mp3"
        spoken = re.sub(r'\*\*(.*?)\*\*', r'\1', turn["text"])
        speaker = turn["speaker"]

        voice = ELENA_VOICE if speaker == "Host1" else MARCUS_VOICE
        rate = VOICE_RATE

        comm = edge_tts.Communicate(spoken, voice, rate=rate)
        boundary_events = []
        with open(mp3_p, "wb") as f_out:
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    f_out.write(chunk["data"])
                elif chunk["type"] == "SentenceBoundary":
                    offset_sec = chunk["offset"] / 10_000_000.0
                    dur_sec = chunk["duration"] / 10_000_000.0
                    boundary_events.append({
                        "text": chunk["text"],
                        "start": offset_sec,
                        "end": offset_sec + dur_sec
                    })

        try:
            r = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(mp3_p)],
                capture_output=True, text=True, check=True
            )
            duration = float(r.stdout.strip())
        except Exception:
            duration = 5.0

        timed_phrases = []
        if boundary_events:
            for b in boundary_events:
                txt = clean_text(b["text"])
                if not txt: continue
                words = txt.split()
                if len(words) > 8:
                    mid = len(words) // 2
                    p1_text = " ".join(words[:mid])
                    p2_text = " ".join(words[mid:])
                    t_mid = b["start"] + (b["end"] - b["start"]) * (len(words[:mid]) / len(words))
                    timed_phrases.append({"text": p1_text, "start": b["start"], "end": t_mid})
                    timed_phrases.append({"text": p2_text, "start": t_mid, "end": b["end"]})
                else:
                    timed_phrases.append({"text": txt, "start": b["start"], "end": b["end"]})
        else:
            raw_sents = [s.strip() for s in re.split(r'([.?!])', spoken) if s.strip()]
            sents = []
            for j in range(0, len(raw_sents), 2):
                if j+1 < len(raw_sents): sents.append(raw_sents[j] + raw_sents[j+1])
                else: sents.append(raw_sents[j])
            sents = [s for s in sents if len(s.split()) >= 2] or [spoken]

            tot_words = sum(len(s.split()) for s in sents)
            t_curr = 0.0
            for s in sents:
                w_count = len(s.split())
                s_dur = duration * (w_count / max(1, tot_words))
                words = s.split()
                if len(words) > 8:
                    mid = len(words) // 2
                    p1_text = " ".join(words[:mid])
                    p2_text = " ".join(words[mid:])
                    t_mid = t_curr + s_dur * 0.5
                    timed_phrases.append({"text": p1_text, "start": t_curr, "end": t_mid})
                    timed_phrases.append({"text": p2_text, "start": t_mid, "end": t_curr + s_dur})
                else:
                    timed_phrases.append({"text": s, "start": t_curr, "end": t_curr + s_dur})
                t_curr += s_dur

        seg = AudioSegment.from_file(str(mp3_p))
        seg = seg.set_channels(1).set_frame_rate(22050)
        raw_samples = np.array(seg.get_array_of_samples(), dtype=np.float32)

        audio_list.append({
            "path": str(mp3_p),
            "duration": duration,
            "speaker": speaker,
            "timed_phrases": timed_phrases,
            "raw_samples": raw_samples,
            "sample_rate": 22050
        })

    return audio_list

def compute_physical_equalizer_bars(raw_samples, sample_rate, current_time, num_bars=16):
    if raw_samples is None or len(raw_samples) == 0:
        return [4] * num_bars

    center_idx = int(current_time * sample_rate)
    window_size = int(0.060 * sample_rate)
    half = window_size // 2

    start_idx = max(0, center_idx - half)
    end_idx = min(len(raw_samples), center_idx + half)

    if end_idx - start_idx < 64:
        return [4] * num_bars

    chunk = raw_samples[start_idx:end_idx]
    rms = np.sqrt(np.mean(chunk**2))
    if rms < 350.0:
        return [4] * num_bars

    window = np.hanning(len(chunk))
    fft_vals = np.abs(np.fft.rfft(chunk * window))
    freqs = np.fft.rfftfreq(len(chunk), d=1.0/sample_rate)

    min_freq = 100.0
    max_freq = 6000.0
    edges = np.geomspace(min_freq, max_freq, num_bars + 1)

    bar_heights = []
    for b in range(num_bars):
        f_low = edges[b]
        f_high = edges[b+1]
        idx = np.where((freqs >= f_low) & (freqs < f_high))[0]
        if len(idx) > 0:
            val = float(np.mean(fft_vals[idx]))
        else:
            val = 0.0

        norm = math.log10(1.0 + val / 1500.0) / 2.2
        norm = max(0.0, min(1.0, norm))

        h = int(6 + norm * 42)
        h = max(4, min(48, h))
        bar_heights.append(h)

    return bar_heights

def load_base_studio_canvas():
    studio_path = ASSETS_DIR / "quiz_studio.png"
    if studio_path.exists():
        img = Image.open(studio_path).convert("RGBA")
        return img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.Resampling.LANCZOS)
    fallback_path = ASSETS_DIR / "two_hosts_studio.png"
    if fallback_path.exists():
        img = Image.open(fallback_path).convert("RGBA")
        return img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (15, 20, 32, 255))
    return canvas

def render_podcast_frame(base_canvas, speaker, phrase_text, active_w_idx, eq_bars, frame_idx, elapsed, total_dur, out_path):
    canvas = base_canvas.copy()
    draw = ImageDraw.Draw(canvas)

    f_pill = load_font(28, bold=True)
    is_host1 = (speaker == "Host1")

    # 1. Left Host Pill (HOST: ELENA)
    h1_bg = DARK_BAR_ACTIVE if is_host1 else DARK_BAR_INACTIVE
    h1_border = GOLD_ACCENT if is_host1 else BORDER_INACTIVE
    h1_text_col = GOLD_ACCENT if is_host1 else MUTED_TEXT
    h1_border_w = 3 if is_host1 else 2
    draw.rounded_rectangle([(60, 45), (430, 115)], radius=18, fill=h1_bg, outline=h1_border, width=h1_border_w)

    if is_host1:
        pulse_r = 7 + int(2 * math.sin(frame_idx * 0.4))
        draw.ellipse([(88 - pulse_r, 80 - pulse_r), (88 + pulse_r, 80 + pulse_r)], fill=LIVE_GREEN)
    else:
        draw.ellipse([(82, 74), (94, 86)], fill=(90, 105, 125))
    draw.text((115, 80), "HOST: ELENA", fill=h1_text_col, font=f_pill, anchor="lm")

    # 2. Right Host Pill (HOST: MARCUS)
    h2_bg = DARK_BAR_ACTIVE if not is_host1 else DARK_BAR_INACTIVE
    h2_border = GOLD_ACCENT if not is_host1 else BORDER_INACTIVE
    h2_text_col = GOLD_ACCENT if not is_host1 else MUTED_TEXT
    h2_border_w = 3 if not is_host1 else 2
    draw.rounded_rectangle([(1490, 45), (1860, 115)], radius=18, fill=h2_bg, outline=h2_border, width=h2_border_w)

    if not is_host1:
        pulse_r = 7 + int(2 * math.sin(frame_idx * 0.4))
        draw.ellipse([(1518 - pulse_r, 80 - pulse_r), (1518 + pulse_r, 80 + pulse_r)], fill=LIVE_GREEN)
    else:
        draw.ellipse([(1512, 74), (1524, 86)], fill=(90, 105, 125))
    draw.text((1545, 80), "HOST: MARCUS", fill=h2_text_col, font=f_pill, anchor="lm")

    # 3. Top Center Episode Pill
    draw.rounded_rectangle([(700, 48), (1220, 112)], radius=16, fill=(10, 14, 24, 210), outline=(80, 100, 130, 180), width=2)
    f_cat = load_font(24, bold=True)
    draw.text((960, 80), "QUIZ CHALLENGE", fill=GOLD_ACCENT, font=f_cat, anchor="mm")

    # 4. Large Subtitles in Safe Center Screen
    raw_words = phrase_text.split()
    f_sub = load_font(68, bold=True)
    max_w = 880

    lines = []
    cur_line = []
    cur_w = 0
    for w_i, raw_w in enumerate(raw_words):
        clean_w = re.sub(r'[\*\*\.]', '', raw_w).strip()
        if not clean_w: continue
        wb = draw.textbbox((0, 0), clean_w + " ", font=f_sub)
        wl = wb[2] - wb[0]
        if cur_w + wl > max_w and cur_line:
            lines.append(cur_line)
            cur_line = [(w_i, clean_w, wl)]
            cur_w = wl
        else:
            cur_line.append((w_i, clean_w, wl))
            cur_w += wl
    if cur_line:
        lines.append(cur_line)

    line_h = 100
    total_h = len(lines) * line_h
    center_x = 960
    center_y = 330
    start_y = max(180, center_y - total_h // 2)

    # Dark background glow
    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    glow_w = max(sum(item[2] for item in l) for l in lines) + 140
    glow_h = total_h + 90
    gdraw.rounded_rectangle([
        (center_x - glow_w // 2, start_y + total_h // 2 - glow_h // 2),
        (center_x + glow_w // 2, start_y + total_h // 2 + glow_h // 2)
    ], radius=30, fill=(0, 0, 0, 160))
    glow = glow.filter(ImageFilter.GaussianBlur(25))
    canvas.paste(glow, (0, 0), glow)

    # Deep drop shadow
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    for l_i, line in enumerate(lines):
        lw = sum(item[2] for item in line)
        lx = center_x - lw // 2
        ly = start_y + l_i * line_h
        for (w_i, clean_w, wl) in line:
            sdraw.text((lx + 4, ly + 5), clean_w, fill=(0, 0, 0, 255), font=f_sub)
            lx += wl
    shadow = shadow.filter(ImageFilter.GaussianBlur(5))
    canvas.paste(shadow, (0, 0), shadow)

    # Foreground text with active spoken word highlighted in Gold (#FFD700)
    draw = ImageDraw.Draw(canvas)
    for l_i, line in enumerate(lines):
        lw = sum(item[2] for item in line)
        lx = center_x - lw // 2
        ly = start_y + l_i * line_h
        for (w_i, clean_w, wl) in line:
            is_active = (w_i == active_w_idx)
            col = GOLD_ACCENT if is_active else WHITE
            draw.text((lx, ly), clean_w, fill=col, font=f_sub)
            lx += wl

    # 5. Physically Synchronized Sound Equalizer Plate in the Center
    # Generous breathing gap below subtitle text (center_y = 585)
    eq_cx = 960
    eq_cy = 585
    eq_w = 440
    eq_h = 58
    draw.rounded_rectangle([
        (eq_cx - eq_w // 2, eq_cy - eq_h // 2),
        (eq_cx + eq_w // 2, eq_cy + eq_h // 2)
    ], radius=16, fill=(14, 18, 28, 220), outline=(255, 215, 0, 180), width=2)

    num_b = 16
    bw = 12
    gap = 12
    total_bars_w = num_b * bw + (num_b - 1) * gap
    start_bx = eq_cx - total_bars_w // 2

    for b_i in range(num_b):
        bh = eq_bars[b_i] if b_i < len(eq_bars) else 4
        bx = start_bx + b_i * (bw + gap)
        by_top = eq_cy - bh // 2
        by_bot = eq_cy + bh // 2
        draw.rounded_rectangle([(bx, by_top), (bx + bw, by_bot)], radius=6, fill=GOLD_ACCENT)

    # 6. Fixed Bottom Footer Ribbon (Permanent, NO jumping text, NO timers)
    draw.line([(0, 1025), (VIDEO_WIDTH, 1025)], fill=(45, 52, 72), width=2)
    ratio = min(1.0, elapsed / max(1.0, total_dur))
    draw.line([(0, 1025), (int(VIDEO_WIDTH * ratio), 1025)], fill=GOLD_ACCENT, width=4)

    f_foot = load_font(28, bold=False)
    draw.text((center_x, 1052), TAGLINE, fill=MUTED_GOLD, font=f_foot, anchor="mm")

    canvas.convert("RGB").save(out_path, quality=95)

def assemble_video(topic_item, turns, audio_list, run_dir):
    frames_dir = run_dir / "frames"
    clips_dir = run_dir / "clips"
    frames_dir.mkdir(parents=True, exist_ok=True)
    clips_dir.mkdir(parents=True, exist_ok=True)

    base_canvas = load_base_studio_canvas()
    total_dur = sum(a["duration"] for a in audio_list)
    elapsed = 0.0
    clips = []

    for i, audio in enumerate(audio_list):
        dur = audio["duration"]
        speaker = audio["speaker"]
        timed_phrases = audio["timed_phrases"]
        raw_samples = audio["raw_samples"]
        sample_rate = audio["sample_rate"]

        turn_frames_dir = frames_dir / f"turn_{i:03d}"
        turn_frames_dir.mkdir(parents=True, exist_ok=True)

        fps_turn = 10
        total_turn_frames = max(1, int(dur * fps_turn))

        for f_idx in range(total_turn_frames):
            frame_p = turn_frames_dir / f"frame_{f_idx:04d}.png"
            t_in_turn = (f_idx / total_turn_frames) * dur
            sub_elapsed = elapsed + t_in_turn

            # 1. Active phrase from Edge TTS timestamps
            active_phrase = timed_phrases[0] if timed_phrases else {"text": "Listen carefully", "start": 0, "end": dur}
            for p in timed_phrases:
                if p["start"] <= t_in_turn <= p["end"]:
                    active_phrase = p
                    break
                elif t_in_turn > p["end"]:
                    active_phrase = p

            # 2. Active word within active phrase
            p_text = active_phrase["text"]
            p_words = p_text.split()
            p_dur = max(0.2, active_phrase["end"] - active_phrase["start"])
            rel_t = max(0.0, min(p_dur, t_in_turn - active_phrase["start"]))
            active_w_idx = min(len(p_words) - 1, int((rel_t / p_dur) * len(p_words)))

            # 3. 16-band physical audio equalizer directly from real voice audio
            eq_bars = compute_physical_equalizer_bars(raw_samples, sample_rate, t_in_turn, num_bars=16)

            render_podcast_frame(
                base_canvas, speaker, p_text, active_w_idx,
                eq_bars, f_idx, sub_elapsed, total_dur, str(frame_p)
            )

        clip_p = clips_dir / f"clip_{i:03d}.mp4"
        input_pattern = str(turn_frames_dir / "frame_%04d.png")

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps_turn),
            "-i", input_pattern,
            "-i", audio["path"],
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-preset", "ultrafast",
            str(clip_p)
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        clips.append(clip_p)
        elapsed += dur

    concat_txt = run_dir / "concat.txt"
    with open(concat_txt, "w") as f:
        for c in clips:
            f.write(f"file '{c.resolve().as_posix()}'\n")

    final_video = run_dir / "quiz_podcast_final.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_txt),
        "-c", "copy",
        str(final_video)
    ], check=True, capture_output=True)

    return final_video, total_dur

async def run_quiz_generation(topic_idx=0, turns_count=4):
    topic_item = TOPICS[topic_idx % len(TOPICS)]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUTPUT_DIR / f"run_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"[English Quiz Masterclass] Generating 16:9 Broadcast: '{topic_item['topic']}' ({turns_count} turns)...")
    turns = generate_script_ai(topic_item, target_turns=turns_count)
    audio_list = await generate_audio_files(turns, run_dir)
    video_p, dur = assemble_video(topic_item, turns, audio_list, run_dir)

    meta = {
        "title": f"English Quiz Masterclass: {topic_item['topic']} 🎙️ Elena & Marcus",
        "description": f"Test your English grammar! Today: '{topic_item['topic']}'. Follow for daily interactive quiz masterclasses! 🏆✨",
        "topic": topic_item["topic"],
        "duration_seconds": dur
    }
    with open(run_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"[English Quiz Masterclass] Video ready: {video_p}")
    return video_p, meta

if __name__ == "__main__":
    asyncio.run(run_quiz_generation(topic_idx=0, turns_count=4))
