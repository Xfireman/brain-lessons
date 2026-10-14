"""Render an explicitly scripted replay from real offline hook decisions.

Maintainer-only dependency: Pillow. Product runtime remains stdlib-only.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets"
COLORS = {"paper": "#F3F0E8", "ink": "#173E34", "muted": "#58685D",
          "terminal": "#13251F", "text": "#F2F4EC", "dim": "#B9C6B9", "accent": "#EDAD82"}


def font(size):
    for candidate in ("DejaVuSansMono.ttf", "/System/Library/Fonts/Menlo.ttc"):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    raise SystemExit("Install DejaVu Sans Mono or run on a Mac with Menlo")


def frame(step, title, lines):
    canvas = Image.new("RGB", (1280, 640), COLORS["paper"])
    draw = ImageDraw.Draw(canvas)
    draw.text((48, 30), "BRAIN / LESSONS", font=font(24), fill=COLORS["ink"])
    draw.text((940, 34), f"OFFLINE REPLAY  {step}/4", font=font(16), fill=COLORS["muted"])
    draw.text((48, 90), title, font=font(36), fill=COLORS["ink"])
    draw.rounded_rectangle((48, 160, 1232, 530), radius=12, fill=COLORS["terminal"])
    draw.text((76, 181), "project / brain-lessons", font=font(17), fill=COLORS["dim"])
    draw.line((76, 218, 1204, 218), fill=COLORS["muted"], width=1)
    for index, (line, emphasis) in enumerate(lines):
        selected_font = font(23)
        assert draw.textlength(line, font=selected_font) <= 1128, line
        draw.text((76, 245 + index * 42), line, font=selected_font,
                  fill=COLORS["accent"] if emphasis else COLORS["text"])
    draw.text((48, 556), "Actual hook decisions. Synthetic inputs. No model or tool execution.",
              font=font(19), fill=COLORS["muted"])
    draw.text((48, 598), "github.com/Xfireman/brain-lessons", font=font(19), fill=COLORS["ink"])
    return canvas


def main():
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "PYTHONDONTWRITEBYTECODE": "1"}
    result = subprocess.run([sys.executable, "-m", "brain_lessons", "demo", "--scenario", "generated-client", "--json"],
                            env=env, cwd=ROOT, check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    assert not data["model_called"] and not data["tools_executed"]
    assert data["checks"]["problems"] == []
    blocked, allowed = data["calls"]
    assert blocked["decision"] == "deny" and allowed["decision"] == "none"
    assert "schema/api.json" in blocked["reason"]
    frames = [
        frame(1, "A correction worth keeping.", [
            ("Don't edit src/generated/ directly.", True),
            ("Change schema/api.json, then regenerate.", False),
            ("", False),
            ("Saved: .brain/lessons/generated-client.json", False),
            ("Scope: Edit + Write / src/generated/* / block", False)]),
        frame(2, "Check both sides of the rule.", [
            (f"MATCH   {blocked['path']}", True),
            (f"MISS    {allowed['path']}", False),
            ("", False),
            (f"{data['checks']['lessons']} rule / {data['checks']['examples_checked']} examples / 0 problems", False),
            ("Preview without executing either edit.", False)]),
        frame(3, "Catch it at the tool call.", [
            (f"apply_patch -> {blocked['path']}", False),
            (f"Decision: {blocked['decision'].upper()}", True),
            ("", False),
            ("Source: .brain/lessons/generated-client.json", False),
            ("Next: change schema/api.json, then regenerate.", False)]),
        frame(4, "Keep ordinary work moving.", [
            (f"apply_patch -> {allowed['path']}", False),
            ("Decision: no Brain decision", True),
            ("Host permissions still apply.", False),
            ("", False),
            ("Try: brain-lessons demo --scenario generated-client", False)]),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    frames[0].save(OUT / "generated-client.gif", save_all=True, append_images=frames[1:],
                   duration=[4500, 4500, 5000, 6000], loop=0, optimize=True)
    frames[2].save(OUT / "social-preview.png")
    (OUT / "demo-result.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"frames": len(frames), "duration_seconds": 20,
                      "files": {p.name: p.stat().st_size for p in OUT.iterdir() if p.is_file()}}))


if __name__ == "__main__":
    main()
