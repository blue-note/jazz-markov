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

       def __gt__(self, n):
        return self.start > n.start

       def __str__(self):
        return "type: " + self.note_type + "\n" + "pitch: " + str(self.pitch) + "\n" + "duration: " + str(self.duration) + " \n"

class Event: 

    # on or off events with absolute tick

    def __init__(self, tipe, start, end, pitch):
        self.type = tipe
        self.start = start
        self.end = end
        self.pitch = pitch

    def __gt__(self, e):
        return self.tick > e.tick


def train(input_file, category_transitions, abstract_note_to_note, category_to_abstract_melodies):
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
    chord_progression = get_chord_progression(bassline, piano, ticks_per_measure, key)
    for c in chord_progression:
        print c
        
    chord_progression = iter(get_chord_progression(bassline, piano, ticks_per_measure, key))

    # FOR TESTING

    # chord_progression = iter([0, 0, 14, 21, 0, 14, 7, 21, 0, 0, 14, 21]) # change_short
    # chord_progression = iter([0, 0, 14]) # change_shortest
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

    measures = get_measures(melody, ticks_per_measure)

    # for e in measures:
        # print " ".join(str(a.pitch) for a in e)
        # print '\n'

    for j in range(len(measures)):
        m = measures[j]
        curr_chord = next(chord_progression)
        if curr_chord != -1:
            abstract_melody = to_abstract_melody(m, curr_chord, key, ticks_per_measure)
            # if j == 4:
            #     print " ".join(str(n) for n in m)
            abstract_melody.append(j)
            for i in range(len(abstract_melody)-1):
                p = m[i].pitch
                n = (p + 12 - key) % 12 # note relative to key
                t = abstract_melody[i][0]
                # print abstract_melody[i]
                if (t, n) in abstract_note_to_note[curr_chord]:
                    abstract_note_to_note[curr_chord][(t,n)] += 1
                else:
                    abstract_note_to_note[curr_chord][(t,n)] = 1
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
            prev_category = curr_category    

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
                notes.append(Note(-1, event.tick, 'R', ticks_so_far-event.tick, ticks_so_far))

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

def get_measures(track, ticks_per_measure):
    notes = get_notes(track)
    notes.sort()
    measure_count = 0
    measures = list()
    current_measure = list()
    carry_over = list()
    note = notes[0]
    i = 1

    while i < len(notes):
        start = measure_count * ticks_per_measure
        end = (measure_count + 1) * ticks_per_measure

        while note.start < end and i < len(notes):
            if note.end <= end:
                current_measure.append(note)
            else:
                remainder = note.end - end
                carry_over.append(Note(note.pitch, remainder, note.note_type, end, note.end))
                note.end -= remainder
                current_measure.append(note) 
            
            
            note = notes[i]
            i += 1

        measures.append(current_measure)
        j = i-1
        a = j # first carried over note is at index a in notes
        carried = False
        for el in carry_over:
            carried = True
            notes.insert(j, el)
            j += 1
        current_measure = list()
        carry_over = list()
        measure_count += 1
        if carried:
            note = notes[a]
            i = a + 1

    return measures

def get_chord_progression(bass, piano, ticks_per_measure, key):
    key = key % 12 # account for minor keys
    bass_measures = get_measures(bass, ticks_per_measure)
    piano_measures = get_measures(piano, ticks_per_measure)

    # for el in bass_measures:
    #     print " ".join(str(n.pitch) for n in el)


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
                        if note.note_type != 'R':
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
                        if note.note_type != 'R':
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

def to_abstract_melody(melody, c, key, ticks_per_measure):
    # returns note representations relative to chord

    chord_tones = list()
    abstract_melody = list()
    minor = c >= 12
    c = c % 12
    key = key % 12
    if minor:
        chord_tones = [c, c+3, c+7, c+10]
    else:
        chord_tones = [c, c+4, c+7, c+11]
    
    color_tones = [c+2, c+5, c+9]
    approach_tones = [c+6, c+8]

    for note in melody:
        n = (note.pitch + 12 - key) % 12 # get note relative to key

        # start and end relative to this measure
        start = note.start % ticks_per_measure
        end = note.end % ticks_per_measure

        if end == 0: # note ended exactly at end of measure
            end = ticks_per_measure

        start = str(roundG(float(start) / float(ticks_per_measure), 4, .0625))
        end = str(roundG(float(end) / float(ticks_per_measure), 4, .0625))

        
        # start = str(roundtoEighth(note.start, ticks_per_measure))
        # end = str(roundtoEighth(note.end, ticks_per_measure))
        # d = str(roundtoEighth(note.duration, ticks_per_measure))
        if note.note_type == 'R':
            abstract_melody.append('R'+ '-' + start + '-' + end)
        elif n in chord_tones:
            abstract_melody.append('A'+ '-' + start + '-' + end)
        elif n in color_tones:
            abstract_melody.append('B'+ '-' + start + '-' + end)
        elif n in approach_tones:
            abstract_melody.append('C'+ '-' + start + '-' + end)
        else: 
            abstract_melody.append('X'+ '-' + start + '-' + end)

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

def choice(state, chain):
    # return random step based on distribution
     
    successors = get_successors(state, chain) # get normalized dict of successors from state in given chain to their transition probs
    if len(successors) == 0:
        c = random.choice(chain.keys())
        return c[1]

    func = random.uniform
    x = func(0,1)
    res = random.choice(successors.keys())
    keys = successors.keys()
    random.shuffle(keys)
    for state in keys:
        prob = successors[state]
        if x < prob:
            res = state
            break
        x = x - prob
    return res

