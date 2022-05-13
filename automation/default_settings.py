"""
These are the default settings for Blender.LectureEdit.

You can define custom settings for your project by opening this file or a copy of it in Blender's
text editor and modifying the values, that you want to be configured differently. Blender.LectureEdit
will then take those settings instead of the ones from the settings file in its source code directory.

You can save the modified file wherever you want. However, it is important, that it is called
"default_settings.py", because that is the name, that Blender.LectureEdit is looking for, when
searching the files, that are opened in Blender's text editor.

Make sure, that this file contains valid Python code. Otherwise, Blender.LectureEdit will crash when
loading it.
"""

# video settings
fps = 25        # the frame rate in frames per second of the source and target videos
width = 1920    # the width in number of pixels of the target video
height = 1080   # the height in number of pixels of the target video

# audio normalization settings
audio_channel = 1               # the channel of the rough audio file, that shall be used as the speaker audio track
highpass_frequencies = [100.0]  # frequencies of high pass filters in Hz below which the frequencies are attenuated. Specify multiple frequencies for a sharper roll-off
notch_filter_frequencies = []   # frequencies for notch filters, that attenuate specific frequencies. Can be used to attenuate hum. Consider specifying a filter for the base frequency of the hum (e.g. 50Hz) and its low integer multiples, especially the odd ones (e.g. 150Hz and 250Hz)
notch_filter_q_factor = 10      # the Q-factor for the filter. Higher values result in a greater attenuation of a narrower frequency band
target_level = -20.0            # the target level of the normalization in dB[FS]
headroom = -0.1                 # the maximum level of the limiter in db[FS]
audio_resolution = 16           # the resolution of the resulting audio file in bits per sample
level_smoothing = 10.0          # the smoothing time in seconds for the normalization
level_threshold = -10.0         # a threshold in dB of the current level, below which a part is regarded as silent and ignored in the normalization
limiter_lookahead = 0.025       # the lookahead time in seconds of the limiter

# settings for the export of the slide transitions to PowerPoint
fps_correction = (25 / fps) * (85918 / 70845) * (70832 / 70845)  # a correction factor for the slide transition times, so the video rendered by PowerPoint can be treated as if it had the desired frame rate

# settings for cropping out the green screen
# (as specified in the keying node in the Greenscreen scenes' compositing view)
pre_blur = 0
screen_balance = 0.5
despill_factor = 1.0
despill_balance = 0.8
edge_kernel_radius = 3
edge_kernel_tolerance = 0.3
clip_black = 0.2
clip_white = 0.9
dilate_erode = 0
feather_falloff = "SMOOTH"  # can be one of: SMOOTH, SPHERE, ROOT, INVERSE_SQUARE, SHARP, LINEAR
feather_distance = 0
post_blur = 0
key_color = (1.0, 1.0, 1.0)

# hue, saturation and value settings for the post-processing of the green screen video
# (as specified in the color-correction- and hue-saturation-value-nodes in the Greenscreen scenes' compositing view)
speaker_hue = 0.5
speaker_saturation = 1.0
speaker_value = 1.0
enable_color_correction = False  # only affects the color-correction node, not the hue-saturation-value node

# settings for the speaker placement in the Merge scene
# (as set for the speaker track in the Merge scene)
speaker_scale = 0.5
speaker_shift_x = 650
speaker_shift_y = -280
speaker_crop_left = 0
speaker_crop_right = 0
speaker_crop_top = 0
speaker_crop_bottom = 0

# settings for the fade-in and fade-out of the speaker in the Merge scene
speaker_fade_time = 1.0    # the time in seconds, that a fade-out or fade_in of the speaker shall take

# settings for the video export
# (as specified in the output settings)
container = "MPEG4"
video_codec = "H264"
video_quality = "HIGH"
encoding_speed = "GOOD"
audio_codec = "VORBIS"
audio_bitrate = 128
sampling_rate = 44100
