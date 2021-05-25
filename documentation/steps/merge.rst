.. _merge:

Merging it all together
=======================

When you have completed all of the previous processing steps, you can combine their results in the final video.
Make sure, that the *Merge* scene is set up by running the command

>>> automation.setup()

When you are coming from the green screen processing, you may have to switch back to the *Video Editing* workspace.


Placing the speaker
-------------------

You can now place the speaker in front of their slides by selecting the *Speaker PIP* tracks in the fourth channel of the sequencer and adjusting their settings in the dialog right of the sequencer.

* You will find the scaling parameter under *Effect Strip*.
* The speaker's position can be adjusted in the *Transform* tab.
* And in the end, it is recommended to adjust the settings in the *Crop* tab, so that the speaker video is reduced to the immediate surroundings of the speaker.
  With regular videos, this obviously reduces the area, that is needlessly covered by the speaker's background.
  But also with green screen videos, the cropping avoids problems, such as a green shimmer from an imperfect proceessing of those areas of the green screen, that were far from the speaker and therefore not illuminated properly.

In the fifth channel, *Blender.LectureEdit* loads an image, that can be used as a reference for placing the speaker.
Obviously, this track has to be hidden (by selecting it and pressing ``h``) before rendering the video.

It can be tedious to set up to configure the speaker placement, when there are many tracks in the fourth channel.
*Blender.LectureEdit* takes its configuration from the first track for each source video file.
So, for example, if the recording of the speaker is split to two video files, you have to identify the first tracks in the fourth channel for each of these files and adjust their settings.
Then you can save the settings with the following command and *Blender.LectureEdit* will apply them to all other tracks in this channel.

>>> automation.save_merge_scene()

Because of this, it is not possible to have different speaker placement settings for two tracks, that come from the same source video.


Configuring the speaker visibility
----------------------------------

.. _fadeout:

Sometimes, the slides leave no room for a speaker to be displayed in front of them.
*Blender.LectureEdit* has a feature to configure the visibility of the speaker for each slide and each click-triggered animation.

You will find the file ``speaker_visibility.json`` in the ``Intermediate`` directory.
It contains a structure, that is similar to a table, where each row is for one slide or animation.
The first entries in these rows are meant to identify the slide or the animation.
The last entry is by default ``true``, but it can be set to ``false``, when the speaker shall not be shown in front of this slide or after this animation.

You may have noticed the markers, that you already know from marking the slide transitions.
They are meant to help navigating to the respective slides, so you can quickly check whether a slide contains content, that would be covered by the speaker.

You can edit the ``true`` and ``false`` values, so the speaker does not cover anything important in the final video.
Do not change anything in the punctuation or the first entries for each row.
Also, make sure that ``true`` and ``false`` are not misspelled and that they are written only in lower case letters.
Otherwise, *Blender.LectureEdit* will not be able to read the file.

In order to apply the changed settings from the ``speaker_visibility.json`` file, you have to re-run the setup-command.

>>> automation.setup()


Exporting the video
-------------------

Now, you can render the final video.
This is being done in the main menu by clicking on ``Render`` and then ``Render Animation``.
You will find the rendered video in the ``Final`` directory.

If you intend to upload your lecture to a video hosting platform like *Youtube*, you may want to create a thumbnail for the video.
For this, move the blue position marker in the sequencer to a frame, where the speaker looks good and then use the ``Render Image`` functionality to create a single image.

