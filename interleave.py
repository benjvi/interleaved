#!/usr/bin/env python3
from pydub import AudioSegment
from pydub.silence import split_on_silence
from os import makedirs
from os.path import exists
import sys

# TODO: proper arg parsing or a config file
base_lang = "English"
base_lang_code = "EN"

target_lang = "Spanish"
target_lang_code = "ES"

base_lang_title = "100-years-of-solitude-ch-1"
# target_lang_title = "el-principito"

discard_initial_chunks_base = 6
discard_initial_chunks_target = 5


class LangChunk:

    def __init__(self, audio_segment, lang_title, **kwargs):
        self.segment = audio_segment
        self.lang_title = lang_title
        self.src_idx = kwargs.pop("src_idx", None)


def create_audio_chunks(audio_segment, min_chunk_length, max_chunk_length,
                        initial_silence_thresh=-46, thresh_incr_size=3,
                        discard_initial_chunks=0):
    silence_thresh = initial_silence_thresh
    attempts = 0
    chunks = []
    max_attempts = 15
    # TODO: binary search / bisection with sensible initial range may be faster
    while attempts < max_attempts:
        attempts += 1
        print("Attempt #{}".format(attempts))
        chunks = split_on_silence(audio_segment, min_silence_len=900, silence_thresh=silence_thresh, keep_silence=900)
        if len(chunks) == 0:
            # we didn't manage to split the audio at all
            # try again with a louder threshold
            print("Chunks: {} with silence threshold {}db".format(len(chunks), silence_thresh))
            silence_thresh = silence_thresh + thresh_incr_size
            continue
        print("Chunks: {}".format(len(chunks)))
        duration = sum(chunk.duration_seconds for chunk in chunks)
        print("Audio length in seconds: {}".format(duration))
        avg_chunk_duration = duration / len(chunks)
        print("Avg chunk duration : {} sec with silence threshold {}db".format(avg_chunk_duration, silence_thresh))

        # if chunks are too long then we have to have a louder silence threshold, so more is considered silence
        # and so more splitting is done
        if avg_chunk_duration > max_chunk_length:
            silence_thresh = silence_thresh + thresh_incr_size
        # if chunks are too short then we should have a lower silence threshold in order to split less
        elif avg_chunk_duration < min_chunk_length:
            silence_thresh = silence_thresh - thresh_incr_size
        elif attempts >= max_attempts:
            print("Max attempts to find best chunk length exceeded, continuing with what we have")
        # success!
        else:
            print("Successfully chunked the audio with average length {}, more than min desired {} sec, and less than "
                  "max desired {} sec".format(
                avg_chunk_duration, min_chunk_length, max_chunk_length))
            break
    return chunks[discard_initial_chunks:]


def interleave_matching_audio_segments(base_lang_chunks, tgt_lang_chunks):
    tgt_lang_duration = sum(chunk.duration_seconds for chunk in tgt_lang_chunks)
    print("{} audio length in seconds: {}".format(target_lang, tgt_lang_duration))

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
                print("Reached last {} chunk in audio".format(base_lang_code))
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
                print("Reached last {} chunk in audio".format(target_lang_code))

    return lang_chunks


def export_bilingual_audio_track(lang_chunks, outdir):
    bilingual_audio = AudioSegment.empty()
    for chunk in lang_chunks:
        bilingual_audio += chunk.segment
    print("Exporting interleaved audio")
    bilingual_audio += AudioSegment.silent(duration=3000)
    bilingual_audio.export("{}/audio-out.mp3".format(outdir),
                           format="mp3",
                           tags={"album": "output-audio-{}-{}".format(base_lang_code, target_lang_code), "artist": "bv", "title": "audio-out"})
    print("Exported interleaved audio")


def export_each_audio_chunk(lang_chunks, outdir, base_lang_title, base_lang_code, target_lang_code):
    idx = 0
    for chunk in lang_chunks:
        idx += 1
        idx_str = str(idx).zfill(len(str(len(lang_chunks))))
        bilingual_audio = AudioSegment.empty()
        bilingual_audio += chunk.segment
        bilingual_audio.export("{}/{}-{}-{}.mp3".format(outdir, idx_str, chunk.lang_title, chunk.src_idx),
                               format="mp3",
                               tags={"album": "{}-{}-{}".format(base_lang_title, base_lang_code, target_lang_code),
                                     "artist": "bv-interleaved-audio",
                                     "title": "{}-{}-{}-{}".format(idx_str, base_lang_title,
                                                                   chunk.lang_title, chunk.src_idx),
                                     "track": idx_str
                                     },
                               )
    print("Exported interleaved audio")


base_audio_path = sys.argv[1]
tgt_audio_path = sys.argv[2]
outdir = sys.argv[3]
# outdir = "output/{}-{}-{}-test".format(fluent_lang_title, fluent_lang_code, learning_lang_code)

if not exists(outdir):
    makedirs(outdir, exist_ok=True)

# TODO: can parallelise both by chapter and chunk generation in FR/ES
base_lang_audio_segment = AudioSegment.from_mp3(base_audio_path)
print("Creating chunks for base language")
base_lang_chunks = create_audio_chunks(base_lang_audio_segment, 5, 15, initial_silence_thresh=-37,
                                       discard_initial_chunks=discard_initial_chunks_base)

tgt_lang_audio_segment = AudioSegment.from_mp3(tgt_audio_path)
print("Creating chunks for target language")
tgt_lang_chunks = create_audio_chunks(tgt_lang_audio_segment, 5, 15, initial_silence_thresh=-37,
                                      discard_initial_chunks=discard_initial_chunks_target)

# TODO: removed for loop, readd it in a way that makes sense on server
# for chapter_num in range(1, 2): #28
all_lang_chunks = interleave_matching_audio_segments(base_lang_chunks, tgt_lang_chunks)

export_each_audio_chunk(all_lang_chunks, outdir, base_lang_title, base_lang_code, target_lang_code)