def get_successors(state, chain):
    # for input state return a dict of successors and their transition probs from the given chain
    res = dict()
    for s, p in chain.iteritems():
        if s[0] == state:
            res[s[1]] = p
    normalize(res)
    return res

def normalize(els):
    # els is dict of states to probabilities
    total_prob = 0
    for k, v in els.iteritems():
        total_prob += v
    for k, v in els.iteritems():
        v = float(v) / float(total_prob)
        els[k] = v

def generate(key, chord_progression, category_transitions, abstract_note_to_note, category_to_abstract_melodies):
    category_walk = list()
    output = list()
    resolution = 480
    ticks_per_measure = resolution * 4
    pattern = midi.Pattern(resolution=resolution)
    track = midi.Track()
    prev_category = random.choice(category_transitions.keys())[random.choice([0, 1])]
    measure_count = 0
    events = list()
    for c in chord_progression:
        # get category based on previous
        curr_category = choice(prev_category, category_transitions)
        melodies = category_to_abstract_melodies[curr_category]
        m = random.choice(melodies)
        prev_category = curr_category
        # print m[len(m)-1]
        # print " ".join(str(el) for el in m)

        ## WITH SIMULTANEOUS NOTES
        for n in m:
            if type(n) is int:
                break
            t = n.split('-')
            if t[0] == 'R':
                continue
            # get start and end in ticks relative to current measure
            start = int(float(t[1]) * ticks_per_measure)
            end = int(float(t[2]) * ticks_per_measure)

            # get absolute start and end in ticks
            measure_start = ticks_per_measure * measure_count
            start = start + measure_start
            end = end + measure_start
            rel_note = choice(t[0], abstract_note_to_note[c]) # choose note relative to key that corresponds to abstract note
            pitch = ((rel_note + key) % 12) + 36


            #print pitch
            # events.append(Event('On', start, pitch))
            # events.append(Event('Off', start+50, pitch))

            events.append(Event('On', start, end, pitch))
            events.append(Event('Off', start, end, pitch))
        
        measure_count += 1
        #print measure_count

        # generate midi track

    #events.sort()

    last_tick = 0 # absolute tick count

    for e in events:
        # print e.end - e.start
        if e.type == 'On':
            #track.append(midi.NoteOnEvent(tick=e.tick-last_tick, data=[e.pitch, 80]))
            track.append(midi.NoteOnEvent(tick=e.start-last_tick, data=[e.pitch, 80]))
            last_tick = e.start
        else:
            #track.append(midi.NoteOffEvent(tick=e.tick-last_tick, data=[e.pitch, 80]))
            track.append(midi.NoteOffEvent(tick=e.end-last_tick, data=[e.pitch, 80]))
            last_tick = e.end
        #last_tick = e.tick

    track.append(midi.EndOfTrackEvent(tick=1))
    pattern.append(track)
    midi.write_midifile("out.mid", pattern)


def test(ifile):
    ticks_so_far = 0
    pattern = midi.read_midifile(ifile)
    metadata = pattern[0]
    melody = pattern[1]
    piano = pattern[2]
    bassline = pattern[3]
    key_code = -1
    beats_per_measure = -1
    ticks_per_measure = -1  

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

    chord_progression = get_chord_progression(bassline, piano, ticks_per_measure, key)
    # for c in chord_progression:
    #     print c


    # for n in notes: 
    #     print n.pitch
    measures = get_measures(melody, ticks_per_measure)



    # for el in measures:
    #     print " ".join(str(n.pitch) + ": " + str(n.start) + "-" + str(n.end) for n in el)

    # # for el in measures:
    #     print " ".join(str(n.pitch) + " " for n in el)

    #print len(measures)

    # for i in range(len(measures)):
    #     print "     ".join(to_abstract_melody(measures[i], chord_progression[i], key, ticks_per_measure))



if __name__ == "__main__":
    category_transitions = dict()
    abstract_note_to_note = dict()
    for i in range(0, 25):
        abstract_note_to_note[i] = dict()
    category_to_abstract_melodies = dict()
    rootdir = "/Users/janitachalam/Documents/Amherst/SENIOR/Thesis/jazz_markov_code/training_phase_2"
    if not sys.argv:
        for subdir, dirs, files in os.walk(rootdir):
            for f in files:
                train(os.path.join(rootdir, f), category_transitions, abstract_note_to_note, category_to_abstract_melodies)
    else:
        train(sys.argv[1], category_transitions, abstract_note_to_note, category_to_abstract_melodies)
    input_chords = [21, 0, 21, 0, 14, 14, 21, 0, 16, 5, 21, 0]
    input_chords = [0, 0] # change_shortest
    input_chords = [0, 0, 5, 21, 0, 5, 21, 0, 0, 0, 5, 21, 0, 5, 21]
    input_chords = [14, 0, 14, 14, 12, 7, 0, 0, 14, 0, 14]
    input_chords = [0, 0, 14, 21, 0, 14, 7, 21, 0, 0, 14, 21] 
    input_chords = [0, 0, 5, 21, 0, 5, 21, 0, 0, 0, 5, 21] # change_short
    input_chords = [0, 0, 0, 0, 0, 8] # basin
    input_chords = [21, 0, 21, 0, 14, 14, 21, 0]
    input_chords = [0, 0, 0, 0]
    input_key = 0
    generate(input_key, input_chords, category_transitions, abstract_note_to_note, category_to_abstract_melodies)