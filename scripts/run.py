"""Convert piano audio/video or MIDI into a draft MusicXML score, quantized MIDI, and PDF."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time


def transcribe(wav, output, device, segment):
    import torch
    import soundfile as sf
    import moduleconf
    import transkun
    from transkun.Data import writeMidi

    base = Path(transkun.__file__).parent / 'pretrained'
    weight = base / '2.0.pt'
    cfg = moduleconf.parseFromFile(str(base / '2.0.conf'))['Model']
    torch.set_num_threads(8)
    model = cfg.module.TransKun(conf=cfg.config).to(device)
    checkpoint = torch.load(weight, map_location='cpu', weights_only=True)
    state = checkpoint.get('best_state_dict', checkpoint.get('state_dict'))
    model.load_state_dict(state, strict=True)
    model.eval()
    audio, sr = sf.read(wav, dtype='float32', always_2d=True)
    if sr != model.fs:
        import soxr
        audio = soxr.resample(audio, sr, model.fs)
    if device == 'cuda':
        torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    with torch.inference_mode():
        events = model.transcribe(
            torch.from_numpy(audio).to(device),
            segmentSizeInSecond=segment,
            stepInSecond=segment / 2,
            discardSecondHalf=False,
        )
    writeMidi(events).write(str(output))
    return {
        'model': 'Transkun 2.0.1 / bundled 2.0.pt (no pedal extension)',
        'parameters': sum(p.numel() for p in model.parameters()),
        'checkpoint_sha256': hashlib.sha256(weight.read_bytes()).hexdigest(),
        'device': device,
        'audio_seconds': len(audio) / model.fs,
        'inference_seconds': time.perf_counter() - start,
        'peak_gpu_allocated_mb': torch.cuda.max_memory_allocated() / 2**20 if device == 'cuda' else None,
    }


def make_score(midi_path, out, args):
    import pretty_midi
    from music21 import stream, note, chord, meter, clef, instrument, layout, metadata, converter, key
    import numpy as np

    midi = pretty_midi.PrettyMIDI(str(midi_path))
    notes = sorted((n for i in midi.instruments if not i.is_drum for n in i.notes), key=lambda n: n.start)
    if not notes:
        raise ValueError('No piano notes detected in MIDI input.')
    bpm = args.bpm or float(midi.estimate_tempo())
    if not args.bpm:
        while bpm > 160:
            bpm /= 2
        while bpm < 55:
            bpm *= 2
    origin = notes[0].start if args.start_offset is None else args.start_offset
    timing = json.loads(Path(args.timing_map).read_text(encoding='utf-8')) if args.timing_map else None
    hands = json.loads(Path(args.hand_map).read_text(encoding='utf-8')) if args.hand_map else []

    def beat_at(t):
        if timing:
            return float(np.interp(t, timing['seconds'], timing['quarters']))
        return (t - origin) * bpm / 60

    def split_at(t):
        matches = [h for h in hands if h['seconds'] <= t]
        return matches[-1]['split'] if matches else args.split

    q = 1 / args.grid
    score = stream.Score()
    score.metadata = metadata.Metadata(
        title=args.title or Path(args.input).stem,
        composer='Automatic transcription - draft',
    )
    parts = []
    quantized = pretty_midi.PrettyMIDI(initial_tempo=bpm)
    max_voices = []
    for right in [True, False]:
        part = stream.Part(id='RH' if right else 'LH')
        piano = instrument.Piano()
        piano.partName = 'RH' if right else 'LH'
        piano.partAbbreviation = piano.partName
        part.insert(0, piano)
        initial_treble = right or bool(hands and hands[0].get('left_clef') == 'treble')
        part.insert(0, clef.TrebleClef() if initial_treble else clef.BassClef())
        if not right and hands:
            for h in hands:
                if h['seconds'] == 0:
                    continue
                part.insert(
                    max(0, round(beat_at(h['seconds']) / q) * q),
                    clef.TrebleClef() if h.get('left_clef') == 'treble' else clef.BassClef(),
                )
        if args.key:
            part.insert(0, key.Key(args.key))
        part.insert(0, meter.TimeSignature(args.meter))
        groups = {}
        ins = pretty_midi.Instrument(0, name='Right hand draft' if right else 'Left hand draft')
        for n in notes:
            if (n.pitch >= split_at(n.start)) != right:
                continue
            onset = max(0, round(beat_at(n.start) / q) * q)
            end = max(onset + q, round(beat_at(n.end) / q) * q)
            groups.setdefault((onset, end), []).append(n)
            ins.notes.append(pretty_midi.Note(n.velocity, n.pitch, onset * 60 / bpm, end * 60 / bpm))
        voices, ends = [], []
        for (onset, end), ns in sorted(groups.items()):
            available = next((i for i, e in enumerate(ends) if e <= onset), None)
            if available is None:
                available = len(voices)
                voices.append(stream.Voice(id=available + 1))
                ends.append(0)
            names = [pretty_midi.note_number_to_name(n.pitch) for n in ns]
            obj = chord.Chord(names) if len(ns) > 1 else note.Note(names[0])
            obj.quarterLength = end - onset
            voices[available].insert(onset, obj)
            ends[available] = end
        if not voices:
            voices = [stream.Voice()]
            voices[0].append(note.Rest(quarterLength=4))
        for voice in voices:
            part.insert(0, voice)
        parts.append(part)
        score.insert(0, part)
        quantized.instruments.append(ins)
        max_voices.append(len(voices))
    score.insert(0, layout.StaffGroup(parts, name='Piano', symbol='brace', barTogether=True))
    score.makeNotation(inPlace=True)
    xml = out / 'score.musicxml'
    score.write('musicxml', fp=str(xml))

    # Give every note an explicit voice so MusicXML importers keep multi-voice layers aligned.
    import xml.etree.ElementTree as ET

    tree = ET.parse(xml)
    for part_xml in tree.findall('./part'):
        values = sorted({v.text for v in part_xml.findall('.//voice')}, key=int)
        voice_map = {v: str(i + 1) for i, v in enumerate(values)}
        for v in part_xml.findall('.//voice'):
            v.text = voice_map[v.text]
    for n in tree.findall('.//note'):
        if n.find('voice') is None:
            voice = ET.Element('voice')
            voice.text = '1'
            duration = n.find('duration')
            n.insert(list(n).index(duration) + 1 if duration is not None else 0, voice)
        if n.find('rest') is not None and n.findtext('voice') == '1':
            n.attrib.pop('print-object', None)
    tree.write(xml, encoding='utf-8', xml_declaration=True)
    converter.parse(str(xml))
    quantized.write(str(out / 'score-quantized.mid'))
    return {
        'notes': len(notes),
        'bpm': bpm,
        'bpm_source': 'manual' if args.bpm else 'MIDI onset estimate',
        'meter': args.meter,
        'meter_source': 'user/default, not detected',
        'grid_per_quarter': args.grid,
        'hand_split_midi_pitch': args.split,
        'timing_map': timing,
        'hand_map': hands,
        'key': args.key,
        'first_note_shift_seconds': origin,
        'voices_per_staff': max_voices,
        'warnings': [
            'Draft only: fixed tempo/grid and pitch-based hand split require musical review.',
            'Performance MIDI retains model timing; quantized MIDI and score are separate derivatives.',
            'Rubato, pickups, tuplets, crossing hands and pedal notation need review.',
        ],
    }


def render_pdf(xml, out, musescore=None):
    import pymupdf

    if musescore:
        subprocess.run([musescore, '-o', str(out / 'score.pdf'), str(xml)], check=True)
        backend = 'MuseScore'
    else:
        import verovio
        import resvg_py

        tk = verovio.toolkit()
        tk.setOptions({
            'inputFrom': 'musicxml',
            'pageWidth': 2100,
            'pageHeight': 2970,
            'scale': 40,
            'adjustPageHeight': False,
            'footer': 'none',
            'header': 'none',
        })
        if not tk.loadFile(str(xml)):
            raise RuntimeError('Verovio failed to load MusicXML')
        pdf = pymupdf.open()
        for page in range(1, tk.getPageCount() + 1):
            svg = tk.renderToSVG(page)
            png = resvg_py.svg_to_bytes(svg_string=svg, background='white', zoom=3)
            target = pdf.new_page(width=595.276, height=841.89)
            target.insert_image(pymupdf.Rect(20, 50, 575.276, 815), stream=png)
            import xml.etree.ElementTree as ET

            title = ET.parse(xml).findtext('.//work-title') or 'Automatic piano transcription'
            target.insert_text((28, 28), title[:70] + ' - draft', fontsize=12)
            target.insert_text((28, 42), 'Review rhythm, hands and accidentals before use', fontsize=8)
            target.insert_text((285, 830), str(page), fontsize=9)
        pdf.save(out / 'score.pdf', deflate=True)
        pdf.close()
        backend = 'Verovio + resvg (~300dpi) + PyMuPDF'
    doc = pymupdf.open(out / 'score.pdf')
    if not len(doc):
        raise RuntimeError('PDF is empty')
    doc[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(out / 'preview.png')
    return {'pdf_backend': backend, 'pages': len(doc)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', help='Input audio, video, or MIDI file')
    p.add_argument('--out', required=True, help='Output directory')
    p.add_argument('--device', choices=['cuda', 'cpu'], default='cuda')
    p.add_argument('--bpm', type=float)
    p.add_argument('--meter', default='4/4')
    p.add_argument('--grid', type=int, default=4, choices=[2, 3, 4, 6, 8])
    p.add_argument('--split', type=int, default=60)
    p.add_argument('--title')
    p.add_argument('--start-offset', type=float)
    p.add_argument('--segment', type=float, default=16)
    p.add_argument('--musescore', help='Optional path to MuseScore executable for PDF rendering')
    p.add_argument('--midi-only', action='store_true')
    p.add_argument('--timing-map')
    p.add_argument('--hand-map')
    p.add_argument('--key')
    args = p.parse_args()
    if args.bpm is not None and args.bpm <= 0:
        p.error('bpm must be positive')
    if args.segment <= 0:
        p.error('segment must be positive')
    source = Path(args.input).resolve(strict=True)
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'input': str(source), 'status': 'started'}
    try:
        if source.suffix.lower() in ['.mid', '.midi']:
            shutil.copy2(source, out / 'performance.mid')
            report['transcription'] = 'supplied MIDI; model not run'
        else:
            ffmpeg = shutil.which('ffmpeg')
            if not ffmpeg:
                raise RuntimeError('FFmpeg is not on PATH')
            wav = out / 'audio.wav'
            subprocess.run([
                ffmpeg, '-hide_banner', '-loglevel', 'error', '-i', str(source),
                '-map', '0:a:0', '-vn', '-ac', '1', '-ar', '44100', '-c:a', 'pcm_s16le', str(wav),
            ], check=True)
            report['transcription'] = transcribe(wav, out / 'performance.mid', args.device, args.segment)
        if not args.midi_only:
            report['score'] = make_score(out / 'performance.mid', out, args)
            report['render'] = render_pdf(out / 'score.musicxml', out, args.musescore)
        report['status'] = 'complete'
    except Exception as e:
        report['status'] = 'failed'
        report['error'] = repr(e)
        raise
    finally:
        (out / 'run.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
