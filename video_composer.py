import os, subprocess, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import config
from audio_visualizer import AudioSpectrumVisualizer

def render_podcast_video(image_path: str, audio_path: str, subtitle_chunks: list, output_video_path: str, fps: int = 30, preview_seconds: float = None) -> str:
    print(f"[VideoComposer] Initializing video render: {output_video_path}...")
    visualizer = AudioSpectrumVisualizer(audio_path, fps=fps)
    total_frames = visualizer.total_frames
    if preview_seconds:
        total_frames = min(total_frames, int(preview_seconds * fps))
        print(f"[VideoComposer] Preview active: rendering {total_frames} frames ({preview_seconds:.1f}s)...")

    base_img = Image.open(image_path).convert("RGBA")
    if base_img.size != (config.VIDEO_WIDTH, config.VIDEO_HEIGHT):
        base_img = base_img.resize((config.VIDEO_WIDTH, config.VIDEO_HEIGHT), Image.Resampling.LANCZOS)

    # Static Branding Ribbon & Footer
    draw_base = ImageDraw.Draw(base_img)
    font_path = config.FONT_PATH if os.path.exists(config.FONT_PATH) else config.FALLBACK_FONT_PATH
    sub_font = ImageFont.truetype(font_path, config.SUBTITLE_FONT_SIZE)
    f_brand = ImageFont.truetype(font_path, 28)

    # 1. Circular Channel Logo Badge with Antialiased Mask & Gold Rim
    logo_size = 104
    logo_x, logo_y = 50, 35
    if os.path.exists(config.LOGO_PATH):
        try:
            raw_logo = Image.open(config.LOGO_PATH).convert("RGBA")
            raw_logo = raw_logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)

            mask = Image.new("L", (logo_size * 4, logo_size * 4), 0)
            m_draw = ImageDraw.Draw(mask)
            m_draw.ellipse((0, 0, logo_size * 4, logo_size * 4), fill=255)
            mask = mask.resize((logo_size, logo_size), Image.Resampling.LANCZOS)

            circular_logo = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
            circular_logo.paste(raw_logo, (0, 0), mask)
            base_img.paste(circular_logo, (logo_x, logo_y), circular_logo)

            draw_base.ellipse(
                [(logo_x - 2, logo_y - 2), (logo_x + logo_size + 2, logo_y + logo_size + 2)],
                outline=(255, 215, 0, 240),
                width=3
            )
        except Exception:
            pass

    # 2. Dynamic Auto-Wrapping Top Branding Pill
    bbox = draw_base.textbbox((0, 0), config.CHANNEL_NAME, font=f_brand)
    text_w = bbox[2] - bbox[0]
    pill_start_x = 168
    text_start_x = pill_start_x + 48
    pill_end_x = text_start_x + text_w + 32

    draw_base.rounded_rectangle(
        [(pill_start_x, 50), (pill_end_x, 112)],
        radius=30,
        fill=(16, 20, 32, 230),
        outline=(255, 215, 0, 220),
        width=2
    )
    # Glowing green live indicator
    dot_cx = pill_start_x + 24
    draw_base.ellipse([(dot_cx - 8, 81 - 8), (dot_cx + 8, 81 + 8)], fill=(34, 197, 94))
    # Channel name text perfectly inside container
    draw_base.text((text_start_x, 66), config.CHANNEL_NAME, fill=(255, 255, 255), font=f_brand)

    # Footer
    draw_base.line([(0, 1025), (config.VIDEO_WIDTH, 1025)], fill=(45, 50, 70), width=2)
    draw_base.text((config.SUBTITLE_CENTER_X, 1052), config.TAGLINE, fill=(235, 225, 200), font=f_brand, anchor="mm")

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{config.VIDEO_WIDTH}x{config.VIDEO_HEIGHT}",
        "-pix_fmt", "bgr24",
        "-r", str(fps),
        "-i", "-",
        "-i", audio_path,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        output_video_path
    ]

    pipe = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    total_audio_sec = total_frames / float(fps)

    # Pre-render subtitle chunks
    space_w = draw_base.textbbox((0, 0), " ", font=sub_font)[2]
    processed_chunks = []
    for c in subtitle_chunks:
        words = c["words"]
        if not words:
            continue
        w_metrics = [{"word": w["word"], "start": w["start"], "end": w["end"], "width": draw_base.textbbox((0, 0), w["word"], font=sub_font)[2]} for w in words]
        total_w = sum(wm["width"] for wm in w_metrics) + max(0, len(w_metrics) - 1) * space_w
        processed_chunks.append({
            "start": c["start"], "end": c["end"], "total_w": total_w,
            "speaker": c.get("speaker", "female"), "words": w_metrics
        })

    active_chunk_idx = 0
    num_chunks = len(processed_chunks)

    for f_idx in range(total_frames):
        t_sec = f_idx / float(fps)
        while active_chunk_idx < num_chunks - 1 and t_sec > processed_chunks[active_chunk_idx]["end"]:
            active_chunk_idx += 1

        chunk = processed_chunks[active_chunk_idx] if active_chunk_idx < num_chunks and processed_chunks[active_chunk_idx]["start"] <= t_sec <= processed_chunks[active_chunk_idx]["end"] else None

        frame_img = base_img.copy()
        draw = ImageDraw.Draw(frame_img)

        # Draw audio visualizer
        visualizer.draw_frame(draw, f_idx)

        # Draw progress line
        ratio = min(1.0, t_sec / max(1.0, total_audio_sec))
        draw.line([(0, 1025), (int(config.VIDEO_WIDTH * ratio), 1025)], fill=(255, 215, 0), width=4)

        # Draw subtitle with STRICT edge clamping [60, 1860]
        if chunk:
            pill_pad = 35
            safe_min_x = 60 + pill_pad
            safe_max_x = (config.VIDEO_WIDTH - 60) - pill_pad - chunk["total_w"]
            ideal_sx = config.SUBTITLE_CENTER_X - (chunk["total_w"] // 2)

            if safe_max_x >= safe_min_x:
                sx = max(safe_min_x, min(ideal_sx, safe_max_x))
            else:
                sx = safe_min_x

            sy = config.SUBTITLE_Y

            # Glow & pill background
            draw.rounded_rectangle([
                (sx - pill_pad, sy - 15),
                (sx + chunk["total_w"] + pill_pad, sy + config.SUBTITLE_FONT_SIZE + 25)
            ], radius=20, fill=(12, 14, 22, 195), outline=(255, 215, 0, 130), width=1)

            curr_x = sx
            for wm in chunk["words"]:
                is_active = (wm["start"] <= t_sec <= wm["end"])
                color = (255, 215, 0) if is_active else (255, 255, 255)
                # Drop shadow
                draw.text((curr_x + 3, sy + 3), wm["word"], fill=(0, 0, 0, 220), font=sub_font)
                draw.text((curr_x, sy), wm["word"], fill=color, font=sub_font)
                curr_x += wm["width"] + space_w

        raw_bgr = np.array(frame_img.convert("RGB"))[:, :, ::-1].tobytes()
        pipe.stdin.write(raw_bgr)

        if (f_idx + 1) % (fps * 30) == 0:
            print(f"  [Video Render] Progress: {f_idx + 1}/{total_frames} frames ({(f_idx+1)/fps:.1f}s)")

    pipe.stdin.close()
    pipe.wait()
    print(f"[VideoComposer] Video rendered successfully: {output_video_path}")
    return output_video_path
