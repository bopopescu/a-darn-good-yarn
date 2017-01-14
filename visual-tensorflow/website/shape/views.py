# Controller for viewing shape 

from collections import defaultdict
import json
from natsort import natsorted
import os
import pandas as pd
from flask import Flask, Response, request, render_template

from shape import app
from core.predictions.utils import smooth

VIDEOS_PATH = 'shape/static/videos/'

title2vidpath = {}
format2titles = defaultdict(list)
title2format = {}

# Used for initial curve to display
cur_format = None
cur_title = None
cur_pd_df = None
cur_vid_framepaths = None

#################################################################################################
# PREDICTION FUNCTIONS 
#################################################################################################
def get_preds_from_df(df, window_len=48):
    """Return smoothed preds: each key is the label, value is list of frame-wise predictions"""
    if len(df.columns) == 2:     # sent_biclass -> just show positive
        preds = {'pos': list(smooth(df.pos.values, window_len=window_len))}
    else:
        preds = {}
        for c in df.columns:
            preds[c] = list(smooth(df[c].values, window_len=window_len))
    return preds

#################################################################################################
# INITIAL SETUP
#################################################################################################
def get_all_vidpaths_with_preds():
    """
    Return list of full paths to every video directory that contains predictions
    e.g. [<VIDEOS_PATH>/@Animated/@OldDisney/Feast/, ...]
    """
    vidpaths = []
    for root, dirs, files in os.walk(VIDEOS_PATH):
        if ('frames' in os.listdir(root)) and ('preds' in os.listdir(root)):
            vidpaths.append(root)
    return vidpaths

def get_cur_vid_framepaths():
    global cur_vid_framepaths, cur_title
    cur_vid_framepaths = [f for f in os.listdir(os.path.join(title2vidpath[cur_title], 'frames')) if \
            not f.startswith('.')]
    cur_vid_framepaths = [os.path.join(title2vidpath[cur_title].split(VIDEOS_PATH)[1], 'frames', f) for \
        f in cur_vid_framepaths]
    cur_vid_framepaths = natsorted(cur_vid_framepaths)
    return cur_vid_framepaths

def setup_initial_data():
    """
    Return initial data to pass to template. 
    Also set global variables cur_pd_df and cur_title
    """
    global title2vidpath, format2titles, title2format, \
        cur_format, cur_title, cur_pd_df, cur_vid_framepaths

    vidpaths = get_all_vidpaths_with_preds()
    format2titles = defaultdict(list)
    for vp in vidpaths:
        format = vp.split(VIDEOS_PATH)[1].split('/')[0].rstrip('s')     # shape/static/videos/shorts/shortoftheweek/Feast -> short
        t = os.path.basename(vp)
        title2format[t] = format
        format2titles[format].append(t)
        title2vidpath[t] = vp
    for format, titles in format2titles.items():
        format2titles[format] = sorted(titles)

    # Get information for first video to show
    # cur_format = format2titles.keys()[0]
    cur_format = 'film'
    cur_title = format2titles[cur_format][0]
    cur_pd_df = pd.read_csv(os.path.join(title2vidpath[cur_title], 'preds', 'sent_biclass.csv'))
    cur_vid_framepaths = get_cur_vid_framepaths()   # full paths to relative paths because js has relative path starting from videos/

    print 'done'

#################################################################################################
# ROUTING FUNCTIONS 
#################################################################################################
@app.route('/shape', methods=['GET'])
def shape():
    """Main shape template with initial data"""
    global format2titles, cur_pd_df, cur_vid_framepaths
    cur_vid_preds = get_preds_from_df(cur_pd_df, window_len=300)    # Window_len has to match default in html file

    data = {'format2titles': format2titles, 'framepaths': cur_vid_framepaths, 'preds': cur_vid_preds}
    # format2titles to create dropdowns in dat.gui
    # framepaths to display image for current video
    # preds to create graph for current video

    return render_template('plot_shape.html', data=json.dumps(data))

@app.route('/api/pred/<title>/<window_len>', methods=['GET'])
def get_preds_and_frames(title, window_len):
    """Return predictions for a given movie with window_len, update global vars"""
    global title2vidpath, \
        cur_format, cur_title, cur_pd_df, cur_vid_framepaths
    if title != cur_title:
        cur_format = title2format[title]
        cur_title = title
        cur_pd_df = pd.read_csv(os.path.join(title2vidpath[cur_title], 'preds', 'sent_biclass.csv'))
        cur_vid_framepaths = get_cur_vid_framepaths()

    preds = get_preds_from_df(cur_pd_df, window_len=int(window_len))
    data = {'preds': preds, 'framepaths': cur_vid_framepaths}

    return Response(
        json.dumps(data),
        mimetype='application/json',
        headers={
            'Cache-Control': 'no-cache',
            'Access-Control-Allow-Origin': '*'
        }
    )

setup_initial_data()
