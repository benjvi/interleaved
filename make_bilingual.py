#!/usr/bin/env python
from pydub import AudioSegment
from pprint import pprint
from pydub.silence import split_on_silence
from os import mkdir
from os.path import exists
import sys

fluent_lang = "English"
learning_lang = "Spanish"
fluent_lang_code = "EN"
learning_lang_code = "ES"
fluent_lang_title = "the-little-prince"
learning_lang_title = "el-principito"
fluent_lang_chapter = "chapter"
learning_lang_chapter = "capitulo"

in_audio_base_path = sys[0]
in_audio_tgt_path = sys[1]
outdir = sys.argv[2]
# outdir = "output/{}-{}-{}-test".format(fluent_lang_title, fluent_lang_code, learning_lang_code)

if not exists(outdir):
    mkdir(outdir)

# because transaltions and emphasis is different between readings and languages, two audio tracks won't make uniform progress through the track
# we add a fudge factor - a constant percentage by which the foreign language progress should remain ahead of the home language progress
PROGRESS_FUDGE_FACTOR=0.10

# TODO: can parallelise both by chapter and chunk generation in FR/ES
# TODO: removed for loop, readd it in a way that makes sense on server
# for chapter_num in range(1, 2): #28
print("Processing chapter {}".format(chapter_num))
# SPANISH
chapter = AudioSegment.from_mp3(in_audio_base_path)
es_chunks = split_on_silence(chapter, silence_thresh=-46, keep_silence=100)
print("{} chunks: {}".format(learning_lang, len(es_chunks)))
es_duration = sum(chunk.duration_seconds for chunk in es_chunks)
print("{} audio length in seconds: {}".format(learning_lang, es_duration))

# FRENCH
chapter = AudioSegment.from_mp3(in_audio_tgt_path))
fr_chunks = split_on_silence(chapter, min_silence_len=900, silence_thresh=-46, keep_silence=100)
print("{} chunks: {}".format(fluent_lang, len(fr_chunks)))
fr_duration = sum(chunk.duration_seconds for chunk in fr_chunks)
print("{} audio length in seconds: {}".format(fluent_lang, fr_duration))

es_progress = 0
fr_progress = 0
es_play_time = es_chunks[0].duration_seconds
fr_play_time = fr_chunks[0].duration_seconds
bilingual_audio = AudioSegment.empty()
fr_idx = -1
es_idx = -1
while (fr_idx < len(fr_chunks)-1 or es_idx < len(es_chunks)-1):
    print(".")
    # make sure we are making more progress through the book in spanish (always want to encounter spanish text first)
    es_progress = float(es_play_time)/es_duration
    fr_progress = float(fr_play_time)/fr_duration
    print("{} play time is now: {}, progress: {}".format(learning_lang_code, es_play_time, es_progress))
    print("{} play time is now: {}, progress: {}".format(fluent_lang_code, fr_play_time, fr_progress))
    if es_idx == -1:
        es_idx += 1
        print("Appending {} chunk number {}, of length {}".format(learning_lang_code, es_idx, es_chunks[es_idx].duration_seconds))
        print("{} play time is now: {}, progress: {}".format(learning_lang_code, es_play_time, es_progress))
        bilingual_audio += es_chunks[0]
        es_play_time += es_chunks[es_idx+1].duration_seconds
    elif (es_progress-PROGRESS_FUDGE_FACTOR > fr_progress or es_idx >= len(es_chunks)-1):
        fr_idx += 1
        if fr_idx < len(fr_chunks):
            print("Appending {} chunk number {}, of length {}".format(fluent_lang_code, fr_idx, fr_chunks[fr_idx].duration_seconds))
            print("{} play time is now: {}, progress: {}".format(fluent_lang_code, fr_play_time, fr_progress))
            bilingual_audio += fr_chunks[fr_idx]
            if (fr_idx+1 < len(fr_chunks)):
                # want calculation of progress in the next iteration to be the projected progress if another FR chunk is chosen
                fr_play_time += fr_chunks[fr_idx+1].duration_seconds
        else:
            print("Reached last {} chunk in chapter".format(fluent_lang_code))
    else:
        es_idx += 1
        if es_idx < len(es_chunks):
            print("Appending {} chunk number {}, of length {}".format(learning_lang_code, es_idx, es_chunks[es_idx].duration_seconds))
            print("{} play time is now: {}, progress: {}".format(learning_lang_code, es_play_time, es_progress))
            bilingual_audio += es_chunks[es_idx]
            if (es_idx+1 < len(es_chunks)):
                # want calculation of progress in the next iteration to be the projected progress if another ES chunk is chosen
                es_play_time += es_chunks[es_idx+1].duration_seconds
        else:
            print("Reached last {} chunk in chapter".format(learning_lang_code))
bilingual_audio += AudioSegment.silent(duration=3000)
bilingual_audio.export("{}/audio-out.mp3", format="mp3", tags={"album": "output-audio-{}-{}".format(fluent_lang_code, learning_lang_code), "artist": "bv", "title": "audio-out"})
