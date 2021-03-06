# Copyright 2020-2021 Jonas Schulte-Coerne and the CYSTINET-Africa project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functools
import itertools
import math
import os
import struct
import threading
import time
import wave
import numpy

__all__ = ("normalize",)


def normalize(source, target, channel, highpass_frequencies, notch_filter_frequencies, notch_filter_q_factor, target_level, headroom, resolution, level_smoothing, level_threshold, limiter_lookahead, show_progress):
    stream, sampling_rate, length = read(path=source, channel=channel)
    for frequency in highpass_frequencies:
        stream = highpass(stream, sampling_rate, frequency=frequency, order=2, regularization=0.0001)
    for frequency in notch_filter_frequencies:
        stream = notch_filter(stream, sampling_rate, frequency, q_factor=notch_filter_q_factor, regularization=0.0001)
    stream = a_weighting(stream, sampling_rate)
    stream = activity(stream, sampling_rate, smoothing_time=0.03)
    stream = level(stream, sampling_rate, smoothing_time=level_smoothing, threshold=level_threshold)
    stream = normalization(stream, level=target_level)
    stream = limiter(stream, sampling_rate, clip=headroom, lookahead=limiter_lookahead, hold=limiter_lookahead / 2)
    if show_progress:
        stream = status(stream, length=length)
    write(stream, sampling_rate, path=target, bits=resolution)


###################################
# The signal processing functions #
###################################


def read(path, channel):
    chunk_size = 2**14
    try:
        import soundfile
    except ImportError:
        def stream():
            with wave.open(str(path), "rb") as f:
                number_of_channels = f.getnchannels()
                if channel > number_of_channels:
                    raise ValueError(f"The channel {channel} does not exist in the file with {number_of_channels} channels")
                bits = f.getsampwidth()
                code = {2: "h", 4: "i"}[bits]
                factor = 1.0 / (2 ** (8 * f.getsampwidth() - 1))
                chunk = f.readframes(chunk_size)
                while chunk:
                    number_of_frames = len(chunk) // bits
                    mask = f"<{number_of_frames}{code}"
                    yield from numpy.multiply(struct.unpack(mask, chunk)[channel-1::number_of_channels], factor)
                    chunk = f.readframes(chunk_size)
        with wave.open(str(path), "rb") as f:
            sampling_rate = float(f.getframerate())
            length = f.getnframes()
        return stream(), sampling_rate, length
    else:
        def stream():
            with soundfile.SoundFile(path) as f:
                chunk = f.read(chunk_size, always_2d=True)
                while len(chunk):
                    yield from chunk[:, channel-1]
                    chunk = f.read(chunk_size, always_2d=True)
        with soundfile.SoundFile(path) as f:
            sampling_rate = float(f.samplerate)
            length = f.frames
        return stream(), sampling_rate, length

def _apply_iir_filter(stream, zb, za, copy_input=False):
    coefficients = numpy.empty(len(zb) + len(za) - 1)
    coefficients[0:len(zb)] = zb
    coefficients[len(zb):] = -za[0:-1]
    data_window = numpy.zeros(len(coefficients))
    input_cache = data_window[0:len(zb)]
    output_cache = data_window[len(zb):]
    if copy_input:
        for sample in stream:
            input_cache[0:-1] = input_cache[1:]
            input_cache[-1] = sample
            filtered = numpy.dot(coefficients, data_window)
            output_cache[0:-1] = output_cache[1:]
            output_cache[-1] = filtered
            yield sample, filtered
    else:
        for sample in stream:
            input_cache[0:-1] = input_cache[1:]
            input_cache[-1] = sample
            filtered = numpy.dot(coefficients, data_window)
            output_cache[0:-1] = output_cache[1:]
            output_cache[-1] = filtered
            yield filtered


