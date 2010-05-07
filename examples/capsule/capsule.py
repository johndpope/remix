#!/usr/bin/env python
# encoding: utf=8

"""
capsule.py
accepts songs on the commandline, order them, beatmatch them, and output an audio file
"""
import os
import sys
from optparse import OptionParser

from echonest.action import render, make_stereo
from echonest.audio import LocalAudioFile
from echonest.cloud_support import AnalyzedAudioFile

from capsule_support import order_tracks, equalize_tracks, resample_features, timbre_whiten, initialize, make_transition, terminate, FADE_OUT, display_actions, is_valid
from utils import tuples


def do_work(audio_files, options):

    inter = float(options.inter)
    trans = float(options.transition)
    order = bool(options.order)
    equal = bool(options.equalize)
    verbose = bool(options.verbose)
    
    # Get pyechonest/remix objects
    analyze = lambda x : AnalyzedAudioFile(x) if os.path.exists(x + '.json') else LocalAudioFile(x)
    tracks = map(analyze, audio_files)
    
    # decide on an initial order for those tracks
    if order == True:
        if verbose: print "Ordering tracks..."
        tracks = order_tracks(tracks)
    
    if equal == True:
        equalize_tracks(tracks)
        if verbose:
            print
            for track in tracks:
                print "Vol = %.0f%%\t%s" % (track.sound_check*100.0, track.analysis.name)
            print
    
    valid = []
    # compute resampled and normalized matrices
    for track in tracks:
        if verbose: print "Resampling", track.analysis.name
        track.resampled = resample_features(track, rate='beats')
        track.resampled['matrix'] = timbre_whiten(track.resampled['matrix'])
        # remove tracks that are too small
        if is_valid(track, inter, trans):
            valid.append(track)
        # for compatibility, we make mono tracks stereo
        track = make_stereo(track)
    tracks = valid
    
    # Initial transition. Should contain 2 instructions: fadein, and playback.
    if verbose: print "Computing transitions..."
    start = initialize(tracks[0], inter, trans)
    
    # Middle transitions. Should each contain 2 instructions: crossmatch, playback.
    middle = []
    [middle.extend(make_transition(t1, t2, inter, trans)) for (t1, t2) in tuples(tracks)]
    
    # Last chunk. Should contain 1 instruction: fadeout.
    end = terminate(tracks[-1], FADE_OUT)
    
    return start + middle + end

def get_options(warn=False):
    usage = "usage: %s [options] <list of mp3s>" % sys.argv[0]
    parser = OptionParser(usage=usage)
    parser.add_option("-t", "--transition", default=8, help="transition (in seconds) default=8")
    parser.add_option("-i", "--inter", default=8, help="section that's not transitioning (in seconds) default=8")
    parser.add_option("-o", "--order", action="store_true", help="automatically order tracks")
    parser.add_option("-e", "--equalize", action="store_true", help="automatically adjust volumes")
    parser.add_option("-v", "--verbose", action="store_true", help="show results on screen")        
    parser.add_option("-p", "--pdb", default=True, help="dummy; here for not crashing when using nose")
    
    (options, args) = parser.parse_args()
    if warn and len(args) < 2: 
        parser.print_help()
    return (options, args)
    
def main():
    options, args = get_options(warn=True);
    
    #try:
    actions = do_work(args, options)
    #except:
    #    print "Error computing capsule!"
    #    return -1
    
    if bool(options.verbose) == True:
        display_actions(actions)
    print "Output Duration = %.3f sec" % sum(act.duration for act in actions)
    
    # Send to renderer
    print "Rendering..."
    render(actions, 'capsule.mp3')
    return 1
    
if __name__ == "__main__":
    sys.exit(main())