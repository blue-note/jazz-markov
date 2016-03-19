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

def train(inputfile, global_structure):

    # inputfile is one-track midi file, 12-bar blues progression in C, 4/4

    pattern = midi.read_midifile(inputfile)
    track = pattern[len(pattern)-1] # skip the metadata
    total_num_measures = 12
    beats_per_measure = 4 # later get this from metatdata in first track in pattern
    ticks_per_measure = pattern.resolution * beats_per_measure
    ticks_per_third = (total_num_measures / 3) * ticks_per_measure
    ticks_so_far = 0

    # create cycle on track, iterate through while counting ticks, note the current note and the following as tuples
    # assume there are no simultaneous notes

    iterTrack = iter(track)
    curr_third = 0
    prev_note = -1
    prev_duration = -1
    prev_note_type = -1

    # for pairwise version

    last_pitch = 0
    last_note_start = 0
    last_note_end = 0
    notes_first = []
    notes_second = []
    notes_third = []
    notes_curr = notes_first

    pitches_first = []
    pitches_second = []
    pitches_third = []
    pitches_curr = pitches_first

    def save_duration_transition(prev_duration, curr_tick):
        ## NO LONGER VALID
        fraction_of_measure = float(curr_tick) / float(ticks_per_measure)
        curr_duration = roundtoEighth(fraction_of_measure) # convert note duration to multiple of eigth note (0.125)
        if prev_duration > 0.0 and curr_duration > 0.0:
            global_structure[curr_third]["duration_chain"][(prev_duration, curr_duration)] += 1
        return curr_duration

    def save_pitch_transition(prev_note, curr_note):
        ## NO LONGER VALID
        global_structure[curr_third]["pitch_chain"][(prev_note, note)] += 1


    def roundtoEighth(x, prec=3, base=0.125):
        fraction_of_measure = float(x) / float(ticks_per_measure)
        res = round(base * round(float(fraction_of_measure)/base), prec)
        if res == 0:
            return 0.125
        else:
            return res

    # digest training melody into notes and rests list

    while curr_third < 3:

        event = next(iterTrack)
        if type(event) is midi.events.EndOfTrackEvent:
            break
        if type(event) is midi.events.NoteOnEvent or type(event) is midi.NoteOffEvent:
            pitch = event.data[0]
            velocity = event.data[1]
        else:
            continue # bypass meta track events

        if type(event) is midi.events.NoteOnEvent and velocity != 0: # start of note

        	###### OLD VERSION

            # if prev_note != -1:
            #     save_pitch_transition(prev_note, note)

            if event.tick > 0:
            	notes_curr.append(Note(-1, event.tick, 'R'))
            ticks_so_far += event.tick

            # transition probability from last rest (if exists) to current note

            ###### OLD VERSION

            # if prev_duration != -1 and event.tick > 0:
            #     prev_duration = save_duration_transition(prev_duration, event.tick)

            # prev_note = note
            # ticks_so_far += event.tick

        elif type(event) is midi.events.NoteOffEvent or velocity == 0: # end of note

        	###### OLD VERSION

            # calculate note duration & increment tick
            # if prev_note != -1 and event.tick > 0:
            #     prev_duration = save_duration_transition(prev_duration, event.tick)
            #     ticks_so_far += event.tick

            n = Note(pitch, event.tick, 'N')
            notes_curr.append(n)
            pitches_curr.append(n)
            ticks_so_far += event.tick

        if ticks_so_far >= ticks_per_third:
            curr_third += 1
            ticks_so_far = 0
            if curr_third == 1:
                notes_curr = notes_second
                pitches_curr = pitches_second
            elif curr_third == 2:
                notes_curr = notes_third
                pitches_curr = pitches_third

    # d = shelve.open("training_data")
    # try:
    #     d["global_structure"] = to_dict(global_structure)
    # finally: 
    #     d.close()


    #### FIRST THIRD

    # LEARN PITCH TRANSITIONS
       # compare each pair to each next pair (with overlapping blocks of four)  

    for i in xrange(0, len(pitches_first)-4):

        # GET 4 PITCHED NOTES
        first = pitches_first[i]
        second = pitches_first[i+1] 
        third = pitches_first[i+2]
        fourth = pitches_first[i+3] 

        if ((first.pitch, second.pitch), (third.pitch, fourth.pitch)) in global_structure[0]["pitch_chain"]:
            global_structure[0]["pitch_chain"][(first.pitch, second.pitch), (third.pitch, fourth.pitch)] += 1
        else:
            global_structure[0]["pitch_chain"][(first.pitch, second.pitch), (third.pitch, fourth.pitch)] = 1

    i += 4
    # LEARN DURATION TRANSITIONS
        # not distinguishing between pitch and rest durations for now

    for i in xrange(0, len(notes_first)-4):

        # GET 4 ANY TYPE NOTES
        first = notes_first[i]
        second = notes_first[i+1] 
        third = notes_first[i+2]
        fourth = notes_first[i+3] 

        if ((first.duration, second.duration), (third.duration, fourth.duration)) in global_structure[0]["duration_chain"]:
            global_structure[0]["duration_chain"][(roundtoEighth(first.duration), roundtoEighth(second.duration)), (roundtoEighth(third.duration), roundtoEighth(fourth.duration))] += 1
        else:
            global_structure[0]["duration_chain"][(roundtoEighth(first.duration), roundtoEighth(second.duration)), (roundtoEighth(third.duration), roundtoEighth(fourth.duration))] = 1
     
        note_type_tuple = ((first.note_type, second.note_type), (third.note_type, fourth.note_type))
        if note_type_tuple in global_structure[0]["notes_and_rests_chain"]:
            global_structure[0]["notes_and_rests_chain"][note_type_tuple] += 1
        else:
             global_structure[0]["notes_and_rests_chain"][note_type_tuple] = 1

    i += 4
    ### SECOND THIRD

    for i in xrange(0, len(pitches_second)-4):

        # GET 4 PITCHED NOTES
        first = pitches_second[i]
        second = pitches_second[i+1] 
        third = pitches_second[i+2]
        fourth = pitches_second[i+3] 

        if ((first.pitch, second.pitch), (third.pitch, fourth.pitch)) in global_structure[1]["pitch_chain"]:
            global_structure[1]["pitch_chain"][(first.pitch, second.pitch), (third.pitch, fourth.pitch)] += 1
        else:
            global_structure[1]["pitch_chain"][(first.pitch, second.pitch), (third.pitch, fourth.pitch)] = 1
    i += 4

    for i in xrange(0, len(notes_second)-4):

        # GET 4 ANY TYPE NOTES
        first = notes_second[i]
        second = notes_second[i+1] 
        third = notes_second[i+2]
        fourth = notes_second[i+3] 

        if ((first.duration, second.duration), (third.duration, fourth.duration)) in global_structure[1]["duration_chain"]:
            global_structure[1]["duration_chain"][(roundtoEighth(first.duration), roundtoEighth(second.duration)), (roundtoEighth(third.duration), roundtoEighth(fourth.duration))] += 1
        else:
            global_structure[1]["duration_chain"][(roundtoEighth(first.duration), roundtoEighth(second.duration)), (roundtoEighth(third.duration), roundtoEighth(fourth.duration))] = 1


        note_type_tuple = ((first.note_type, second.note_type), (third.note_type, fourth.note_type))
        if note_type_tuple in global_structure[1]["notes_and_rests_chain"]:
            global_structure[1]["notes_and_rests_chain"][note_type_tuple] += 1
        else:
             global_structure[1]["notes_and_rests_chain"][note_type_tuple] = 1

    i += 4
    ### LAST THIRD
    for i in xrange(0, len(pitches_third)-4):

        # GET 4 PITCHED NOTES
        first = pitches_third[i]
        second = pitches_third[i+1] 
        third = pitches_third[i+2]
        fourth = pitches_third[i+3] 

        if ((first.pitch, second.pitch), (third.pitch, fourth.pitch)) in global_structure[2]["pitch_chain"]:
            global_structure[2]["pitch_chain"][(first.pitch, second.pitch), (third.pitch, fourth.pitch)] += 1
        else:
            global_structure[2]["pitch_chain"][(first.pitch, second.pitch), (third.pitch, fourth.pitch)] = 1

    i += 4
    for i in xrange(0, len(notes_third)-4):

        # GET 4 ANY TYPE NOTES
        first = notes_third[i]
        second = notes_third[i+1] 
        third = notes_third[i+2]
        fourth = notes_third[i+3] 

        if ((first.duration, second.duration), (third.duration, fourth.duration)) in global_structure[2]["duration_chain"]:
            global_structure[2]["duration_chain"][(roundtoEighth(first.duration), roundtoEighth(second.duration)), (roundtoEighth(third.duration), roundtoEighth(fourth.duration))] += 1
        else:
            global_structure[2]["duration_chain"][(roundtoEighth(first.duration), roundtoEighth(second.duration)), (roundtoEighth(third.duration), roundtoEighth(fourth.duration))] = 1

        note_type_tuple = ((first.note_type, second.note_type), (third.note_type, fourth.note_type))
        if note_type_tuple in global_structure[2]["notes_and_rests_chain"]:
            global_structure[2]["notes_and_rests_chain"][note_type_tuple] += 1
        else:
             global_structure[2]["notes_and_rests_chain"][note_type_tuple] = 1
    i += 4

