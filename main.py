import midi
import pykov
import sys
import random
from itertools import cycle
import shelve
import os

def train(inputfile):

    # inputfile is one-track midi file, 12-bar blues progression in C, 4/4

    pattern = midi.read_midifile(inputfile)
    track = pattern[len(pattern)-1] # skip the metadata
    total_num_measures = 12
    beats_per_measure = 4 # later get this from metatdata in first track in pattern
    ticks_per_measure = pattern.resolution * beats_per_measure
    ticks_per_third = (total_num_measures / 3) * ticks_per_measure
    ticks_so_far = 0
    total_ticks = 0

    # chains

    global_structure = dict()
    global_structure[0] = dict()
    global_structure[1] = dict()
    global_structure[2] = dict()

    global_structure[0]["pitch_chain"] = pykov.Chain()
    global_structure[0]["duration_chain"] = pykov.Chain()
    global_structure[0]["notes_and_rests_chain"] = pykov.Chain()

    global_structure[1]["pitch_chain"] = pykov.Chain()
    global_structure[1]["duration_chain"] = pykov.Chain()
    global_structure[1]["notes_and_rests_chain"] = pykov.Chain()

    global_structure[2]["pitch_chain"] = pykov.Chain()
    global_structure[2]["duration_chain"] = pykov.Chain()
    global_structure[2]["notes_and_rests_chain"] = pykov.Chain()

    # for now, assume even first-order transition probability from note to rest and rest to note

    global_structure[0]["notes_and_rests_chain"][('N','R')] = 0.25
    global_structure[0]["notes_and_rests_chain"][('N', 'N')] = 0.25
    global_structure[0]["notes_and_rests_chain"][('R','N')] = 0.25
    global_structure[0]["notes_and_rests_chain"][('R', 'R')] = 0.25

    global_structure[1]["notes_and_rests_chain"][('N','R')] = 0.25
    global_structure[1]["notes_and_rests_chain"][('N', 'N')] = 0.25
    global_structure[1]["notes_and_rests_chain"][('R','N')] = 0.25
    global_structure[1]["notes_and_rests_chain"][('R', 'R')] = 0.25

    global_structure[2]["notes_and_rests_chain"][('N','R')] = 0.25
    global_structure[2]["notes_and_rests_chain"][('N', 'N')] = 0.25
    global_structure[2]["notes_and_rests_chain"][('R','N')] = 0.25
    global_structure[2]["notes_and_rests_chain"][('R', 'R')] = 0.25

    # create cycle on track, iterate through while counting ticks, note the current note and the following as tuples
    # assume there are no simultaneous notes

    iterTrack = iter(track)
    curr_third = 0
    prev_note = -1
    prev_duration = -1
    prev_note_type = -1

    def save_duration_transition(prev_duration, curr_tick):
        fraction_of_measure = float(curr_tick) / float(ticks_per_measure)
        curr_duration = roundtoEighth(fraction_of_measure) # convert note duration to multiple of eigth note (0.125)
        if prev_duration > 0.0 and curr_duration > 0.0:
            global_structure[curr_third]["duration_chain"][(prev_duration, curr_duration)] += 1
        return curr_duration

    def save_pitch_transition(prev_note, curr_note):
        global_structure[curr_third]["pitch_chain"][(prev_note, note)] += 1

    while curr_third < 3:
        event = next(iterTrack)
        if type(event) is midi.events.EndOfTrackEvent:
            break
        if type(event) is midi.events.NoteOnEvent or type(event) is midi.NoteOffEvent:
            note = event.data[0]
            velocity = event.data[1]
        else:
            continue

        if type(event) is midi.events.NoteOnEvent and velocity != 0:
            if prev_note != -1:
                save_pitch_transition(prev_note, note)

            # transition probability from last rest (if exists) to current note
            if prev_duration != -1 and event.tick > 0:
                prev_duration = save_duration_transition(prev_duration, event.tick)

            prev_note = note
            ticks_so_far += event.tick
            total_ticks += event.tick

        elif type(event) is midi.events.NoteOffEvent or velocity == 0:
            # calculate note duration & increment tick
            if prev_note != -1 and event.tick > 0:
                prev_duration = save_duration_transition(prev_duration, event.tick)
                ticks_so_far += event.tick
                total_ticks += event.tick

        if ticks_so_far >= ticks_per_third:
            curr_third += 1
            ticks_so_far = 0

    d = shelve.open("training_data")
    try:
        d["global_structure"] = to_dict(global_structure)
    finally: 
        d.close()

def roundtoEighth(x, prec=3, base=0.125):

    return round(base * round(float(x)/base), prec)

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

def generate():

    # get training data from disk

    d = shelve.open("training_data")
    try:
        global_structure = to_pykov_chains(d["global_structure"])
    finally: 
        d.close()

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

    prev_note = choice(pitch_chain.steady())
    prev_duration = choice(duration_chain.steady())
    prev_note_type = choice(notes_and_rests_chain.steady())

    while curr_third < 3:

        pitch_chain = global_structure[curr_third]["pitch_chain"]
        duration_chain = global_structure[curr_third]["duration_chain"]
        notes_and_rests_chain = global_structure[curr_third]["notes_and_rests_chain"]

        prev_note = step(prev_note, pitch_chain, 'P')
        prev_duration = step(prev_duration, duration_chain, 'D')
        prev_note_type = step(prev_note_type, notes_and_rests_chain, 'N')

        pitch_walk.append(prev_note)
        duration_walk.append(prev_duration)
        notes_and_rests_walk.append(prev_note_type)

        measures_so_far += prev_duration

        if measures_so_far >= 4:
         curr_third += 1
         measures_so_far = 0

    # generate midi file

    pattern = midi.Pattern(resolution=resolution)
    track = midi.Track()

    prev_num_ticks = 0 # rest tick count

    for i in xrange(len(pitch_walk)):
        curr_note_type = notes_and_rests_walk[i]
        curr_duration = duration_walk[i]
        curr_num_ticks = int(curr_duration * ticks_per_measure) # tick count for this note
        curr_note = pitch_walk[i]

        if curr_note_type == 'N':
            track.append(midi.NoteOnEvent(tick=prev_num_ticks, data=[curr_note, 80]))
            track.append(midi.NoteOffEvent(tick=curr_num_ticks, data=[curr_note, 80]))
            prev_num_ticks = 0

        elif curr_note_type == 'R':
            prev_num_ticks += curr_num_ticks

    track.append(midi.EndOfTrackEvent(tick=1))
    pattern.append(track)
    midi.write_midifile("testing5.mid", pattern)

def step(state, chain, chaintype):
    successors = get_successors(state, chain)
    if len(successors) == 0:
        c = random.choice(chain.keys())
        return c[0]
    else:
        return choice(successors)

def get_successors(state, chain):
    # for input state return a dict of successors and their transition probs from the given chain
    res = pykov.Vector()
    for s, p in chain.iteritems():
        if s[0] == state:
            res[s[1]] = p
    res.normalize()
    return res

def choice(successors):
    # return random step based on distribution
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
    train(sys.argv[1])
    generate()