def highpass(stream, sampling_rate, frequency, order, regularization):
    # compute the filter coefficients for a time-continuous Butterworth filter
    k = 1 / (2 * math.pi * frequency)
    if order == 1:
        a = (k, 1)
    elif order == 2:
        a = (k**2, 2 * k * math.cos(math.pi / 4), 1)
    else:
        raise ValueError("Filter orders higher than two are not supported.")
    order = len(a) - 1
    b = (1,) + (0,) * order
    # transform the coefficients with the bilinear transform
    fs = sampling_rate
    q = 1.0 - regularization
    formulas = {
        1: lambda x: (-2 * x[0] * fs + x[1] * q, 2 * x[0] * fs + x[1]),
        2: lambda x: (4 * x[0] * fs**2 - 2 * x[1] * fs * q + x[2] * q**2, -8 * x[0] * fs**2 + 2 * x[1] * fs * (q - 1) + 2 * x[2] * q, 4 * x[0] * fs**2 + 2 * x[1] * fs + x[2]),
    }
    za, zb = (formulas[order](x) for x in (a, b))
    zb = numpy.divide(zb, za[-1])
    zb *= k ** order
    za = numpy.divide(za, za[-1])
    # apply the filter to the stream
    yield from _apply_iir_filter(stream, zb, za)


def notch_filter(stream, sampling_rate, frequency, q_factor, regularization):
    # compute the filter coefficients for a time-continuous notch filter
    w = 2 * math.pi * frequency
    a = (1, w / q_factor, w ** 2)
    b = (1, 0, w ** 2)
    # transform the coefficients with the bilinear transform
    fs = sampling_rate
    q = 1.0 - regularization
    formula = lambda x: (4 * x[0] * fs**2 - 2 * x[1] * fs * q + x[2] * q**2, -8 * x[0] * fs**2 + 2 * x[1] * fs * (q - 1) + 2 * x[2] * q, 4 * x[0] * fs**2 + 2 * x[1] * fs + x[2])
    za, zb = (formula(x) for x in (a, b))
    zb = numpy.divide(zb, za[-1])
    za = numpy.divide(za, za[-1])
    # apply the filter to the stream
    yield from _apply_iir_filter(stream, zb, za)


def a_weighting(stream, sampling_rate):
    # compute the zeros and poles for a time-continuous A-weighting filter
    fr = 1000.0  # 1000Hz in IEC 61672-1
    fl = 10 ** 1.5  # f_L in IEC 61672-1:2013, Appendix E.2
    fa = 10 ** 2.45  # f_A in IEC 61672-1:2013, Appendix E.3
    fh = 10 ** 3.9  # f_H in IEC 61672-1
    fr2 = fr ** 2
    fl2 = fl ** 2
    fh2 = fh ** 2
    c = fl2 * fh2  # c in IEC 61672-1
    d = 0.5 ** 0.5  # D in IEC 61672-1
    b = (fr2 + c / fr2 - d * (fl2 + fh2)) / (1.0 - d)  # b in IEC 61672-1
    root = (b ** 2 - 4 * c) ** 0.5
    root5 = 5 ** 0.5 / 2
    f1 = ((-b - root) / 2) ** 0.5  # f_1 in IEC 61672-1
    f2 = (1.5 - root5) * fa  # f_2 in IEC 61672-1
    f3 = (1.5 + root5) * fa  # f_3 in IEC 61672-1
    f4 = ((-b + root) / 2) ** 0.5  # f_2 in IEC 61672-1
    zeros = (0.0,) * 4
    poles = numpy.multiply((f1, f1, f2, f3, f4, f4), -2 * math.pi)
    # transform the zeros and poles with the matched-z-transform
    num, den = (functools.reduce(numpy.polynomial.polynomial.polymul, ((-math.exp(x / sampling_rate), 1.0) for x in d)) for d in (zeros, poles))
    gain = 10 ** (2.446165 / 20)
    zb, za = numpy.divide(num, gain*den[-1]), numpy.divide(den, den[-1])
    # apply the filter to the stream
    yield from _apply_iir_filter(stream, zb, za, copy_input=True)


