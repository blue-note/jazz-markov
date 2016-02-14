import midi
import pykov
import sys
import random
from itertools import cycle

# specify filename on command line

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
    global_structure[0]["num_pitch_tuples"] = 0
    global_structure[0]["num_duration_tuples"] = 0

    global_structure[1]["pitch_chain"] = pykov.Chain()
    global_structure[1]["duration_chain"] = pykov.Chain()
    global_structure[1]["notes_and_rests_chain"] = pykov.Chain()
    global_structure[1]["num_pitch_tuples"] = 0
    global_structure[1]["num_duration_tuples"] = 0

    global_structure[2]["pitch_chain"] = pykov.Chain()
    global_structure[2]["duration_chain"] = pykov.Chain()
    global_structure[2]["notes_and_rests_chain"] = pykov.Chain()
    global_structure[2]["num_pitch_tuples"] = 0
    global_structure[2]["num_duration_tuples"] = 0

    # for now, assume even first-order transition probability from note to rest and rest to note

    global_structure[0]["notes_and_rests_chain"][('N','R')] = 0.5
    global_structure[0]["notes_and_rests_chain"][('R','N')] = 0.5
    global_structure[1]["notes_and_rests_chain"][('N','R')] = 0.5
    global_structure[1]["notes_and_rests_chain"][('R','N')] = 0.5
    global_structure[2]["notes_and_rests_chain"][('N','R')] = 0.5
    global_structure[2]["notes_and_rests_chain"][('R','N')] = 0.5

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
            global_structure[curr_third]["num_duration_tuples"] += 1
        return curr_duration

    def save_pitch_transition(prev_note, curr_note):
        global_structure[curr_third]["pitch_chain"][(prev_note, note)] += 1
        global_structure[curr_third]["num_pitch_tuples"] += 1

    while curr_third < 3:
        event = next(iterTrack)
        if type(event) is midi.events.EndOfTrackEvent:
            break
        note = event.data[0]
        velocity = event.data[1]

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

    #print global_structure
    #print total_ticks
    generate(global_structure, 16, 1920)


def roundtoEighth(x, prec=3, base=0.125):
    return round(base * round(float(x)/base), prec)

def generate(global_structure, beats_per_third, ticks_per_measure):
    # generate melody
    measures_so_far = 0
    curr_third = 0
    pitch_chain = global_structure[curr_third]["pitch_chain"]
    duration_chain = global_structure[curr_third]["duration_chain"]
    notes_and_rests_chain = global_structure[curr_third]["notes_and_rests_chain"]

    # generated walks
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

    	prev_note = step(prev_note, pitch_chain)
    	prev_duration = step(prev_duration, duration_chain)
    	prev_note_type = step(prev_note_type, notes_and_rests_chain)

    	pitch_walk.append(prev_note)
    	duration_walk.append(prev_duration)
    	notes_and_rests_walk.append(prev_note_type)

    	measures_so_far += prev_duration

    	if measures_so_far >= 4:
         curr_third += 1
         measures_so_far = 0


    # generate midi file

    pattern = midi.Pattern(resolution=480)
    track = midi.Track()

    # OLD MIDI GEN LOOP

    # get starting state

    # prev_note = pitch_walk[0]
    # prev_num_ticks = duration_walk[0] * ticks_per_measure
    # prev_note_type = notes_and_rests_walk[0]

    # for i in xrange(1, len(pitch_walk)):
    # 	curr_note_type = notes_and_rests_walk[i]
    # 	curr_duration = duration_walk[i]
    # 	curr_num_ticks = int(curr_duration * ticks_per_measure)
    # 	curr_note = pitch_walk[i]

    # 	if prev_note_type == 'N' and curr_note_type == 'N':
    # 		track.append(midi.NoteOnEvent(tick=curr_num_ticks, data=[curr_note, 80]))
    # 		track.append(midi.NoteOffEvent(tick=curr_num_ticks, data=[curr_note, 80]))
    # 		prev_num_ticks = 0

    # 	elif prev_note_type == 'R' and curr_note_type == 'N':
    # 		#print type(curr_num_ticks)
    # 		track.append(midi.NoteOnEvent(tick=curr_num_ticks, data=[curr_note, 80]))
    # 		track.append(midi.NoteOffEvent(tick=curr_num_ticks, data=[curr_note, 80]))

    # 	if prev_note_type == 'R' and curr_note_type == 'R':
    # 		prev_num_ticks += curr_num_ticks

    # 	else:
    # 		prev_num_ticks = curr_num_ticks

    # 	prev_note = curr_note
    # 	prev_note_type = curr_note_type


    # NEW MIDI GEN LOOP

    prev_num_ticks = 0 # rest tick count
    total_num_ticks = 0

    for i in xrange(len(pitch_walk)):
        curr_note_type = notes_and_rests_walk[i]
        curr_duration = duration_walk[i]
        curr_num_ticks = int(curr_duration * ticks_per_measure) # tick count for this note
        total_num_ticks += curr_num_ticks
        curr_note = pitch_walk[i]

        if curr_note_type == 'N':
            track.append(midi.NoteOnEvent(tick=prev_num_ticks, data=[curr_note, 80]))
            track.append(midi.NoteOffEvent(tick=curr_num_ticks, data=[curr_note, 80]))
            prev_num_ticks = 0

        elif curr_note_type == 'R':
            prev_num_ticks += curr_num_ticks

    track.append(midi.EndOfTrackEvent(tick=1))
    pattern.append(track)
    print total_num_ticks
    midi.write_midifile("testing.mid", pattern)

def step(state, chain):
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

def test():
	# Instantiate a MIDI Pattern (contains a list of tracks)
	pattern = midi.Pattern()
	# Instantiate a MIDI Track (contains a list of MIDI events)
	track = midi.Track()
	# Append the track to the pattern
	pattern.append(track)
	# Instantiate a MIDI note on event, append it to the track
	on = midi.NoteOnEvent(tick=0, velocity=20, pitch=midi.G_3)
	track.append(on)
	# Instantiate a MIDI note off event, append it to the track
	off = midi.NoteOffEvent(tick=100, pitch=midi.G_3)
	track.append(off)
	# Add the end of track event, append it to the track
	eot = midi.EndOfTrackEvent(tick=1)
	track.append(eot)
	# Print out the pattern
	print pattern
	# Save the pattern to disk
	midi.write_midifile("example.mid", pattern)

if __name__ == "__main__":
	train(sys.argv[1])
	#test()