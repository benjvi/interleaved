from pydub import AudioSegment

# gcloud speech api doesn't handle mp3s
song = AudioSegment.from_mp3("C:\\Users\\ben\\Documents\\code\\interleaved-test\\el-principito-capitulo-1.mp3")
song.export("C:\\Users\\ben\\Documents\\code\\interleaved-test\\el-principito-capitulo-1.flac", format="flac", parameters=["-ar", "16000", "-ac", "1"])