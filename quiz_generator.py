"""
Interactive English Quiz Challenge - Video Generator (9:16 Vertical Reel)
Gamified 10-second quiz with 5s countdown timer bar, animated answer reveal, and grammar explanation.
"""
import os, sys, json, subprocess, random, requests, re, asyncio
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from dotenv import load_dotenv
import edge_tts

load_dotenv()

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH = 1080
HEIGHT = 1920
FPS = 30

BG_DARK = (15, 14, 38)
NEON_YELLOW = (250, 204, 21)
NEON_CYAN = (6, 182, 212)
GREEN_SUCCESS = (16, 185, 129)
CARD_BG = (28, 26, 64)
WHITE = (255, 255, 255)

VOICE_HOST = "en-US-AvaNeural"

QUIZZES = [
    {
        "question": "She ________ to Paris three times.",
        "level": "INTERMEDIATE (B1)",
        "options": [
            ("A", "is going"),
            ("B", "has been"),
            ("C", "went")
        ],
        "correct": "B",
        "explanation": "Rule: 'Has been' is Present Perfect tense, used when describing life experiences!",
        "intro_speech": "English Quiz time! Fill in the blank: She... to Paris three times. A: is going, B: has been, or C: went? You have five seconds to think!",
        "reveal_speech": "The correct answer is B: has been! We use the present perfect for life experiences. Comment your score below and follow for daily quizzes!"
    },
    {
        "question": "I look forward to ________ you tomorrow.",
        "level": "UPPER-INTERMEDIATE (B2)",
        "options": [
            ("A", "see"),
            ("B", "seeing"),
            ("C", "saw")
        ],
        "correct": "B",
        "explanation": "Rule: 'Look forward to' is a phrasal verb followed by a gerund (-ing form)!",
        "intro_speech": "Quick English test! Fill in the blank: I look forward to... you tomorrow. A: see, B: seeing, or C: saw? Five seconds on the clock!",
        "reveal_speech": "The correct answer is B: seeing! 'Look forward to' is always followed by an ING verb. Comment if you got it right!"
    }
]

def load_font(size, bold=True):
    fonts_to_try = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in fonts_to_try:
        if Path(p).exists():
            try: return ImageFont.truetype(p, size)
            except: continue
    return ImageFont.load_default()

