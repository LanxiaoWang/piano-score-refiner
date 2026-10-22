---
name: piano-score-refiner
description: >-
  Refine automatically transcribed or MIDI-imported piano drafts into clear, sight-readable scores. Use for MIDI, MusicXML, or MuseScore projects that need hand allocation, held-note span checks, voice and redundant-rest cleanup, rhythmic notation, clefs, pitch-name labels, or layout improvements, with checks that velocity and pedal data survive editing.
---

# Piano Score Refiner

[English](SKILL.md) | [简体中文](SKILL.zh-CN.md)

An execution guide for refining piano transcription drafts while protecting their performance data. Before working on a score, read [SOP.md](SOP.md) in the same directory for detailed decision rules and acceptance criteria. [README.md](README.md) provides the project overview and reference transcription workflow. The [`scripts/`](scripts/) directory contains helpers for generating drafts from audio/MIDI (`run.py`) and checking MusicXML event consistency (`verify_score.py`).

## Inputs and Scope

- **Supported formats:** Accept `.mid / .midi`, `.musicxml / .mxl`, and `.mscz / .mscx`. Parse structured score files first; use images or screenshots to locate problematic measures and inspect layout.
- **Supporting material:** Original audio can help check rhythm and missing notes. Scanned PDFs or images must first be converted to structured notation through OMR or manual transcription.
- **Scope confirmation:** Establish the target piece and page or measure range before starting. Ask the user only when a key preference is missing, such as permission to omit notes or a target hand-span limit.

## Processing Modes

Default to **notation refinement**. Preserve the existing notes and performance data unless the user explicitly requests otherwise:

| Mode | Scope |
|---|---|
| **Notation refinement (default)** | Adjust hand allocation, voices, rest visibility, clefs, rhythmic spelling, pitch-name labels, and layout; strictly preserve sounding pitches, start/end times, per-note velocities, tempo, and controller events such as pedal |
| **Performance-parameter adjustment** | Adjust dynamics, timing, pedal, or playback timbre as requested, and document differences from the original |
| **Simplification and arrangement** | Omit notes, transpose, shift octaves, shorten sustained notes, or introduce rolled chords as requested, listing every affected position |

For display-only refinement of an already approved project, use that project as the baseline and do not requantize. If initial score creation from raw performance MIDI requires quantization, retain the original performance MIDI and explain the timing changes introduced by snapping.

## Workflow

1. **Back up and parse the baseline**
   Back up the current project and retain the original input. Following [SOP sections 1–2](SOP.md#1-input-formats-and-available-data), parse staves, voices, note starts and ends, ties, transposition, tempo, and controller events. Calculate sounding pitch names and octaves using scientific pitch notation, with middle C = C4.
2. **Check rhythm and measure structure**
   Following [SOP section 3](SOP.md#3-quantization-and-polyphonic-notation), check meter, pickups, rubato, voice durations, beam groups, and tie relationships. Keep measure durations complete on every staff and repair any `Incomplete measure` import errors.
3. **Refine hand allocation**
   Following [SOP section 4](SOP.md#4-hand-allocation-and-fingering-suggestions), consider new attacks, notes still being held—including ties across measures—and subsequent hand movements. Before transferring notes, also assess the receiving hand's existing workload. If a span beyond an octave cannot be resolved without changing notes, retain the original notes and record the measure for the user to review.
4. **Clean up voices and redundant rests**
   Following [SOP section 3.1](SOP.md#31-voices-chords-and-redundant-rests), review voice structure. Combine notes into single-stem chords only when their attacks, durations, and tie relationships are fully compatible. Hide redundant auxiliary rests fully covered by other voices on the same staff, retaining rests that indicate whole-hand silence or clarify the beat. Change visibility only, keeping internal voice durations complete.
5. **Improve pitch reading and layout**
   Following [SOP section 5](SOP.md#5-score-readability-and-reading-aids), address excessive ledger lines, local 8va markings, clef changes, system spacing, and page turns. Where useful, add sparse pitch-name labels with no playback effect at ledger-line-heavy notes or leaps across octaves. Use the original spelling plus octave, such as `C2` or `G6`, and distinguish labels from fingerings. Hide duplicated end-of-system clef reminders when appropriate.
6. **Verify playback data and rendered output**
   Following [SOP sections 6–7](SOP.md#6-protecting-playback-and-controller-data), compare pitches, attacks, note ends, individual velocities, tempo, and pedal events before and after editing, retaining existing sound and reverb settings. Reopen the project in the target notation software and render every changed page, checking for overlapping symbols, obscured elements, or unintended missing notes.

## Delivery Requirements

- **Editor and export checks:** Inspect both the notation editor's display—for example, MuseScore's gray hidden-element view controlled by `Score/showInvisible`—and the exported PDF pages. Save the project view state according to the user's preference.
- **Files:** Deliver the refined editable project (`.mscz`), `.pdf`, and any requested `.mid` files. If both original performance MIDI and quantized notation MIDI are retained, name them separately and explain their purposes.
- **Change summary:** Provide a concise summary of affected measures, retained large-span difficulties, and the event-comparison and rendering checks.