def activity(stream, sampling_rate, smoothing_time):
    stream = iter(stream)
    smoothing = numpy.exp(-2*math.pi / (smoothing_time * sampling_rate))
    first = numpy.empty(shape=(int(round(sampling_rate * smoothing_time)), 2))
    for i, sample in zip(range(len(first)), stream):
        first[i] = sample
    first = first[0:i+1]
    envelope0 = envelope1 = numpy.linalg.norm(first[:, 1]) / math.sqrt(len(first))
    for data in (first, stream):
        for output, side_chain in data:
            squared = side_chain ** 2
            envelope0 = (envelope0 - squared) * smoothing + squared
            envelope1 = (envelope1 - envelope0) * smoothing + envelope0
            yield output, math.sqrt(envelope1)
        first = None


def level(stream, sampling_rate, smoothing_time, threshold):
    stream = iter(stream)
    smoothing = numpy.exp(-2*math.pi / (smoothing_time * sampling_rate))
    first = numpy.empty(shape=(int(round(sampling_rate * smoothing_time)), 2))
    for i, sample in zip(range(len(first)), stream):
        first[i] = sample
    first = first[0:i+1]
    envelope0 = envelope1 = numpy.linalg.norm(first[:, 1]) / math.sqrt(len(first))
    threshold_factor = 10.0 ** (threshold / 20.0)
    for data in (first, stream):
        for output, side_chain in data:
            activity = 0
            if side_chain >= envelope1 * threshold_factor:
                envelope0 = (envelope0 - side_chain) * smoothing + side_chain
                envelope1 = (envelope1 - envelope0) * smoothing + envelope0
                activity = 0.5
            yield output, envelope1
        first = None


def normalization(stream, level):
    target_level = 10.0 ** (level / 20.0)
    for output, side_chain in stream:
        yield output * target_level / side_chain


def limiter(stream, sampling_rate, clip, lookahead, hold):
    stream = iter(stream)
    peak = 10.0 ** (clip / 20.0)
    length = int(round(lookahead * sampling_rate))
    buffer = numpy.zeros(length)
    gain_buffer = numpy.ones(length)
    ones = itertools.cycle((1.0, ))
    hold = numpy.empty(int(round(hold * sampling_rate)))
    release = None
    for i, sample in zip(range(length), stream):
        buffer[i] = sample
    amplitude = max(numpy.abs(buffer))
    if amplitude > peak:
        target_gain = peak / amplitude
        gain_buffer[:] = target_gain
        release = numpy.linspace(target_gain, 1.0, length)
        state = release
    else:
        state = ones
    target_gain = 1.0
    i = 0
    while True:
        for sample, gain in zip(stream, state):
            current_gain = gain_buffer[i]
            amplitude = abs(sample)
            yield buffer[i] * current_gain
            buffer[i] = sample
            gain_buffer[i] = gain
            i = (i + 1) % length
            if amplitude * gain > peak:
                target_gain = min(target_gain, peak / amplitude)
                slope = (target_gain - current_gain) / length
                slope = min(gain_buffer[i] - current_gain, slope)
                if slope == 0:
                    gain_buffer[:] = target_gain
                    release = numpy.linspace(target_gain, 1.0, length)
                    state = release
                else:
                    attack = numpy.arange(current_gain + slope, target_gain, slope)
                    gain_buffer[0:len(attack)] = attack
                    gain_buffer[len(attack):] = target_gain
                    gain_buffer = numpy.roll(gain_buffer, i)
                    hold[:] = target_gain
                    state = hold
                break
        else:
            if state is hold:
                release = numpy.linspace(target_gain, 1.0, length)
                state = release
            elif state is release:
                target_gain = 1.0
                state = ones
            elif state is ones:
                break
    buffer = numpy.roll(buffer, -i)
    gain_buffer = numpy.roll(gain_buffer, -i)
    fade_out = numpy.blackman(2*length)[length:]
    gain_buffer *= fade_out
    for sample, gain in zip(buffer, gain_buffer):
        yield sample * gain


