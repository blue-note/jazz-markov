import midi
import pykov
import sys
import random
from itertools import cycle
import shelve
import os
import math


class Note:
       def __init__(self, pitch, duration, note_type, start=-1, end=-1):
        # pitch = integer
        # duration = ticks
        # note_type = 'N' or 'R'
        self.pitch = pitch
        self.duration = duration
        self.note_type = note_type
        self.start = start
        self.end = end

       def __gt__(self, note_2):
        return self.start > note_2.start

       def __str__(self):
        return "type: " + self.note_type + "\n" + "pitch: " + str(self.pitch) + "\n" + "duration: " + str(self.duration) + " \n"

def train(input_file, category_transitions, abstract_note_to_pitch, category_to_abstract_melodies):
    ticks_so_far = 0
    pattern = midi.read_midifile(input_file)
    metadata = pattern[0]
    melody = pattern[1]
    piano = pattern[2]
    bassline = pattern[3]
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
        sys.exit("No time or key signature: " + input_file)

    key = get_key(key_code)
    # msrs = get_measures_3(piano, ticks_per_measure)
    # for m in msrs:
    #     print 'MEASURE: '
    #     for n in m:
    #         print n


    chord_progression = iter(get_chords_2(bassline, piano, ticks_per_measure, key))
    # for c in chord_progression:
    #     print c
    #     print "\n"
    # chord_progression = iter([0, 0, 0, 0, 5, 5, 0, 0, 7, 5, 0, 0])

    prev_chord = ""
    curr_category = ""
    prev_category = ""
    curr_phrase = list()
    prev_phrase = list()
    first_next = -1

    ## PHRASE TRANSITION LEARNING

    measures = get_measures_3(melody, ticks_per_measure)

    for m in measures:
        curr_chord = next(chord_progression)
        if curr_chord != -1:
            abstract_melody = to_abstract_melody(m, curr_chord, key, ticks_per_measure)
            for i in range(len(abstract_melody)):
                p = m[i].pitch
                n = (p + 12 - key) % 12 # note relative to key
                t = abstract_melody[i][0]
                if n in abstract_note_to_pitch[curr_chord][t]:
                    abstract_note_to_pitch[curr_chord][t][n] += 1
                else:
                    abstract_note_to_pitch[curr_chord][t][n] = 1
            curr_category = get_category(m)
            if curr_category in category_to_abstract_melodies:
                category_to_abstract_melodies[curr_category].append(abstract_melody)
            else:
                category_to_abstract_melodies[curr_category] = [abstract_melody]
        
            if prev_category != "":
                if (prev_category, curr_category) in category_transitions:
                    category_transitions[(prev_category, curr_category)] += 1
                else:
                    category_transitions[(prev_category, curr_category)] = 1


     ### OLD VERSION ###
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
    #             if ((prev_category, prev_chord), (curr_category, curr_chord)) in category_transitions:
    #                 category_transitions[((prev_category, prev_chord), (curr_category, curr_chord))] += 1
    #             else:
    #                 category_transitions[((prev_category, prev_chord), (curr_category, curr_chord))] = 1

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
    pitch = -1
    velocity = -1
    current_notes = dict() # list current pitches being played to their note objects
    ticks_so_far = 0

    while type(event) != midi.EndOfTrackEvent:
        event = next(iterTrack)
        ticks_so_far += event.tick

        if type(event) is midi.NoteOnEvent or type(event) is midi.NoteOffEvent:
            pitch = event.data[0]
            velocity = event.data[1]
        else:
            continue # bypass meta track events
        if type(event) is midi.NoteOnEvent and velocity != 0: # start of note

            if event.tick > 0 and not current_notes: # register prior rest if no other notes playing
                notes.append(Note(-1, event.tick, 'R'))

            n = Note(pitch, 0, 'N', ticks_so_far)
            current_notes[pitch] = n

        elif type(event) is midi.NoteOffEvent or velocity == 0: # end of note
            if pitch in current_notes:
                n = current_notes[pitch]
                n.duration = ticks_so_far - n.start
                n.end = ticks_so_far
                notes.append(n)
                del current_notes[pitch]

    return notes

