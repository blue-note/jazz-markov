import midi
import pykov
import sys
import random
from itertools import cycle
import shelve
import os
import math


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
    key_code = -1
    beats_per_measure = -1
    ticks_per_measure = -1
    
    iterTrack = iter(melody)
    pitch = -1
    velocity = -1 

 
    # extract time and key signature
    for el in metadata:
        if type(el) is midi.KeySignatureEvent: 
            key_code = el.data[0]
        elif type(el) is midi.TimeSignatureEvent:
            beats_per_measure = el.data[0]
            ticks_per_measure = pattern.resolution * beats_per_measure
    if key_code == -1 or beats_per_measure == -1:
        sys.exit("No time or key signature")

    key = get_key(key_code)
    chord_progression = get_chords(bassline, ticks_per_measure, key)
    for c in chord_progression:
        print c
        print "\n"
    #curr_chord = next(chord_progression)
    prev_chord = ""
    curr_category = ""
    prev_category = ""
    curr_phrase = list()
    prev_phrase = list()
    first_next = -1

    ## PHRASE TRANSITION LEARNING

    # # extract phrases 
    # notes = get_notes(melody)
    # for note in notes:

    #     ticks_so_far += note.duration
    #     curr_phrase.append(note)

    #     if ticks_so_far >= ticks_per_measure:
    #         ticks_so_far = ticks_so_far % ticks_per_measure # reset tick count, keeping remainder
    #         if ticks_so_far > 0:
    #             curr_phrase[len(curr_phrase)-1].duration -= ticks_so_far # truncate last note in last phrase

    #         if ticks_so_far > 0:
    #             first_next = note
    #             first_next.duration = ticks_so_far
    #         else:
    #             first_next = -1

    #         # get "feel" category
    #         abstract_melody = to_abstract_melody(curr_phrase, curr_chord)
    #         curr_category = get_category(abstract_melody)

    #         if len(prev_phrase) > 0:
    #             # save feel, chord --> feel, chord transition
    #             if ((prev_category, prev_chord), (curr_category, curr_chord)) in phrase_transitions:
    #                 phrase_transitions[((prev_category, prev_chord), (curr_category, curr_chord))] += 1
    #             else:
    #                 phrase_transitions[((prev_category, prev_chord), (curr_category, curr_chord))] = 1

    #             # save abstract melody under category

    #             if curr_category in category_to_abstract_melodies:
    #                 category_to_abstract_melodies[curr_category].append(abstract_melody)
    #             else:
    #                 category_to_abstract_melodies[curr_category] = list()
    #                 category_to_abstract_melodies[curr_category].append(abstract_melody)

    #             # save abstract note type --> pitch prob

    #             # <---FILL THIS IN ---> 

    #         prev_phrase = curr_phrase
    #         curr_phrase = list()
    #         if first_next != -1:
    #             curr_phrase.append(first_next)
    #         prev_chord = curr_chord
    #         curr_chord = next(chord_progression)
    #         prev_category = curr_category

def get_key(k):

    if k <= 7:
        return (k*7) % 12
    elif k >= 249:
        return (((k - 249)*7+11)%12)
    elif k >= 9 and k <= 23:
        return ((k-9)*7+20)%12 + 12

def get_notes(track):
    # returns list of note objects based on midi track
    notes = list()
    iterTrack = iter(track)
    event = ""
    while type(event) != midi.EndOfTrackEvent:
        event = next(iterTrack)
        if type(event) is midi.NoteOnEvent or type(event) is midi.NoteOffEvent:
            pitch = event.data[0]
            velocity = event.data[1]
        else:
            continue # bypass meta track events
        if type(event) is midi.NoteOnEvent and velocity != 0: # start of note
               if event.tick > 0: # register prior rest
                    notes.append(Note(-1, event.tick, 'R'))

        elif type(event) is midi.NoteOffEvent or velocity == 0: # end of note
            notes.append(Note(pitch, event.tick, 'N'))

    return notes


def get_chords(bass_track, ticks_per_measure, key):
    key = key % 12 # account for minor keys
    notes = get_notes(bass_track)
    ticks_so_far = 0
    chord_progression = list()
    current_measure = dict() # dict of pitches to durations
    first_next = -1

    for i in range(len(notes)):
        note = (notes[i].pitch + 12 - key) % 12 # get scale note relative to key
        duration = notes[i].duration
        ticks_so_far += duration

        if notes[i].note_type != 'R':
            # print note
            if note in current_measure:
                current_measure[note] += duration
            else:
                current_measure[note] = duration
        
        if ticks_so_far >= ticks_per_measure: 
            # print "\n"
            ticks_so_far = ticks_so_far % ticks_per_measure

            max_weight = 0
            matched_chord = -1
            for i in range(0, 23): # iterate through major and minor chords
                minor = False
                o = i
                i = (i + 12 - key) % 12
                weight = 0
                first = -1
                third = -1
                fifth = -1
                major = [i, i+2, i+4, i+5, i+7, i+9, i+11]
                minor = [i, i+2, i+3, i+5, i+7, i+8, i+10]
                
                if o < 12: # major key
                    first = i
                    third = (i + 4) % 12
                    fifth = (third + 3) % 12

                else: # minor chord
                    minor = True
                    first = i
                    third = (i + 3) % 12
                    fifth = (third + 4) % 12

                # sum the length of matching occurrences

                if first in current_measure:
                    weight += current_measure[first]
                if third in current_measure:
                    weight += current_measure[third]
                if fifth in current_measure:
                    weight += current_measure[fifth]

                # find max matching chord 
                if weight > max_weight:
                    max_weight = weight
                    if minor:
                        matched_chord = i + 12
                    else:
                        matched_chord = i
           
            chord_progression.append(matched_chord)
            current_measure = dict()
            if ticks_so_far > 0 and notes[i].note_type != 'R': # carry over note from last measure
                current_measure[note] = duration 
           
    return chord_progression

def get_chord_progression(bass_track, ticks_per_measure, key):
     # returns list of chords corresponding to bassline

    key = key % 12 # account for minor keys
    notes = get_notes(bass_track)
    ticks_so_far = 0
    first_half = list()
    pitches = dict() # pitches occurring in first half
    chord_progression = list()
    first_in_next = -1

    for i in range(len(notes)):
        ticks_so_far += notes[i].duration
        if ticks_so_far > ticks_per_measure:
            ticks_so_far = ticks_so_far % ticks_per_measure

            first_half.append(notes[i])

            # get notes in first half of measure
            while ticks_so_far <= ticks_per_measure/2 and i < len(notes)-1:
                i += 1
                first_half.append(notes[i])
                ticks_so_far += notes[i].duration
                
            for n in first_half:
                if n.note_type is 'N':
                    if n.pitch in pitches:
                        pitches[n.pitch] += n.duration
                    else:
                        pitches[n.pitch] = n.duration 

            max_freq = 0   
            max_pitch = -1

            for k, v in pitches.iteritems():
                if v > max_freq:
                    max_freq = v
                    max_pitch = k

            chord = 12 - (math.fabs((max_pitch % 12) - key))
            #chord = math.ceil(((max_pitch % 12) - key) / 2)
            chord_progression.append(chord)

    return chord_progression

def to_abstract_melody(melody, curr_chord):
    # returns note representations
    pass 

def get_category(melody):
    pass

if __name__ == "__main__":
    phrase_transitions = dict()
    abstract_note_to_pitch = dict()
    category_to_abstract_melodies = dict()
    train(sys.argv[1], phrase_transitions, abstract_note_to_pitch, category_to_abstract_melodies)