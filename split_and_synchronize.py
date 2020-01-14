from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
from collections import Counter

def transcribe_gcs(gcs_uri, language_code):
    """Transcribes the audio file specified by the gcs_uri."""
    client = speech.SpeechClient()

    audio = types.RecognitionAudio(uri=gcs_uri)
    config = types.RecognitionConfig(
        encoding=enums.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=16000,
        language_code=language_code,
        enable_word_time_offsets=True)

    operation = client.long_running_recognize(config, audio)

    print('Waiting for operation to complete...')
    response = operation.result(timeout=120)

    # Each result is for a consecutive portion of the audio. Iterate through
    # them to get the transcripts for the entire audio file.
    for result in response.results:
        # The first alternative is the most likely one for this portion.
        words = [w.word for w in result.alternatives[0].words]
        word_counts = Counter(words)
        print(word_counts)

transcribe_gcs("gs://benjvi-audio-files/el-principito-capitulo-1.flac", "es-MX")