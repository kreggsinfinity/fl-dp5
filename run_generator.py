import sys
import asyncio
from quiz_generator import run_quiz_generation

def main():
    print("Starting Interactive English Quiz generator (9:16 Vertical Reel)...")
    video_p, meta = asyncio.run(run_quiz_generation(idx=0))
    print(f"Done! Final video generated: {video_p}")

if __name__ == "__main__":
    main()
