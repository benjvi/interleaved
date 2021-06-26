#!/usr/bin/env python3
from pydub import AudioSegment
from pydub.silence import split_on_silence
from pydub.utils import mediainfo
from os import makedirs
from os.path import exists
import sys
import argparse
import re
import pprint
import glob

# TODO: proper arg parsing or a config file
base_lang = "English"
base_lang_code = "EN"

target_lang = "Spanish"
target_lang_code = "ES"

class LangChunk:

    def __init__(self, audio_segment, lang_title, **kwargs):
        self.segment = audio_segment
        self.lang_title = lang_title
        self.src_idx = kwargs.pop("src_idx", None)


class DualLangSection:

    def __init__(self, base_start_chunk, tgt_start_chunk, base_end_chunk, tgt_end_chunk):
        self.base_start = base_start_chunk
        self.base_end = base_end_chunk
        self.tgt_start = tgt_start_chunk
        self.tgt_end = tgt_end_chunk

    def __repr__(self):
        return "Base start {} , Base end {}, tgt start {}, target end {}".format(self.base_start, self.base_end, self.tgt_start, self.tgt_end)

    def __str__(self):
        return "Base start {} , Base end {}, tgt start {}, target end {}".format(self.base_start, self.base_end, self.tgt_start, self.tgt_end)

