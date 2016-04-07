#!/usr/bin/python3
# -*- coding: utf-8 -*-
from __future__ import division, print_function, unicode_literals

import io
import time
import threading
import picamera
from PIL import Image
import os
from dmx import DmxBus

# Create a pool of image processors
done = False
lock = threading.Lock()
pool = []
dmx_bus = DmxBus()


class ImageProcessor(threading.Thread):
    def __init__(self):
        super(ImageProcessor, self).__init__()
        self.stream = io.BytesIO()
        self.event = threading.Event()
        self.terminated = False
        self.start()

    def run(self):
        # This method runs in a separate thread
        global done
        while not self.terminated:
            # Wait for an image to be written to the stream
            if self.event.wait(1):
                try:
                    self.stream.seek(0)
                    # Read the image and do some processing on it
                    image = Image.open(self.stream).convert('RGB')
                    r, g, b = image.getpixel((320, 240))
                    dmx_bus.set_channels({1: r, 2: b, 3: g})
                    # Set done to True if you want the script to terminate
                    # at some point
                    #done=True
                finally:
                    # Reset the stream and event
                    self.stream.seek(0)
                    self.stream.truncate()
                    self.event.clear()
                    # Return ourselves to the pool
                    with lock:
                        pool.append(self)


def streams():
    while not done:
        with lock:
            if pool:
                processor = pool.pop()
            else:
                processor = None
        if processor:
            yield processor.stream
            processor.event.set()
        else:
            # When the pool is starved, wait a while for it to refill
            time.sleep(0.1)


# Shut down the processors in an orderly fashion
def shutdown():
    while pool:
        with lock:
            processor = pool.pop()
        processor.terminated = True
        processor.join()

with picamera.PiCamera() as camera:
    pool = [ImageProcessor() for i in range(4)]
    camera.resolution = (640, 480)
    camera.framerate = 30
    camera.start_preview()
    time.sleep(2)
    camera.capture_sequence(streams(), use_video_port=True)

shutdown()
