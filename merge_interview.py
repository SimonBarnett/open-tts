from pathlib import Path
import subprocess

def main():
    base_dir = Path("M:\\open-tts\\interview_audio")  # Change if needed
    
    leo_dir = base_dir / "leo"
    eve_dir = base_dir / "eve"
    
    # Collect all mp3 files
    all_files = []
    
    # Get Leo and Eve files
    leo_files = sorted(leo_dir.glob("leo_*.mp3"), key=lambda x: int(x.stem.split('_')[1]))
    eve_files = sorted(eve_dir.glob("eve_*.mp3"), key=lambda x: int(x.stem.split('_')[1]))
    
    # Combine them in correct order (01, 02, 03, ...)
    all_mp3s = []
    for leo, eve in zip(leo_files, eve_files):
        all_mp3s.append(leo)
        all_mp3s.append(eve)
    
    if len(leo_files) > len(eve_files):
        all_mp3s.append(leo_files[-1])
    
    print(f"Found {len(all_mp3s)} audio segments")
    
    if not all_mp3s:
        print("No mp3 files found!")
        return

    # Create file list for ffmpeg
    list_file = base_dir / "concat_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for mp3 in all_mp3s:
            f.write(f"file '{mp3.absolute()}'\n")

    output_file = base_dir / "full_interview.mp3"

    print("Merging all segments in order...")

    try:
        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(list_file), "-c", "copy", str(output_file)
        ], check=True)
        
        print(f"\n✅ SUCCESS!")
        print(f"Full interview saved as: {output_file}")
        print(f"Total segments: {len(all_mp3s)}")
        
    except FileNotFoundError:
        print("❌ ffmpeg not found! Please make sure ffmpeg is installed and in your PATH.")
    except subprocess.CalledProcessError as e:
        print("❌ Merge failed.")
    finally:
        list_file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()