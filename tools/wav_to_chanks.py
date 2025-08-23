from pydub import AudioSegment
import math
import os

input_file = "resources/sounds/minotaur/footsteps/loud-footsteps-1.wav"  
output_dir = "resources/sounds/minotaur/footsteps/"
chunk_duration_ms = 600  # 0.6 seconds

os.makedirs(output_dir, exist_ok=True)
audio = AudioSegment.from_wav(input_file)
total_chunks = math.ceil(len(audio) / chunk_duration_ms)

for i in range(total_chunks):
    start = i * chunk_duration_ms
    end = min((i + 1) * chunk_duration_ms, len(audio))
    chunk = audio[start:end]
    chunk.export(f"{output_dir}/chunk_{i+1}.wav", format="wav")
print(f"Split into {total_chunks} files.")