def render_quiz_frame(quiz, state="question", countdown_sec=5, out_path="frame.png"):
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), BG_DARK)
    draw = ImageDraw.Draw(canvas)

    # Gradient background
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(15 + ratio * 18)
        g = int(14 + ratio * 16)
        b = int(38 + ratio * 40)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b, 255))

    # Top Header Pill
    draw.rounded_rectangle([(70, 90), (WIDTH - 70, 180)], radius=22, fill=(35, 30, 80), outline=NEON_YELLOW, width=3)
    f_hdr = load_font(32, bold=True)
    draw.text((WIDTH // 2, 135), "🎯 10-SECOND ENGLISH QUIZ CHALLENGE", fill=NEON_YELLOW, font=f_hdr, anchor="mm")

    # Level Tag
    draw.rounded_rectangle([(70, 210), (WIDTH - 70, 280)], radius=18, fill=(30, 25, 65), outline=NEON_CYAN, width=2)
    f_lvl = load_font(26, bold=True)
    draw.text((WIDTH // 2, 245), f"DIFFICULTY LEVEL: {quiz['level']}", fill=NEON_CYAN, font=f_lvl, anchor="mm")

    # Question Box
    draw.rounded_rectangle([(70, 310), (WIDTH - 70, 560)], radius=30, fill=(38, 34, 88), outline=NEON_YELLOW, width=4)
    f_qlbl = load_font(28, bold=True)
    draw.text((WIDTH // 2, 355), "CAN YOU CHOOSE THE CORRECT OPTION?", fill=(220, 225, 245), font=f_qlbl, anchor="mm")

    f_qtxt = load_font(46, bold=True)
    draw.text((WIDTH // 2, 455), quiz["question"], fill=WHITE, font=f_qtxt, anchor="mm")

    # Options (A, B, C)
    opt_y = 610
    for letter, opt_text in quiz["options"]:
        is_correct = (letter == quiz["correct"])
        if state == "reveal":
            if is_correct:
                border_c = GREEN_SUCCESS
                bg_c = (20, 60, 45)
                text_c = GREEN_SUCCESS
                tag_bg = GREEN_SUCCESS
            else:
                border_c = (60, 55, 90)
                bg_c = (25, 22, 50)
                text_c = (140, 140, 165)
                tag_bg = (60, 55, 90)
        else:
            border_c = NEON_CYAN
            bg_c = CARD_BG
            text_c = WHITE
            tag_bg = (50, 45, 100)

        draw.rounded_rectangle([(70, opt_y), (WIDTH - 70, opt_y + 140)], radius=22, fill=bg_c, outline=border_c, width=3)
        draw.rounded_rectangle([(100, opt_y + 25), (200, opt_y + 115)], radius=15, fill=tag_bg)
        f_letter = load_font(42, bold=True)
        draw.text((150, opt_y + 70), letter, fill=WHITE, font=f_letter, anchor="mm")

        f_opt = load_font(42, bold=True)
        draw.text((240, opt_y + 70), opt_text, fill=text_c, font=f_opt, anchor="lm")

        if state == "reveal" and is_correct:
            draw.text((WIDTH - 120, opt_y + 70), "✅ CORRECT", fill=GREEN_SUCCESS, font=load_font(28, bold=True), anchor="rm")

        opt_y += 170

    # Countdown Bar / Status Box
    if state == "countdown":
        draw.rounded_rectangle([(70, 1150), (WIDTH - 70, 1330)], radius=25, fill=(45, 30, 80), outline=NEON_YELLOW, width=3)
        f_cd = load_font(65, bold=True)
        draw.text((WIDTH // 2, 1220), f"⏳ TIME REMAINING: {countdown_sec}s", fill=NEON_YELLOW, font=f_cd, anchor="mm")

        # Progress bar
        ratio = max(0.0, countdown_sec / 5.0)
        draw.line([(100, 1290), (WIDTH - 100, 1290)], fill=(60, 50, 95), width=10)
        draw.line([(100, 1290), (int(100 + (WIDTH - 200) * ratio), 1290)], fill=NEON_YELLOW, width=12)

    elif state == "reveal":
        draw.rounded_rectangle([(70, 1150), (WIDTH - 70, 1420)], radius=25, fill=(20, 50, 40), outline=GREEN_SUCCESS, width=4)
        f_ans = load_font(38, bold=True)
        draw.text((WIDTH // 2, 1200), f"🎉 ANSWER: [{quiz['correct']}] IS CORRECT!", fill=GREEN_SUCCESS, font=f_ans, anchor="mm")

        # Explanation
        f_exp_lbl = load_font(26, bold=True)
        draw.text((110, 1265), "GRAMMAR BREAKDOWN:", fill=NEON_YELLOW, font=f_exp_lbl, anchor="lm")

        f_exp_txt = load_font(34, bold=False)
        ewords = quiz["explanation"].split()
        elines = []
        ce = []
        for ew in ewords:
            tb = draw.textbbox((0, 0), " ".join(ce + [ew]), font=f_exp_txt)
            if tb[2] - tb[0] > (WIDTH - 240):
                elines.append(" ".join(ce))
                ce = [ew]
            else:
                ce = [ew]
        if ce: elines.append(" ".join(ce))
        for el_idx, el in enumerate(elines):
            draw.text((110, 1320 + el_idx * 48), el, fill=WHITE, font=f_exp_txt, anchor="lm")
    else:
        draw.rounded_rectangle([(70, 1150), (WIDTH - 70, 1300)], radius=25, fill=(30, 25, 65), outline=NEON_CYAN, width=2)
        f_prep = load_font(34, bold=True)
        draw.text((WIDTH // 2, 1225), "🤔 THINK CAREFULLY... COUNTDOWN COMING!", fill=WHITE, font=f_prep, anchor="mm")

    # Bottom CTA Box
    draw.rounded_rectangle([(70, 1480), (WIDTH - 70, 1720)], radius=25, fill=(35, 30, 75), outline=NEON_YELLOW, width=3)
    f_cta_big = load_font(36, bold=True)
    draw.text((WIDTH // 2, 1545), "💬 COMMENT YOUR SCORE: DID YOU GET IT RIGHT?", fill=NEON_YELLOW, font=f_cta_big, anchor="mm")
    f_cta_sub = load_font(30, bold=False)
    draw.text((WIDTH // 2, 1640), "Follow Daily English Quiz for your daily test! 🚀", fill=WHITE, font=f_cta_sub, anchor="mm")

    # Footer
    f_foot = load_font(26, bold=False)
    draw.text((WIDTH // 2, 1820), "❤️ Like • 🔄 Share With Friends • 💾 Save", fill=(148, 163, 184), font=f_foot, anchor="mm")

    canvas.convert("RGB").save(out_path, quality=95)

async def assemble_quiz_reel(quiz, run_dir):
    frames_dir = run_dir / "frames"
    clips_dir = run_dir / "clips"
    audio_dir = run_dir / "audio"
    for d in [frames_dir, clips_dir, audio_dir]:
        d.mkdir(parents=True, exist_ok=True)

    clips = []

    # 1. Intro Speech + Question frame
    intro_mp3 = audio_dir / "intro.mp3"
    await edge_tts.Communicate(quiz["intro_speech"], VOICE_HOST, rate="-10%").save(str(intro_mp3))
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(intro_mp3)], capture_output=True, text=True, check=True)
    intro_dur = float(r.stdout.strip())

    intro_frame = frames_dir / "frame_intro.png"
    render_quiz_frame(quiz, state="question", countdown_sec=5, out_path=str(intro_frame))

    intro_clip = clips_dir / "clip_intro.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(intro_frame), "-i", str(intro_mp3),
        "-vf", f"scale={WIDTH}:{HEIGHT},fps={FPS}",
        "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-preset", "fast", "-t", f"{intro_dur:.3f}", str(intro_clip)
    ], check=True, capture_output=True)
    clips.append(intro_clip)

    # 2. Countdown 5 seconds (5 frames of 1 second each)
    for sec in range(5, 0, -1):
        cd_frame = frames_dir / f"frame_cd_{sec}.png"
        render_quiz_frame(quiz, state="countdown", countdown_sec=sec, out_path=str(cd_frame))
        cd_clip = clips_dir / f"clip_cd_{sec}.mp4"
        # Generate 1 sec silent audio or low tick
        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(cd_frame),
            "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
            "-vf", f"scale={WIDTH}:{HEIGHT},fps={FPS}",
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p", "-preset", "fast", "-t", "1.000", str(cd_clip)
        ], check=True, capture_output=True)
        clips.append(cd_clip)

    # 3. Reveal Speech + Answer Reveal Frame
    reveal_mp3 = audio_dir / "reveal.mp3"
    await edge_tts.Communicate(quiz["reveal_speech"], VOICE_HOST, rate="-10%").save(str(reveal_mp3))
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(reveal_mp3)], capture_output=True, text=True, check=True)
    reveal_dur = float(r.stdout.strip())

    reveal_frame = frames_dir / "frame_reveal.png"
    render_quiz_frame(quiz, state="reveal", countdown_sec=0, out_path=str(reveal_frame))

    reveal_clip = clips_dir / "clip_reveal.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(reveal_frame), "-i", str(reveal_mp3),
        "-vf", f"scale={WIDTH}:{HEIGHT},fps={FPS}",
        "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-preset", "fast", "-t", f"{reveal_dur:.3f}", str(reveal_clip)
    ], check=True, capture_output=True)
    clips.append(reveal_clip)

    # Concat
    concat_txt = run_dir / "concat.txt"
    with open(concat_txt, "w") as f:
        for c in clips:
            f.write(f"file '{c.resolve().as_posix()}'\n")

    final_v = run_dir / "interactive_quiz_reel.mp4"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(final_v)], check=True, capture_output=True)
    return final_v

async def run_quiz_generation(idx=0):
    quiz = QUIZZES[idx % len(QUIZZES)]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = OUTPUT_DIR / f"run_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"[Quiz Challenge] Generating: {quiz['question']}...")
    final_v = await assemble_quiz_reel(quiz, run_dir)

    meta = {
        "title": f"Can you answer this in 5 seconds? 🎯 English Quiz Challenge",
        "description": f"Test your English level! {quiz['question']} Comment your answer below! Explanation: {quiz['explanation']} Follow for daily quizzes! 🌟",
        "question": quiz["question"],
        "correct": quiz["correct"]
    }
    with open(run_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"[Quiz Challenge] Video ready: {final_v}")
    return final_v, meta
