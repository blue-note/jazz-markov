import midi
import pykov
import sys
import random
from itertools import cycle
import shelve
import os

class Note:
       def __init__(self, pitch, duration, note_type):
        # pitch = integer
        # duration = ticks
        # note_type = 'N' or 'R'
        self.pitch = pitch
        self.duration = duration
        self.note_type = note_type

       def __str__(self):
        return "type: " + self.note_type + "\n" + "pitch: " + str(self.pitch) + "\n" + "duration: " + str(self.duration) + " \n"

def train(input_file, phrase_transitions, abstract_note_to_pitch, category_to_abstract_melodies):
    ticks_so_far = 0
    pattern = midi.read_midifile(input_file)
    metadata = pattern[0]
    melody = pattern[1]
    bassline = pattern[2]
    key = -1
    beats_per_measure = -1
    ticks_per_measure = -1
    chord_progression = iter(get_chord_progression(bassline, ticks_per_measure))
    iterTrack = iter(melody)
    pitch = -1
    velocity = -1 

 
    # extract time and key signature
    for el in metadata:
        if type(el) is midi.KeySignatureEvent: 
            key = el.data[0]
        elif type(el) is midi.TimeSignatureEvent:
            beats_per_measure = el.data[0]
            ticks_per_measure = pattern.resolution * beats_per_measure
    if key == -1 or beats_per_measure == -1:
        sys.exit("No time or key signature")

    event = ""
    curr_chord = next(chord_progression)
    prev_chord = ""
    curr_category = ""
    prev_category = ""
    curr_phrase = list()
    prev_phrase = list()

    while type(event) != midi.EndOfTrackEvent:
        event = next(iterTrack)
        if type(event) is midi.NoteOnEvent or type(event) is midi.NoteOffEvent:
            pitch = event.data[0]
            velocity = event.data[1]
        else:
            continue # bypass meta track events
        if type(event) is midi.NoteOnEvent and velocity != 0: # start of note
               if event.tick > 0: # register prior rest
                    curr_phrase.append(Note(-1, event.tick, 'R'))
                    ticks_so_far += event.tick

        elif type(event) is midi.NoteOffEvent or velocity == 0: # end of note
            curr_phrase.append(Note(pitch, event.tick, 'N'))
            ticks_so_far += event.tick

        if ticks_so_far >= ticks_per_measure:
            ticks_so_far = 0 # reset tick count

            # get "feel" category
            abstract_melody = to_abstract_melody(curr_phrase, curr_chord)
            curr_category = get_category(abstract_melody)

            if len(prev_phrase) > 0:
                # save feel, chord --> feel, chord transition
                if ((prev_category, prev_chord), (curr_category, curr_chord)) in phrase_transitions:
                    phrase_transitions[((prev_category, prev_chord), (curr_category, curr_chord))] += 1
                else:
                    phrase_transitions[((prev_category, prev_chord), (curr_category, curr_chord))] = 1

                # save abstract melody under category

                if curr_category in category_to_abstract_melodies:
                    category_to_abstract_melodies[curr_category].append(abstract_melody)
                else:
                    category_to_abstract_melodies[curr_category] = list()
                    category_to_abstract_melodies[curr_category].append(abstract_melody)

                # save abstract note type --> pitch prob

            prev_phrase = curr_phrase
            curr_phrase = list()
            prev_chord = curr_chord
            curr_chord = next(chord_progression)
            prev_category = curr_category

def get_notes(track):
    # returns list of note objects based on midi track


def get_chord_progression(bass_track, ticks_per_measure):
     # returns list of chords corresponding to bassline
    

def to_abstract_melody(melody, curr_chord):
    # returns note representations
    pass

def get_category(melody):
    pass

if __name__ == "__main__":
    phrase_transitions = dict()
    abstract_note_to_pitch = dict()
    category_to_abstract_melodies = dict()
    train(sys.argv[1], phrase_transitions, abstract_note_to_pitch)