def to_dict(global_structure):
    global_structure_new = dict()
    for key, chain_dict in global_structure.iteritems():
        all_chains_new = dict() # replaces dict of chain names to chains
        for name, chain in chain_dict.iteritems():
            single_chain_new = dict() # replaces pykov chain
            for t in chain: 
                single_chain_new[t] = chain[t]
            all_chains_new[name] = single_chain_new
        global_structure_new[key] = all_chains_new

    return global_structure_new

def to_pykov_chains(global_structure):
    global_structure_new = dict()
    for key, chain_dict in global_structure.iteritems():
        for name, chain in chain_dict.iteritems():
            chain_dict[name] = pykov.Chain(chain) # replace dict with pykov chain
    return global_structure

def generate(global_structure):

    # get training data from disk

    # d = shelve.open("training_data")
    # try:
    #     global_structure = to_pykov_chains(d["global_structure"])
    # finally: 
    #     d.close()

    # generate melody

    resolution = 480
    ticks_per_measure = resolution * 4
    measures_so_far = 0
    curr_third = 0
    pitch_chain = global_structure[curr_third]["pitch_chain"]
    duration_chain = global_structure[curr_third]["duration_chain"]
    notes_and_rests_chain = global_structure[curr_third]["notes_and_rests_chain"]

    # walks to be generated

    pitch_walk = list()
    duration_walk = list()
    notes_and_rests_walk = list()

    # select starting state based on steady state probabilities

    prev_pitch_pair = random.choice(pitch_chain.keys())[0]
    prev_duration_pair = random.choice(duration_chain.keys())[0]
    prev_note_type_pair = random.choice(notes_and_rests_chain.keys())[0]

    while curr_third < 3:

        pitch_chain = global_structure[curr_third]["pitch_chain"]
        duration_chain = global_structure[curr_third]["duration_chain"]
        notes_and_rests_chain = global_structure[curr_third]["notes_and_rests_chain"]

        prev_pitch_pair = choice(prev_pitch_pair, pitch_chain)
        prev_duration_pair = choice(prev_duration_pair, duration_chain)
        prev_note_type_pair = choice(prev_note_type_pair, notes_and_rests_chain)

        pitch_walk.append(prev_pitch_pair)
        duration_walk.append(prev_duration_pair)
        notes_and_rests_walk.append(prev_note_type_pair)

        measures_so_far += prev_duration_pair[0] + prev_duration_pair[1]

        if measures_so_far >= 4:
         curr_third += 1
         measures_so_far = 0

    # generate midi file

    pattern = midi.Pattern(resolution=resolution)
    track = midi.Track()

    prev_num_ticks = 0 # rest tick count

    for i in xrange(len(pitch_walk)):
        # curr_note_type = notes_and_rests_walk[i]
        curr_duration_pair = duration_walk[i]
        first_duration = curr_duration_pair[0]
        second_duration = curr_duration_pair[1]
        first_num_ticks = int(first_duration * ticks_per_measure) # tick count for this note
        second_num_ticks = int(second_duration * ticks_per_measure) # tick count for this note

        curr_note_type_pair = notes_and_rests_walk[i]
        first_note_type = curr_note_type_pair[0]
        second_note_type = curr_note_type_pair[1]

        curr_pitch_pair = pitch_walk[i]
        first_pitch = curr_pitch_pair[0]
        second_pitch = curr_pitch_pair[1]


        if first_note_type == 'N':
            track.append(midi.NoteOnEvent(tick=prev_num_ticks, data=[first_pitch, 80]))
            track.append(midi.NoteOffEvent(tick=first_num_ticks, data=[first_pitch, 80]))
            prev_num_ticks = 0

        elif first_note_type == 'R':
            prev_num_ticks += first_num_ticks

        if second_note_type == 'N':
            track.append(midi.NoteOnEvent(tick=prev_num_ticks, data=[second_pitch, 80]))
            track.append(midi.NoteOffEvent(tick=second_num_ticks, data=[second_pitch, 80]))
            prev_num_ticks = 0

        elif second_note_type == 'R':
            prev_num_ticks += second_num_ticks


    track.append(midi.EndOfTrackEvent(tick=1))
    pattern.append(track)
    midi.write_midifile("test.mid", pattern)

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

