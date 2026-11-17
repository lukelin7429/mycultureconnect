"""Record every 🔊 phrase on the tutoring lesson pages with a natural (neural) voice.

Scans tutoring*.html for say('...') calls, writes one MP3 per phrase to
assets/audio/lesson/, and a manifest (text -> file) that lesson.js reads.
Phrases that already have an MP3 are skipped, so re-running after adding a
lesson only records the new lines. Needs `edge-tts` on PATH.
"""
import glob, hashlib, json, os, re, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "audio", "lesson")
VOICE = "en-US-AvaMultilingualNeural"
RATE = "-8%"
# Words the default voice says oddly, re-recorded with a voice Luke picked by ear.
VOICE_FOR = {"genre": "en-US-JennyNeural"}

def phrases():
    found = set()
    for path in sorted(glob.glob(os.path.join(ROOT, "tutoring*.html"))):
        for m in re.finditer(r"say\('((?:[^'\\]|\\.)*)'\)", open(path, encoding="utf-8").read()):
            found.add(m.group(1).replace("\\'", "'"))
    return sorted(found)

def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = {}
    for text in phrases():
        voice = VOICE_FOR.get(text, VOICE)
        key = text if voice == VOICE else text + "|" + voice
        name = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12] + ".mp3"
        dest = os.path.join(OUT, name)
        if not os.path.exists(dest):
            subprocess.run(["edge-tts", "--voice", voice, f"--rate={RATE}",
                            "--text", text, "--write-media", dest], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        manifest[text] = name
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=0, sort_keys=True)
    print(f"{len(manifest)} phrases recorded in assets/audio/lesson/")

if __name__ == "__main__":
    main()
