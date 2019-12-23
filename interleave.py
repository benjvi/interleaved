#!/usr/bin/env python3
from pydub import AudioSegment
from pprint import pprint
from pydub.silence import split_on_silence
from os import makedirs
from os.path import exists
import sys

base_lang = "English"
target_lang = "Spanish"
base_lang_code = "EN"
target_lang_code = "ES"
base_lang_title = "the-little-prince"
target_lang_title = "el-principito"
base_lang_chapter = "chapter"
target_lang_chapter = "capitulo"


class LangChunk:

    def __init__(self, audio_segment, lang_title, **kwargs):
        self.segment = audio_segment
        self.lang_title = lang_title
        self.lang_chapter = kwargs.pop("lang_chapter", None)
        self.chapter_num = kwargs.pop("chapter_num", None)
        self.src_idx = kwargs.pop("src_idx", None)


def interleave_matching_audio_segments(base_segment, tgt_segment):
    # Target lang data
    tgt_lang_chunks = split_on_silence(tgt_lang_audio_segment, min_silence_len=900, silence_thresh=-46, keep_silence=900)
    print("{} chunks: {}".format(target_lang, len(tgt_lang_chunks)))
    tgt_lang_duration = sum(chunk.duration_seconds for chunk in tgt_lang_chunks)
    print("{} audio length in seconds: {}".format(target_lang, tgt_lang_duration))

    # base lang data
    base_lang_chunks = split_on_silence(base_lang_audio_segment, min_silence_len=900, silence_thresh=-46, keep_silence=900)
    print("{} chunks: {}".format(base_lang, len(base_lang_chunks)))
    base_lang_duration = sum(chunk.duration_seconds for chunk in base_lang_chunks)
    print("{} audio length in seconds: {}".format(base_lang, base_lang_duration))

    # because translations and emphasis is different between readings and languages,
    # two audio tracks won't make uniform progress through the track
    # we add a fudge factor
    # - a constant percentage by which the target language progress should remain ahead of the base language progress
    # atm this needs to be adjusted with the length of the target lang audio
    # makes sense to have this about the same size as average chunk length
    # this should have the effect of consolidating chunks that are too short
    # N.B. float division here
    tgt_lang_avg_chunk_duration = tgt_lang_duration / len(tgt_lang_chunks)
    progress_fudge_factor = tgt_lang_avg_chunk_duration / (tgt_lang_audio_segment.duration_seconds * 2.0)

    tgt_lang_play_time = tgt_lang_chunks[0].duration_seconds
    base_lang_play_time = base_lang_chunks[0].duration_seconds
    interleaved_audio = AudioSegment.empty()
    lang_chunks = []
    base_lang_idx = -1
    tgt_lang_idx = -1
    out_idx = 0
    while base_lang_idx < len(base_lang_chunks) - 1 or tgt_lang_idx < len(tgt_lang_chunks) - 1:
        out_idx += 1
        print(".")

        # projected progress, including the next chunk length in each audio track
        tgt_lang_progress = float(tgt_lang_play_time) / tgt_lang_duration
        base_lang_progress = float(base_lang_play_time) / base_lang_duration

        print("{} play time is now: {}, progress: {}".format(target_lang_code, tgt_lang_play_time, tgt_lang_progress))
        print("{} play time is now: {}, progress: {}".format(base_lang_code, base_lang_play_time, base_lang_progress))

        # always start off with the target lang - the one we want to learn
        if tgt_lang_idx == -1:
            tgt_lang_idx += 1

            print("Appending {} chunk number {}, of length {}".format(target_lang_code, tgt_lang_idx, tgt_lang_chunks[tgt_lang_idx].duration_seconds))
            print("{} play time is now: {}, progress: {}".format(target_lang_code, tgt_lang_play_time, tgt_lang_progress))

            lang_chunks.append(LangChunk(tgt_lang_chunks[0], target_lang, src_idx=0))
            if tgt_lang_idx+1 < len(tgt_lang_chunks):
                tgt_lang_play_time += tgt_lang_chunks[tgt_lang_idx + 1].duration_seconds

        # if target lang progress exceeds the base lang by a large amount already, take the base lang chunk to catch up
        elif tgt_lang_progress - progress_fudge_factor > base_lang_progress or tgt_lang_idx >= len(tgt_lang_chunks) - 1:
            base_lang_idx += 1
            if base_lang_idx < len(base_lang_chunks):
                print("Appending {} chunk number {}, of length {}".format(base_lang_code, base_lang_idx, base_lang_chunks[base_lang_idx].duration_seconds))
                print("{} play time is now: {}, progress: {}".format(base_lang_code, base_lang_play_time, base_lang_progress))

                lang_chunks.append(LangChunk(base_lang_chunks[base_lang_idx], base_lang, src_idx=base_lang_idx))
                if base_lang_idx+1 < len(base_lang_chunks):
                    # want calculation of progress in the next iteration to be the projected progress if another base chunk is chosen
                    base_lang_play_time += base_lang_chunks[base_lang_idx + 1].duration_seconds
            else:
                print("Reached last {} chunk in chapter".format(base_lang_code))
        # otherwise, we normally want to make progress with the target language first
        else:
            tgt_lang_idx += 1
            if tgt_lang_idx < len(tgt_lang_chunks):
                print("Appending {} chunk number {}, of length {}".format(target_lang_code, tgt_lang_idx, tgt_lang_chunks[tgt_lang_idx].duration_seconds))
                print("{} play time is now: {}, progress: {}".format(target_lang_code, tgt_lang_play_time, tgt_lang_progress))

                lang_chunks.append(LangChunk(tgt_lang_chunks[tgt_lang_idx], target_lang, src_idx=tgt_lang_idx))
                if (tgt_lang_idx+1 < len(tgt_lang_chunks)):
                    # want calculation of progress in the next iteration to be the projected progress if another target chunk is chosen
                    tgt_lang_play_time += tgt_lang_chunks[tgt_lang_idx + 1].duration_seconds
            else:
                print("Reached last {} chunk in chapter".format(target_lang_code))

    return lang_chunks


base_audio_path = sys.argv[1]
tgt_audio_path = sys.argv[2]
outdir = sys.argv[3]
# outdir = "output/{}-{}-{}-test".format(fluent_lang_title, fluent_lang_code, learning_lang_code)

if not exists(outdir):
    makedirs(outdir, exist_ok=True)

# TODO: can parallelise both by chapter and chunk generation in FR/ES
# TODO: removed for loop, readd it in a way that makes sense on server
# for chapter_num in range(1, 2): #28

base_lang_audio_segment = AudioSegment.from_mp3(base_audio_path)
tgt_lang_audio_segment = AudioSegment.from_mp3(tgt_audio_path)

lang_chunks = interleave_matching_audio_segments(base_lang_audio_segment, tgt_lang_audio_segment)

bilingual_audio = AudioSegment.empty()
for chunk in lang_chunks:
    bilingual_audio += chunk.segment
print("Exporting interleaved audio")
bilingual_audio += AudioSegment.silent(duration=3000)
bilingual_audio.export("{}/audio-out.mp3".format(outdir), format="mp3", tags={"album": "output-audio-{}-{}".format(base_lang_code, target_lang_code), "artist": "bv", "title": "audio-out"})
print("Exported interleaved audio")