def choice(state, chain):
    # return random step based on distribution
     
    successors = get_successors(state, chain) # get normalized dict of successors from state in given chain to their transition probs
    if len(successors) == 0:
        c = random.choice(chain.keys())
        return c[0]

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

if __name__ == "__main__":

    # chains

    global_structure = dict()
    global_structure[0] = dict()
    global_structure[1] = dict()
    global_structure[2] = dict()

    global_structure[0]["pitch_chain"] = dict()
    global_structure[0]["duration_chain"] = dict()
    global_structure[0]["notes_and_rests_chain"] = dict()

    global_structure[1]["pitch_chain"] = dict()
    global_structure[1]["duration_chain"] = dict()
    global_structure[1]["notes_and_rests_chain"] = dict()

    global_structure[2]["pitch_chain"] = dict()
    global_structure[2]["duration_chain"] = dict()
    global_structure[2]["notes_and_rests_chain"] = dict()

    # for now, assume even first-order transition probability from note to rest and rest to note

    # global_structure[0]["notes_and_rests_chain"][('N','R')] = 0.25
    # global_structure[0]["notes_and_rests_chain"][('N', 'N')] = 0.25
    # global_structure[0]["notes_and_rests_chain"][('R','N')] = 0.25
    # global_structure[0]["notes_and_rests_chain"][('R', 'R')] = 0.25

    # global_structure[1]["notes_and_rests_chain"][('N','R')] = 0.25
    # global_structure[1]["notes_and_rests_chain"][('N', 'N')] = 0.25
    # global_structure[1]["notes_and_rests_chain"][('R','N')] = 0.25
    # global_structure[1]["notes_and_rests_chain"][('R', 'R')] = 0.25

    # global_structure[2]["notes_and_rests_chain"][('N','R')] = 0.25
    # global_structure[2]["notes_and_rests_chain"][('N', 'N')] = 0.25
    # global_structure[2]["notes_and_rests_chain"][('R','N')] = 0.25
    # global_structure[2]["notes_and_rests_chain"][('R', 'R')] = 0.25

    # rootdir = "/Users/janitachalam/Documents/Amherst/SENIOR/Thesis/jazz_markov_code/test_melodies"
    # for subdir, dirs, files in os.walk(rootdir):
    #     for f in files:
            #train(os.path.join(rootdir, f), global_structure) 


    train(sys.argv[1], global_structure)
    #print global_structure
    #print global_structure[0]["notes_and_rests_chain"]
    generate(global_structure)

