# Piano Score Refiner

[English](README.md) | [简体中文](README.zh-CN.md)

An AI Agent Skill for refining automatically transcribed piano scores. It accepts existing MIDI, MusicXML, or MuseScore project files and guides an AI assistant through hand allocation, redundant-rest cleanup, clef and layout improvements, and checks that note velocities and pedal data survive the edits.

## Background

Piano score drafts generated with automatic transcription tools, such as audio-to-MIDI models like Transkun, can be difficult to sight-read after import into notation software—even when most pitches and durations are correct:

- A fixed pitch threshold may split the hands mechanically, assigning melody and accompaniment awkwardly.
- Overlapping voices can produce large numbers of auxiliary rests and clutter the score.
- Extreme registers may require too many ledger lines, while local clef changes or octave markings can be unclear.
- Ties and beam groups may obscure the meter and make rhythms difficult to count.
- Manual or scripted voice rearrangement can lose per-note velocity and pedal controller events (CC64/CC67).

This project organizes score-refinement rules and checks into a structured Agent Skill. AI assistants with file access, such as Codex, can follow it to improve notation and verify playback data.

## Key Features

| Common problem | Refinement approach |
|---|---|
| Mechanical hand splitting makes passages awkward to play | Consider surrounding hand movements, held notes, and the other hand's workload when reallocating notes |
| Dense rests and separate stems clutter overlapping voices | Combine chords with compatible durations; hide only redundant rests fully covered by other voices on the same staff, and retain independent voices with different durations |
| Confusing rhythms, ties, and beam groups | Review beaming, rests across beats, and ties according to the meter, while keeping each voice's measure duration complete |
| Too many ledger lines or ambiguous clefs and octaves | Adjust local clefs or 8va markings and add sparse pitch-name labels at ledger-line-heavy notes or large leaps when useful |
| Playback becomes flat or loses pedal after editing | Compare note starts and ends, individual velocities, tempo, and pedal events before and after the changes |
| The editor and exported PDF look different | Inspect both the notation editor's hidden-element view and the rendered PDF |

By default, changes affect notation and display only, preserving pitches, durations, and performance data. Request note omissions, transposition, shortened sustained notes, or rolled-chord arrangements separately in your prompt.

## Usage

Keep `README.md`, `SKILL.md`, and `SOP.md` together in one folder, or install the folder in your AI assistant's `skills` directory. Provide it alongside the score to an assistant that supports file operations.

Example prompt:

```text
Read piano-score-refiner/SKILL.md and refine this piano score according to SOP.md.

Make the notation clearer and easier to sight-read with both hands. Parse the structured score data first, then check hand allocation, held-note spans, voices and rests, rhythmic notation, clefs, and page layout.
Preserve the existing pitches, note durations, individual velocities, and pedal data by default. If the input is an unquantized performance MIDI, retain the original MIDI and explain the timing changes introduced by quantization.
Export an editable project and a PDF, together with a summary of the edits and verification results. Identify any hand-span difficulties that would require arrangement changes, such as omitting notes or shifting octaves, before making those changes.
```

Add any specific requirements to the prompt, such as refining only the first page, labeling difficult ledger-line notes with pitch names, or accommodating a particular hand span.

### Inputs and Outputs

- **Preferred input:** `.mscz / .mscx` (MuseScore projects) or `.musicxml / .mxl`, which already contain staff and voice structure. `.mid / .midi` files are also supported, but initial score creation requires decisions about meter and quantization. Scanned PDFs or images must first be converted to structured notation with an OMR tool.
- **Optional references:** Original audio, the original performance MIDI, or screenshots marking problematic measures.
- **Deliverables:** A refined editable project (`.mscz`), a printable `.pdf`, and an exported `.mid` when requested, along with the affected measures, retained hand-span difficulties, and playback-data comparison results.

## Reference Workflow: From Audio to Score

This Skill is not tied to a particular transcription model. If you already have MIDI or a notation project, start with score refinement above. For audio or video input, the following open-source toolchain provides a reference workflow:

`Audio extraction (FFmpeg) → Piano transcription (Transkun) → Draft generation (pretty_midi / music21) → Score refinement and engraving (Piano Score Refiner + MuseScore Studio)`

| Tool / Library | Purpose | Link |
|---|---|---|
| FFmpeg | Extract standard audio from video or audio sources | [Official download](https://ffmpeg.org/download.html) |
| Transkun | Transcribe piano audio into MIDI with velocity and pedal data | [GitHub](https://github.com/Yujia-Yan/Transkun) |
| pretty_midi | Read and process MIDI notes and controller events | [GitHub](https://github.com/craffel/pretty-midi) |
| music21 | Process rhythms and voices and generate draft MusicXML | [Official documentation](https://www.music21.org/music21docs/) |
| MuseScore Studio | Edit scores, adjust voices and layout, play back, and export PDFs | [Official download](https://musescore.org/en/download) |

### Starting from Audio

1. Install [Python](https://www.python.org/downloads/) and FFmpeg, then create a virtual environment.
2. Install a suitable CPU or CUDA build from the [PyTorch website](https://pytorch.org/get-started/locally/), then follow the official instructions to install Transkun, `pretty_midi`, and `music21`.
3. Run [`scripts/run.py`](scripts/run.py) to turn piano audio or MIDI into a performance MIDI (`performance.mid`), a quantized MIDI (`score-quantized.mid`), draft `score.musicxml`, and a preview PDF. Use [`scripts/verify_score.py`](scripts/verify_score.py) to check MusicXML notes and ties:
   ```bash
   python scripts/run.py input_audio.mp3 --out ./draft_out --device cuda
   python scripts/verify_score.py ./draft_out
   ```
4. Give the generated draft to an AI assistant for refinement with this Skill and MuseScore.

> **Reference environment:** This workflow was tested with Python 3.12, PyTorch/torchaudio 2.6.0 (CUDA 12.4), Transkun 2.0.1, music21 10.5.0, and MuseScore Studio 4.7.5. Salamander C5 Light and GeneralUser GS were also used for playback. Soundfonts affect playback timbre, not note recognition or score refinement.

## Repository Files

| File | Description |
|---|---|
| [README.md](README.md) | English project background, features, usage, and reference toolchain |
| [README.zh-CN.md](README.zh-CN.md) | Chinese version of the project overview and usage guide |
| [SKILL.md](SKILL.md) | Agent entry point defining when to use the Skill, processing modes, and the core workflow |
| [SOP.md](SOP.md) | Detailed rules for input parsing, rhythm and voices, hand allocation, layout annotations, and acceptance checks |
| [scripts/run.py](scripts/run.py) | Helper script for generating draft MusicXML, quantized MIDI, and a preview PDF from audio/video or raw MIDI |
| [scripts/verify_score.py](scripts/verify_score.py) | Check MusicXML notes, start/end timings, and cross-measure ties against the quantized MIDI |
| [LICENSE](LICENSE) | MIT License |

## Feedback and Contributions

Feedback through Issues and Pull Requests is welcome. For score-refinement problems, include before-and-after screenshots of the relevant measures, a minimal reproducible file (MIDI / MusicXML / MSCZ), and the notation you expected. Indicate whether the issue concerns pitch reading, rhythm, hand allocation, layout, or lost playback data so the rules can be improved.

## Acknowledgments and License

Parts of the toolchain were inspired by [piano-2-sheet](https://github.com/thanhpt1110/piano-2-sheet). Earlier versions used Verovio, resvg_py, and PyMuPDF for off-screen rendering tests; the workflow now uses MuseScore Studio for export.

This project is released under the [MIT License](LICENSE). Upstream tools and models retain their respective licenses.
