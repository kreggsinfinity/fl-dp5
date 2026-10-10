import sys
import asyncio
from quiz_generator import run_quiz_generation

def main():
    turns = 4
    if "--test" in sys.argv:
        turns = 2
    elif "--full" in sys.argv:
        turns = 16
    print(f"Starting Interactive Quiz Podcast (16:9 Landscape, turns={turns})...")
    video_p, meta = asyncio.run(run_quiz_generation(topic_idx=0, turns_count=turns))
    print(f"Done! Final video generated: {video_p}")

if __name__ == "__main__":
    main()
