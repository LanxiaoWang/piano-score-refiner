"""Verify that a MusicXML score preserves all quantized MIDI note pitches, onsets, durations, and ties."""
import argparse
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import pretty_midi

STEP_TO_SEMITONE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def extract_xml_events(xml_path: Path):
    tree = ET.parse(xml_path)
    events = []
    for part in tree.findall('./part'):
        base = 0.0
        active = {}
        divisions = 10080
        for measure in part.findall('measure'):
            position = 0.0
            extent = 0.0
            last_start = 0.0
            for el in measure:
                if el.tag == 'attributes':
                    divisions = int(el.findtext('divisions') or divisions)
                if el.tag in ('backup', 'forward'):
                    position += int(el.findtext('duration')) / divisions * (-1 if el.tag == 'backup' else 1)
                if el.tag != 'note':
                    continue
                dur = int(el.findtext('duration') or 0) / divisions
                start = last_start if el.find('chord') is not None else position
                if el.find('chord') is None:
                    last_start = start
                    position += dur
                extent = max(extent, start + dur)
                pitch = el.find('pitch')
                if pitch is None:
                    continue
                name = pitch.findtext('step')
                alter = int(pitch.findtext('alter') or 0)
                midi = (int(pitch.findtext('octave')) + 1) * 12 + STEP_TO_SEMITONE[name] + alter
                voice = el.findtext('voice') or '1'
                key = (voice, midi)
                ties = {t.get('type') for t in el.findall('tie')}
                if 'stop' in ties:
                    assert key in active, ('unmatched tie', key, measure.get('number'))
                    event = active[key]
                    assert abs(event[2] - (base + start)) < 1e-5, ('tie gap', key, event, base + start)
                    event[2] = base + start + dur
                else:
                    event = [midi, base + start, base + start + dur]
                    events.append(event)
                if 'start' in ties:
                    active[key] = event
                else:
                    active.pop(key, None)
            base += extent
        assert not active, ('unfinished ties', active)
    return events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', help='Output directory from run.py, or path to a MusicXML file')
    parser.add_argument('--midi', help='Reference MIDI path (required if target is a MusicXML file)')
    parser.add_argument('--bpm', type=float, help='BPM for beat conversion (defaults to run.json or MIDI estimate)')
    args = parser.parse_args()

    target = Path(args.target)
    if target.is_dir():
        xml_path = target / 'score.musicxml'
        midi_path = Path(args.midi) if args.midi else target / 'score-quantized.mid'
        bpm = args.bpm or json.loads((target / 'run.json').read_text(encoding='utf-8'))['score']['bpm']
        out_json = target / 'score-verification.json'
    else:
        xml_path = target
        if not args.midi:
            parser.error('--midi is required when target is a MusicXML file')
        midi_path = Path(args.midi)
        midi_obj = pretty_midi.PrettyMIDI(str(midi_path))
        bpm = args.bpm or float(midi_obj.estimate_tempo())
        out_json = None

    events = extract_xml_events(xml_path)
    midi_data = pretty_midi.PrettyMIDI(str(midi_path))
    expected = [
        (n.pitch, round(n.start * bpm / 60, 2), round(n.end * bpm / 60, 2))
        for inst in midi_data.instruments
        for n in inst.notes
    ]
    actual = [(n, round(s, 2), round(e, 2)) for n, s, e in events]
    assert Counter(actual) == Counter(expected), {
        'extra': list((Counter(actual) - Counter(expected)).items())[:10],
        'missing': list((Counter(expected) - Counter(actual)).items())[:10],
    }
    result = {
        'notes': len(events),
        'pitch_onset_duration_preserved_after_xml_tie_reconstruction': True,
        'all_ties_contiguous': True,
    }
    if out_json:
        out_json.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
