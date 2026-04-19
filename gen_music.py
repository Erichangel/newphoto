import os, wave, struct, math, random

MUSIC_DIR = r'K:\Pictures\音乐'
os.makedirs(MUSIC_DIR, exist_ok=True)

NOTE_NAMES = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11,
             'Cm':0,'Dm':2,'Em':4,'Fm':5,'Gm':7,'Am':9,'Bm':11}

def get_freq(note_name, octave=4):
    base = NOTE_NAMES.get(note_name, 0)
    return 440 * (2 ** ((base + (octave - 4) * 12) / 12))

def generate_wav(filepath, bpm, key, duration_sec=25):
    sr = 44100
    total_samples = sr * duration_sec
    beat_len = 60.0 / bpm
    is_minor = key.endswith('m')
    chord_progression = [0, 7, 9, 5, 0, 4, 7, 0]
    bars_per_chord = 4; beats_per_bar = 4
    melody_pentatonic = [0, 2, 4, 7, 9, 7, 4, 2]

    all_data = bytearray()
    sample_idx = 0

    for ci, chord_semi in enumerate(chord_progression):
        root_freq = get_freq(key, 4) * (2 ** (chord_semi / 12))
        third_freq = root_freq * (2 ** (4/12 if not is_minor else 3/12))
        fifth_freq = root_freq * (2 ** (7/12))

        for b in range(bars_per_chord):
            for beat in range(beats_per_bar):
                note_dur = beat_len * (1 if beat % 2 == 0 else 0.5)
                n_samples = int(sr * note_dur)
                if sample_idx + n_samples > total_samples:
                    n_samples = total_samples - sample_idx

                mel_note = melody_pentatonic[(beat + b*3 + ci*5 + random.randint(0,2)) % len(melody_pentatonic)]
                mel_freq = root_freq * (2 ** (mel_note / 12))

                chunk = []
                for i in range(n_samples):
                    t = i / sr
                    vol = 0.18 + 0.04 * math.sin(2*math.pi*(beat/beats_per_bar + b/bars_per_chord + ci*0.3))
                    env = max(0, 1 - t/note_dur*0.3)
                    mel_env = max(0, 1 - t/note_dur*1.5)

                    val = vol*env*(math.sin(2*math.pi*root_freq*t) + 0.55*math.sin(2*math.pi*third_freq*t) + 0.45*math.sin(2*math.pi*fifth_freq*t))
                    val += vol*0.7*mel_env*math.sin(2*math.pi*mel_freq*t)
                    val += vol*0.12*math.sin(2*math.pi*root_freq*2*t) + vol*0.06*math.sin(2*math.pi*root_freq*3*t)
                    val = max(-1.0, min(1.0, val))
                    chunk.append(struct.pack('<h', int(val * 32000)))

                if chunk:
                    all_data.extend(b''.join(chunk))
                sample_idx += n_samples

    remaining = total_samples - sample_idx
    if remaining > 0:
        fade_len = min(int(sr * 2), remaining)
        for i in range(remaining):
            env = 1.0 - min(i/fade_len, 1.0) if i < fade_len else 0
            all_data.extend(struct.pack('<h', 0))

    with wave.open(filepath, 'w') as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(bytes(all_data))

tracks = [
    ('晨光微露.wav',120,'C'),('午后阳光.wav',95,'G'),('雨后彩虹.wav',88,'D'),
    ('森林漫步.wav',100,'Am'),('海浪轻语.wav',72,'F'),('星空下的思念.wav',80,'Em'),
    ('春风十里.wav',110,'C'),('秋日私语.wav',85,'Dm'),('冬日暖阳.wav',78,'G'),
    ('月夜听风.wav',65,'Am'),('花开时节.wav',105,'F'),('云端漫步.wav',90,'C'),
    ('溪流潺潺.wav',92,'G'),('咖啡时光.wav',75,'Cm'),('书香岁月.wav',82,'F'),
    ('远方的你.wav',88,'G'),('静谧湖畔.wav',68,'Dm'),('晨曦初露.wav',115,'C'),
    ('暮色温柔.wav',70,'Am'),('竹林深处.wav',95,'E'),('樱花飘落.wav',86,'D'),
    ('山间小路.wav',102,'G'),('月光如水.wav',76,'Em'),('微风拂面.wav',98,'C'),
    ('梦境边缘.wav',64,'Am'),('茶香袅袅.wav',80,'F'),('雪落无声.wav',60,'Dm'),
    ('归途的鸟.wav',108,'G'),('老街旧巷.wav',85,'Cm'),('烛光晚餐.wav',72,'F'),
    ('蒲公英的约定.wav',90,'C'),('时间的河.wav',66,'Am'),('记忆碎片.wav',84,'Dm'),
    ('雨中漫步.wav',88,'G'),('夕阳西下.wav',70,'F'),('夜的钢琴曲.wav',60,'Am'),
    ('风的形状.wav',96,'Em'),('秘密花园.wav',82,'C'),('远方来信.wav',94,'G'),
    ('浅笑安然.wav',78,'F'),('流年似水.wav',68,'Dm'),('梧桐叶落.wav',86,'Am'),
    ('琴声悠扬.wav',102,'C'),('宁静致远.wav',55,'D'),('心之所向.wav',92,'G'),
    ('岁月静好.wav',74,'F'),('云端之恋.wav',80,'Em'),('往事随风.wav',88,'Cm'),
    ('指尖流淌.wav',96,'D'),('暖冬将至.wav',72,'G'),('春暖花开.wav',110,'C'),
    ('夏夜蝉鸣.wav',85,'Am'),('秋意浓时.wav',78,'Dm'),('冬日炉火.wav',60,'F'),
]

print(f'Generating {len(tracks)} tracks...')
for i,(name,bpm,key) in enumerate(tracks):
    fp = os.path.join(MUSIC_DIR,name)
    print(f'[{i+1}/{len(tracks)}] {name}', end=' ', flush=True)
    generate_wav(fp,bpm,key,duration_sec=25)
    print(f'{os.path.getsize(fp)//1024}KB')
print(f'Done! {len(tracks)} files in {MUSIC_DIR}')
