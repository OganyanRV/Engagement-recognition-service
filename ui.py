import logging
import random
import threading
import time

from utils_nms import nms

import av
import numpy as np
import streamlit as st
import torch
from streamlit_webrtc import webrtc_streamer


CLIENT_STATUS_UPDATE_PERIOD = 1
CLIENT_FPS_UPDATE_PERIOD = 0.5
MODEL_UPDATE_PERIOD = 0.01

@st.cache_data(show_spinner='Loading model...')
def load_model():
    return torch.hub.load('ultralytics/yolov5', 'custom', path='yolov5/best_yolo5s.pt', force_reload=True)
 
model = load_model()

status_lock = threading.Lock()
fps_lock = threading.Lock()
status = {'in': 0, 'out': 0}
fps = 0

previous_update = None


def video_frame_callback(frame):
    global status, previous_update, fps

    img = frame.to_ndarray(format="bgr24")
    predict_time_start = time.monotonic()
    results = model(img)
    predict_time_stop = time.monotonic()
    
    
    results.pred = nms(results.pred, iou_thr=0.5)

    rendered_frame = np.squeeze(results.render())

    if not previous_update:
        previous_update = time.monotonic()

    if time.monotonic() - previous_update > MODEL_UPDATE_PERIOD:        
        engaged_count, disengaged_count = 0,0
        for box in results.pred:
            if box.nelement() == 0:
                break
            class_ = box[0][-1].item() - 15
            if class_ == 1:
                engaged_count +=1
            else:
                disengaged_count +=1
        
        with status_lock:
            status['in'] += engaged_count
            status['out'] += disengaged_count
            
        with fps_lock:
            fps = round(1./(predict_time_stop-predict_time_start))

        previous_update = time.monotonic()

    return av.VideoFrame.from_ndarray(rendered_frame, format="bgr24")


ctx = webrtc_streamer(
    key="sample", 
    video_frame_callback=video_frame_callback, 
    media_stream_constraints={
        "video" : True,
#         "video": {"width": {"min": 1280, "max": 1280 },
#                   "height": {"min": 720, "max": 720 }
#                  }, 
        "audio": False,
        # "frameRate": {"ideal": 30}},
#         "width": {"min": 1280, "max": 1280 },
#         "height": {"min": 720, "max": 720 }
        }, 
    video_html_attrs={
        "controls": False,
        "autoPlay": True,
    },
)

fps_text = st.empty()
status_text = st.empty()

client_previous_status_update = time.monotonic()
client_previous_fps_update = time.monotonic()

current_status = None
current_fps = None

while ctx.state.playing:
    status_updated = False
    fps_updated = False
    if time.monotonic() - client_previous_status_update > CLIENT_STATUS_UPDATE_PERIOD:
        with status_lock:
            current_status = status
            status_updated = True
            status = {'in': 0, 'out': 0}
        client_previous_status_update = time.monotonic()
    if time.monotonic() - client_previous_fps_update > CLIENT_FPS_UPDATE_PERIOD:
        with fps_lock:
            current_fps = fps 
            fps_updated = True
        client_previous_fps_update = time.monotonic()

    if status_updated:
        if current_status:
            if current_status['in'] != current_status['out']:
                if current_status['in'] > current_status['out']:
                    status_str = 'вовлечен'
                elif current_status['in'] < current_status['out']:
                    status_str = 'не вовлечен'
            else:
                if current_status['in'] == 0 and current_status['out'] == 0:
                    status_str = 'неизвестно'
                else:
                    status_str = None
                
            if status_str:            
                status_text.text(f'Статус: {status_str}')
            status_updated = False
    
    if fps_updated:
        if current_fps:
            fps_text.text(f'FPS: {current_fps}')
            fps_updated = False

    time.sleep(min(CLIENT_STATUS_UPDATE_PERIOD, CLIENT_FPS_UPDATE_PERIOD))
    