def status(stream, length):
    start = time.time()
    i = 0
    run = True
    def poll_information():
        while run:
            print(f"processing the audio track: {i / length * 100:4.1f}% ({int(round(time.time() - start))}s)", end="\r")
            time.sleep(2)
    thread = threading.Thread(target=poll_information)
    thread.daemon = True
    thread.start()
    for i, sample in enumerate(stream):
        yield sample
    run = False
    thread.join()
    duration = time.time() - start
    print(f"processing the audio track: done in {int(duration / 60)}:{int(round(duration % 60))} minutes")


def write(stream, sampling_rate, path, bits):
    buffer_size = 2**14 * 8 // bits # buffer 16kB of the outbut file before writing them to the file
    buffer = numpy.empty(buffer_size)
    factor = 2 ** (bits - 1) - 1
    code = {16: "h", 32: "i"}[bits]
    try:
        import soundfile
    except ImportError:
        if not str(path).lower().endswith(".wav") or bits not in (16, 32):
            raise ValueError("Writing files other than 16 or 32 bit wav files is not supported.\n"
                             "Change the file format or read the documentation about how to use the SoundFile library to support additional formats.")
        with wave.open(str(path), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(bits // 8)
            f.setframerate(int(round(sampling_rate)))
            while True:
                i = -1
                for i, sample in zip(range(buffer_size), stream):
                    buffer[i] = sample
                if i >= 0:
                    b = buffer[0:i+1]
                    b *= factor
                    mask = f"<{len(b)}{code}"
                    integers = numpy.round(b).astype(int)
                    chunk = struct.pack(mask, *integers)
                    f.writeframes(chunk)
                else:
                    break
    else:
        file_format = {".wav": "WAV", ".flac": "FLAC"}[os.path.splitext(path)[1]]
        with soundfile.SoundFile(path, mode="w",
                                 samplerate=int(round(sampling_rate)), channels=1,
                                 format=file_format, subtype=f"PCM_{bits}") as f:
            while True:
                i = -1
                for i, sample in zip(range(buffer_size), stream):
                    buffer[i] = sample
                if i >= 0:
                    f.write(buffer[0:i+1])
                else:
                    break


##############################################
# If the file is used as a standalone script #
##############################################

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="the path to the audio file that shall be normalized", type=str)
    parser.add_argument("target", help="the path to where the normlized audio shall be saved", type=str)
    parser.add_argument("-c", "--channel", help="the channel of the input audio file", type=int, default=1)
    parser.add_argument("-f", "--highpass", help="a frequency of a high pass filter", type=float, default=None)
    parser.add_argument("-h", "--humfilter", help="a frequency of hum, that shall be removed (usually 50Hz or 60Hz)", type=float, default=None)
    parser.add_argument("-q", "--q_factor", help="the Q-factor of the hum filtering", type=float, default=10.0)
    parser.add_argument("-l", "--level", help="the target level in db[FS]", type=float, default=-20.0)
    parser.add_argument("-p", "--headroom", help="the headroom in dB[FS] after limiting", type=float, default=-0.1)
    parser.add_argument("-r", "--resolution", help="the resolution in bits of the target file", type=int, default=16)
    parser.add_argument("-s", "--smoothing", help="the smoothing time in seconds for the level normalization", type=float, default=10.0)
    parser.add_argument("-t", "--threshold", help="the level threshold in dB for the activity detection of the normalization", type=float, default=-10.0)
    parser.add_argument("-a", "--lookahead", help="the lookahead time of the limiter in seconds", type=float, default=0.025)
    args = parser.parse_args()

    normalize(source=args.source,
              target=args.target,
              channel=args.channel,
              highpass_frequencies=[args.highpass] if args.highpass else [],
              notch_filter_frequencies=numpy.multiply(args.humfilter, [1, 3, 5]) if args.humfilter else [],
              notch_filter_q_factor=args.q_factor,
              target_level=args.level,
              headroom=args.headroom,
              resolution=args.resolution,
              level_smoothing=args.smoothing,
              level_threshold=args.threshold,
              limiter_lookahead=args.lookahead,
              show_progress=True)