def get_measures_3(track, ticks_per_measure):
    notes = get_notes(track)
    notes.sort()
    measure_count = 0
    measures = list()
    current_measure = list()
    carry_over = list()
    i = 0
    note = notes[i]

    while i < len(notes):
        start = measure_count * ticks_per_measure
        end = (measure_count + 1) * ticks_per_measure

        while note.start < end and i < len(notes):
            if note.note_type != 'R':
                if note.end <= end:
                    current_measure.append(note)
                else:
                    remainder = note.end - end
                    carry_over.append(Note(note.pitch, remainder, 'N', end, note.end))
                    note.end -= remainder
                    current_measure.append(note) 
            
            note = notes[i]
            i += 1
        
        measures.append(current_measure)
        j = i
        for el in carry_over:
            notes.insert(j, el)
            j += 1
        current_measure = list()
        carry_over = list()
        measure_count += 1

    return measures


def get_measures(track, ticks_per_measure):
    notes = get_notes(track)
    measures = list()
    ticks_so_far = 0
    current_measure = list()
    carry_over = set()
    total_ticks = 0
    num_measures = 0

    for i in range(len(notes)):
        note = notes[i]
        ticks_so_far += note.start - last_end # relative count (within measure)
        total_ticks = note.start # absolute count
        last_end = 0
        if ticks_so_far + note.duration <= ticks_per_measure:
            if note.note_type != 'R':
                current_measure.append(note)

        
        elif ticks_so_far < ticks_per_measure and ticks_so_far + note.duration > ticks_per_measure:
            if note.note_type != 'R':
                remainder = ticks_so_far + note.duration - ticks_per_measure
                carry_over.add(Note(note.pitch, remainder, 'N', total_ticks+note.duration-remainder, total_ticks+note.duration)) # need absolute start
                note.duration -= remainder
                

        if ticks_so_far >= ticks_per_measure:
            ticks_so_far = ticks_so_far % ticks_per_measure


        else:
            carry_over = set()



            if ticks_so_far > 0: # split note between measures
                first_next = Note(note.pitch, ticks_so_far, note.note_type)
                current_measure[len(current_measure)-1].duration -= ticks_so_far
            else: 
                first_next = -1
            measures.append(current_measure)    
            current_measure = list()
            if first_next != -1:
                current_measure.append(first_next)
    return measures


def get_chords_2(bass, piano, ticks_per_measure, key):
    key = key % 12 # account for minor keys
    bass_measures = get_measures_3(bass, ticks_per_measure)
    piano_measures = get_measures_3(piano, ticks_per_measure)

    # for m in bass_measures:
    #     if len(m) >= 1:
    #         m[0].duration *= 2

    max_length = max(len(bass_measures), len(piano_measures))
    chord_progression = list()

    for j in range(0, max_length): 
        current_measure = list()
        if j < len(bass_measures):
            current_measure += bass_measures[j]
        if j < len(piano_measures):
            current_measure += piano_measures[j]

        max_weight = 0
        matched_chord = -1
        for i in range(0, 23): # iterate through major and minor chords
            o = i 
            i = (i + 12 - key) % 12
            weight = 0

            major = [i, i+2, i+4, i+5, i+7, i+9, i+11]
            minor = [i, i+2, i+3, i+5, i+7, i+8, i+10]

            major = [i, i+4, i+7, i+11]
            minor = [i, i+3, i+7, i+10]

            if o < 12: # major chord
                for chord_tone in major:
                    c = chord_tone % 12
                    for note in current_measure:
                        n = (note.pitch + 12 - key) % 12
                        if n == c:
                            if c == i: # increase weight for matched tonic notes
                                weight += note.duration * 2 # change to duration after simultaneous notes
                            else:
                                weight += note.duration

            else: # minor chord
                for chord_tone in minor:
                    c = chord_tone % 12
                    for note in current_measure:
                        n = (note.pitch + 12 - key) % 12
                        if n == c:
                            if c == i: # increase weight for matched tonic notes
                                weight += note.duration * 2 # change to duration after simultaneous notes
                            else:
                                weight += note.duration

            # if j == 1 and i == 0:
            #     print "2nd measure notes: "
            #     for n in current_measure:
                    #print str((n.pitch + 12 - key) % 12) + ": " + str(roundtoEighth(float(n.duration) / float(ticks_per_measure), ticks_per_measure))
                     # print str((n.pitch + 12 - key) % 12) 
                    #+ ": " + str(n.duration)
            # if i == 8 and j == 0 and o < 12:
            #     print "major 8 chord weight for measure 1: " + str(weight)

            # if i == 0 and o < 12 and j == 0:
            #     print "major 9 chord weight for measure 1: " + str(weight)

            # if j == 1 and o < 12 and i == 0:
            #     print "0th chord weight for measure 2: " + str(weight)
            # if j == 1 and o < 12 and i == 10:
            #     print "7th chord weight for measure 2: " + str(weight)

            # find max matching chord 
            if weight > max_weight:
                max_weight = weight
                if o >= 12:
                    matched_chord = i + 12
                else:
                    matched_chord = i

        chord_progression.append(matched_chord)
        # print "MEASURE"
        # for n in current_measure:
        #     print (n.pitch +12 - key) % 12
        # print '\n'


    return chord_progression


