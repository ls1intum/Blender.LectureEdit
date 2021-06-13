.. _default_settings:

Adjusting the default settings
==============================

*Blender.LectureEdit* has a configurable set of default settings.
Some of these are simply default values for configurations, that will be adjusted individually for each video.
Examples for these are the configuration for green screen processing or the speaker placement.
Other settings like the video resolution and frame rate are not adjusted during the video editing process.
In order to change these, you have no other option but to edit the default settings.

The default settings are in a *Python* file with the name ``default_settings.py`` in the ``automation`` directory of the *Blender.LectureEdit*.
You can simply edit this file to adjust the settings globally for all video editing projects.
If you want to adjust the settings only for individual projects, you can open the file in the *Blender* text editor and adjust the settings there.

.. image:: /images/blender_default_settings.png
   :scale: 20%

If you have the settings file open in *Blender*'s text editor, *Blender.LectureEdit* will find it there and load the default settings from the content of that text editor.
The path from where *Blender* has loaded the file is not important, because *Blender.LectureEdit* finds the opened file by only looking for the file name ``default_settings.py``.
So you can make a copy of the file, if you want to avoid to overwrite the original file.

You will find some hints about which setting each of the values configures in the file.

The ``default_settings.py`` file has to contain valid *Python* code.
Otherwise, it will not be possible to interpret the settings in the file and *Blender.LectureEdit* will crash.
So make sure, that you do not add any invalid punctuation or whitespaces.
Also, do not delete any of the settings, because missing settings will cause crashes, too.