def create_audio_chunks(audio_segment, min_chunk_length, max_chunk_length,title,
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
    return [LangChunk(x,title,src_idx=i) for i, x in enumerate(chunks[discard_initial_chunks:])]

def load_audio_chunks(chunkdir, title, lang_title):
    print("Searching for chunks with: {}/*-{}-*.mp3".format(chunkdir, title))
    # chunks need to be loaded in order !
    # our chunks are outputted with chunk number prefix (formatted for lexical sorting), so lexical order
    chunk_files = sorted(glob.glob("{}/*-{}-*.mp3".format(chunkdir, title)))
    print("Found {} chunk files".format(len(chunk_files)))
    print("Loading chunk files..", end=' ')
    chunks=[]
    for file in chunk_files:
        chunk_segment = AudioSegment.from_mp3(file)
        pattern = '.*-([0-9]+).mp3'
        m = re.match(pattern, file)
        idx = int(m.group(1))
        print(idx , end=' ')
        chunks.append(LangChunk(chunk_segment, lang_title, src_idx=idx))
    print("... Finished!")
    return chunks


def interleave_matching_audio_segments(base_lang_chunks, tgt_lang_chunks):
    tgt_lang_duration = sum(chunk.segment.duration_seconds for chunk in tgt_lang_chunks)
    print("{} audio length in seconds: {}".format(target_lang, tgt_lang_duration))

    base_lang_duration = sum(chunk.segment.duration_seconds for chunk in base_lang_chunks)
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
    progress_fudge_factor = tgt_lang_avg_chunk_duration / ( tgt_lang_duration * 4 )

    tgt_lang_play_time = tgt_lang_chunks[0].segment.duration_seconds
    base_lang_play_time = base_lang_chunks[0].segment.duration_seconds
    lang_chunks = []
    base_lang_idx = -1
    tgt_lang_idx = -1
    out_idx = 0

    # loop until all chunks have been added, from both audio tracks
    while base_lang_idx < len(base_lang_chunks) - 1 or tgt_lang_idx < len(tgt_lang_chunks) - 1:
        out_idx += 1
        print(".")

        # projected progress, including the next chunk length in each audio track
        tgt_lang_progress = float(tgt_lang_play_time) / tgt_lang_duration
        base_lang_progress = float(base_lang_play_time) / base_lang_duration

        print("{} play time is now: {}, progress: {}".format(target_lang_code, tgt_lang_play_time, tgt_lang_progress))
        print("{} play time is now: {}, progress: {}".format(base_lang_code, base_lang_play_time, base_lang_progress))

        # always start off with the target lang
        if tgt_lang_idx == -1:
            tgt_lang_idx += 1

            print("Appending {} chunk number {}, of length {}".format(target_lang_code, tgt_lang_idx, tgt_lang_chunks[tgt_lang_idx].segment.duration_seconds))
            print("{} play time is now: {}, progress: {}".format(target_lang_code, tgt_lang_play_time, tgt_lang_progress))

            lang_chunks.append(tgt_lang_chunks[0])
            if tgt_lang_idx+1 < len(tgt_lang_chunks):
                tgt_lang_play_time += tgt_lang_chunks[tgt_lang_idx + 1].segment.duration_seconds

        # when do we want to take the base chunk?
        # if target lang progress exceeds the base lang by a certain amount already ("fudge factor"), take the base lang chunk to catch up
        # otherwise if all target lang chunks have already been added
        elif tgt_lang_progress - progress_fudge_factor > base_lang_progress \
                or tgt_lang_idx >= len(tgt_lang_chunks) - 1:
            base_lang_idx += 1
            if base_lang_idx < len(base_lang_chunks):
                print("Appending {} chunk number {}, of length {}".format(base_lang_code, base_lang_idx, base_lang_chunks[base_lang_idx].segment.duration_seconds))
                print("{} play time is now: {}, progress: {}".format(base_lang_code, base_lang_play_time, base_lang_progress))

                lang_chunks.append(base_lang_chunks[base_lang_idx])
                if base_lang_idx+1 < len(base_lang_chunks):
                    # want calculation of progress in the next iteration to be the projected progress if another base chunk is chosen
                    base_lang_play_time += base_lang_chunks[base_lang_idx + 1].segment.duration_seconds
            else:
                print("Reached last {} chunk in audio".format(base_lang_code))
        # otherwise, we normally want to make progress with the target language first
        else:
            tgt_lang_idx += 1
            if tgt_lang_idx < len(tgt_lang_chunks):
                print("Appending {} chunk number {}, of length {}".format(target_lang_code, tgt_lang_idx, tgt_lang_chunks[tgt_lang_idx].segment.duration_seconds))
                print("{} play time is now: {}, progress: {}".format(target_lang_code, tgt_lang_play_time, tgt_lang_progress))

                lang_chunks.append(tgt_lang_chunks[tgt_lang_idx])
                if (tgt_lang_idx+1 < len(tgt_lang_chunks)):
                    # want calculation of progress in the next iteration to be the projected progress if another target chunk is chosen
                    tgt_lang_play_time += tgt_lang_chunks[tgt_lang_idx + 1].segment.duration_seconds
            else:
                print("Reached last {} chunk in audio section".format(target_lang_code))

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

def export_raw_audio_chunks(raw_chunks, chunkdir, title, lang_code):
    for chunk in raw_chunks:
        idx_str = str(chunk.src_idx).zfill(len(str(len(raw_chunks))))
        bilingual_audio = AudioSegment.empty()
        bilingual_audio += chunk.segment
        bilingual_audio.export("{}/{}/{}-{}-{}.mp3".format(chunkdir, lang_code, idx_str, title, chunk.src_idx),
                               format="mp3",
                               tags={"album": "{}-{}".format(title, lang_code),
                                     "artist": "bv-interleaved-audio",
                                     "title": "{}-{}-{}".format(idx_str, title, chunk.src_idx),
                                     "track": idx_str
                                     },
                               )
    print("Exported {} raw audio chunks".format(lang_code))

def create_sections_from_sync_points(sync_points, num_base_chunks, num_tgt_chunks):
    if sync_points is None or len(sync_points) == 0:
        return None
    # NB 0:0 or end:end cannot be added as a sync point

    sections = []
    # sync points should be a list of tuples, but we get it as two ints separated by a colon
    for i, point in enumerate(sync_points):
        m = re.match(r'([0-9]+):([0-9]+)', point)
        # why +1?  array slicing is exclusive, but we want it inclusive - so we're synced after the specified points
        base_end = int(m.group(1)) + 1
        tgt_end = int(m.group(2)) + 1
        if i == 0:
            base_start = 0
            tgt_start = 0
        else:
            # array slicing end index is exclusive, next section starts with the end index
            base_start = sections[i-1].base_end
            tgt_start = sections[i-1].tgt_end
        sections.append(DualLangSection(base_start, tgt_start, base_end, tgt_end))

    # add extra section to capture the remaining audio after the final sync point
    sections.append(DualLangSection(sections[-1].base_end, sections[-1].tgt_end, num_base_chunks, num_tgt_chunks))

    [validate_section(x) for x in sections]

    return sections


def validate_section(section):
    print("validating section: ")
    pprint.pprint(section)
    assert section.base_start < section.base_end
    assert section.tgt_start < section.tgt_end


def main():
    parser = argparse.ArgumentParser(description='Split two audio files into chunks by utterances and interleave corresponding chunks')
    parser.add_argument('--base-audio',  type=str,
                        help='Audio file whose chunks will trail the target audio. Suggested to be in a language you already know)')
    parser.add_argument('--base-offset', type=int, default=0,
                        help='Discard this number of chunks on the base audio file')
    parser.add_argument('--target-audio', type=str,
                        help='Audio file whose chunks will be placed first. Suggested to be in the language you want to know')
    parser.add_argument('--target-offset', type=int, default=0,
                        help='Discard this number of chunks on the target audio file')
    parser.add_argument('--chunkdir', type=str,
                        help='Directory to output raw chunked audio from the two audio input tracks before any interleaving is done')
    parser.add_argument('--outdir', type=str,
                        help='Directory to output created files to')
    parser.add_argument('--title', type=str,
                        help='Title with which to label output files')
    # TODO: sync points has to be used with a specific, known silence level used for splitting
    parser.add_argument('--base-audio-silence-threshold', type=int, default=-37,
                        help='Silence level that will be used to split the base audio')
    parser.add_argument('--target-audio-silence-threshold', type=int, default=-37,
                        help='Silence level that will be used to split the target audio')
    parser.add_argument('--sync-points', type=str, nargs='+',
                        help='List of pairs of chunk indexes, to force syncing at a specific point in the two audio tracks'
                             'Audio will be synced at the end of the specified chunks, '
                             'Use this to fine tune the output. '
                             'Specify each index pair as a separate argument, with the format: "<base_chunk_index>:<tgt_chunk_index>". '
                             'Sync points must be specified *in order*')
    args = parser.parse_args()

    target_audio = args.target_audio
    base_audio = args.base_audio

    title = args.title
    base_offset = args.base_offset
    target_offset = args.target_offset
    base_audio_silence_threshold = args.base_audio_silence_threshold
    target_audio_silence_threshold = args.target_audio_silence_threshold
    sync_points = args.sync_points

    outdir = args.outdir
    if not exists(outdir):
        makedirs(outdir, exist_ok=True)

    chunkdir = args.chunkdir
    base_chunkdir="{}/{}".format(chunkdir, base_lang_code)
    target_chunkdir="{}/{}".format(chunkdir, target_lang_code)
    base_lang_chunks=None
    target_lang_chunks=None
    if chunkdir is not None:
        if not exists(base_chunkdir):
            makedirs(base_chunkdir, exist_ok=True)
        if not exists(target_chunkdir):
            makedirs(target_chunkdir, exist_ok=True)
        # try to load any existing chunks
        base_lang_chunks = load_audio_chunks(base_chunkdir, title, base_lang)
        print("Loaded {} chunks in base lang {} from {}".format(len(base_lang_chunks), base_lang, base_chunkdir))
        target_lang_chunks = load_audio_chunks(target_chunkdir, title, target_lang)
        print("Loaded {} chunks in target lang {} from {}".format(len(target_lang_chunks), target_lang, target_chunkdir))

    # Generate chunks in case we weren't able to load them
    if base_lang_chunks is None or len(base_lang_chunks) == 0:
        # TODO: can parallelise both by chapter and chunk generation in base/tgt
        base_lang_audio_segment = AudioSegment.from_mp3(base_audio)
        print("Creating chunks for base language")
        base_lang_chunks = create_audio_chunks(base_lang_audio_segment, 5, 15, base_lang, initial_silence_thresh=base_audio_silence_threshold,
                                               discard_initial_chunks=base_offset)
        export_raw_audio_chunks(base_lang_chunks, chunkdir, title, base_lang_code)

    if target_lang_chunks is None or len(target_lang_chunks) == 0:
        tgt_lang_audio_segment = AudioSegment.from_mp3(target_audio)
        print("Creating chunks for target language")
        target_lang_chunks = create_audio_chunks(tgt_lang_audio_segment, 5, 15, target_lang, initial_silence_thresh=target_audio_silence_threshold,
                                              discard_initial_chunks=target_offset)
        export_raw_audio_chunks(target_lang_chunks, chunkdir, title, target_lang_code)

    #
    sync_sections = create_sections_from_sync_points(sync_points, len(base_lang_chunks), len(target_lang_chunks))
    if sync_sections is None or len(sync_sections) == 0:
        all_lang_chunks = interleave_matching_audio_segments(
            base_lang_chunks, target_lang_chunks)
    else:
        all_lang_chunks = []
        print("{} sync points found, going to interleave {} sections in sequence", len(sync_points), len(sync_sections))
        for i, section in enumerate(sync_sections):
            print("Starting to interleave chunks for section {}, starting from {}:{}, finishing at {}:{}".format(
                i,
                section.base_start,section.tgt_start,
                section.base_end,section.tgt_end))

            all_lang_chunks += interleave_matching_audio_segments(
                base_lang_chunks[section.base_start:section.base_end], target_lang_chunks[section.tgt_start:section.tgt_end])

            print("Finished interleaving chunks for section {} (from {}:{} to {}:{})".format(
                i,
                section.base_start,section.tgt_start,
                section.base_end,section.tgt_end))

    export_each_audio_chunk(all_lang_chunks, outdir, title, base_lang_code, target_lang_code)

if __name__ == '__main__':
    main()