def get_chords(bass, piano, ticks_per_measure, key):
    key = key % 12 # account for minor keys
    notes = get_notes(bass)
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
                minor_chord = False
                o = i
                i = (i + 12 - key) % 12
                weight = 0
                first = -1
                third = -1
                fifth = -1

                major = [i, i+2, i+4, i+5, i+7, i+9, i+10]
                minor = [i, i+2, i+3, i+5, i+7, i+8, i+10]

                major = [i, i+4, i+7, i+11]
                minor = [i, i+3, i+7, i+10]

                if o < 12: # major chord
                    for n in major:
                        if n in current_measure:
                            weight += current_measure[n]

                else: # minor chord
                    minor_chord = True
                    for n in minor:
                        if n in current_measure:
                            weight += current_measure[n]

                # find max matching chord 
                if weight > max_weight:
                    max_weight = weight
                    if minor_chord:
                        matched_chord = i + 12
                    else:
                        matched_chord = i
           
            chord_progression.append(matched_chord)
            current_measure = dict()
            if ticks_so_far > 0 and notes[i].note_type != 'R': # carry over note from last measure
                current_measure[note] = duration 
           
    return chord_progression

def roundtoEighth(x, ticks_per_measure, prec=3, base=0.125):
    fraction_of_measure = float(x) / float(ticks_per_measure)
    res = round(base * round(float(fraction_of_measure)/base), prec)
    if res == 0:
        return 0.125
    else:
        return res

def roundG(x, prec, base):
    return round(base * round(float(x)/float(base)), prec)

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

def to_abstract_melody(melody, c, key, ticks_per_measure):
    # returns note representations relative to chord

    chord_tones = list()
    abstract_melody = list()
    minor = key >= 12
    key = key % 12
    if minor:
        chord_tones = [c, c+3, c+7, c+10]
    else:
        chord_tones = [c, c+4, c+7, c+11]
    
    color_tones = [c+2, c+5, c+9]
    approach_tones = [c+6, c+8]

    for note in melody:
        n = (note.pitch + 12 - key) % 12 # get note relative to key
        d = str(roundtoEighth(note.duration, ticks_per_measure))
        if n in chord_tones:
            abstract_melody.append('A' + d)
        elif n in color_tones:
            abstract_melody.append('B' + d)
        elif n in approach_tones:
            abstract_melody.append('C' + d)
        else: 
            abstract_melody.append('X' + d)

    return abstract_melody

def get_category(melody):
    num_ascending = 0
    num_descending = 0
    for i in range(len(melody) - 1):
        a = melody[i]
        b = melody[i+1]
        if a.pitch <= b.pitch:
            num_ascending += 1
        else: 
            num_descending += 1

    c = roundG(len(melody), 0, 4) # round length of phrase to nearest 4
    r = 2
    if num_descending != 0:
        r = float(num_ascending) / float(num_descending)

    r = roundG(r, 1, 0.5) # round ratio of ascending to descending pairs
    return str(r) + '-' + str(c)

if __name__ == "__main__":
    category_transitions = dict()
    abstract_note_to_pitch = dict()
    for i in range(0, 25):
        abstract_note_to_pitch[i] = dict()
        abstract_note_to_pitch[i]['A'] = dict()
        abstract_note_to_pitch[i]['B'] = dict()
        abstract_note_to_pitch[i]['C'] = dict()
        abstract_note_to_pitch[i]['X'] = dict()
    category_to_abstract_melodies = dict()
    train(sys.argv[1], category_transitions, abstract_note_to_pitch, category_to_abstract_melodies)