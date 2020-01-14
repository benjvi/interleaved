#!/usr/bin/env python
from pydub import AudioSegment
from datetime import timedelta

audiobook_filename = "the-little-prince-en.mp3"
chapter_segments = [
  (timedelta(seconds=0), timedelta(minutes=3, seconds=8)),
  (timedelta(minutes=3, seconds=8), timedelta(minutes=8, seconds=13)),
  (timedelta(minutes=8, seconds=13), timedelta(minutes=11, seconds=18)),
  (timedelta(minutes=11, seconds=18), timedelta(minutes=16, seconds=32)),
  (timedelta(minutes=16, seconds=32), timedelta(minutes=21, seconds=30)),
  (timedelta(minutes=21, seconds=30), timedelta(minutes=23, seconds=7)),
  (timedelta(minutes=23, seconds=7), timedelta(minutes=28, seconds=37)),
  (timedelta(minutes=28, seconds=37), timedelta(minutes=33, seconds=55)),
  (timedelta(minutes=33, seconds=55), timedelta(minutes=37, seconds=7)), 
  (timedelta(minutes=37, seconds=7), timedelta(minutes=45, seconds=42)), 
  (timedelta(minutes=45, seconds=42), timedelta(minutes=47, seconds=51)), 
  (timedelta(minutes=47, seconds=51), timedelta(minutes=49, seconds=11)), 
  (timedelta(minutes=49, seconds=11), timedelta(minutes=54, seconds=55)), 
  (timedelta(minutes=54, seconds=55), timedelta(minutes=59, seconds=51)), 
  (timedelta(minutes=59, seconds=51), timedelta(hours=1, minutes=5, seconds=47)), 
  (timedelta(hours=1, minutes=5, seconds=47), timedelta(hours=1, minutes=7, seconds=35)), 
  (timedelta(hours=1, minutes=7, seconds=35), timedelta(hours=1, minutes=11, seconds=40)), 
  (timedelta(hours=1, minutes=11, seconds=40), timedelta(hours=1, minutes=12, seconds=34)), 
  (timedelta(hours=1, minutes=12, seconds=34), timedelta(hours=1, minutes=13, seconds=58)), 
  (timedelta(hours=1, minutes=13, seconds=58), timedelta(hours=1, minutes=15, seconds=42)), 
  (timedelta(hours=1, minutes=15, seconds=42), timedelta(hours=1, minutes=25, seconds=22)), 
  (timedelta(hours=1, minutes=25, seconds=22), timedelta(hours=1, minutes=27, seconds=15)), 
  (timedelta(hours=1, minutes=27, seconds=15), timedelta(hours=1, minutes=28, seconds=5)), 
  (timedelta(hours=1, minutes=28, seconds=5), timedelta(hours=1, minutes=33, seconds=18)), 
  (timedelta(hours=1, minutes=33, seconds=18), timedelta(hours=1, minutes=39, seconds=12)), 
  (timedelta(hours=1, minutes=39, seconds=12), timedelta(hours=1, minutes=50, seconds=13)), 
  (timedelta(hours=1, minutes=50, seconds=13), timedelta(hours=1, minutes=57, seconds=37)) 
]

audiobook = AudioSegment.from_mp3("{}".format(audiobook_filename))

for idx, segment in enumerate(chapter_segments, start=1):
  chapter = audiobook[segment[0].total_seconds()*1000:segment[1].total_seconds()*1000]
  chapter.export("the-little-prince/chapter-{}.mp3".format(idx), format="mp3", tags={"album": "The Little Prince", "artist": "bv", "title": "the-little-prince-ch-{}".format(idx)}) 
