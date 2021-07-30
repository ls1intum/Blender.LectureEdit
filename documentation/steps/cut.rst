Cutting the video
=================

If you did the synchronization of the source files before, the *Cut* :ref:`scene <blender_documentation_scenes>` should already be populated with a single track, that contains the speaker audio.
If this is not the case, you can issue the setup command again to initialize the *Cut* scene.

>>> automation.setup()

Now, you can crop and cut the audio track how you want it to be in the lecture.
The video will be cut automatically by *Blender.LectureEdit* according to your editing of the audio track.

After this, you have to save your work with the following command:

>>> automation.save_cut_scene()

