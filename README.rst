Blender.LectureEdit
===================

*Blender.LectureEdit* is a script library for `Blender <https://www.blender.org/>`_, that facilitates the editing of lecture videos, in which feature a speaker, who is visible in front of his presentation slides.
It automates routine tasks in the editing of such videos, which saves time, makes the videos of a series of lectures more consistent and allows for corrections in the slide deck without major re-editing of the video or even re-recording of the lecture.

Features
--------
* Facilitation of the synchronization of multiple camera tracks.
* Automated setup of the compositing for processing greenscreen recordings of the speaker.
* Exporting the slide transition times and starting times of animations to a Microsoft PowerPoint presentation.
* Automation of blending out the speaker for certain slides.

Maturity of the project
-----------------------
So far, the project is very immature.
This is all documentation, that exists and some features are still missing (e.g. normalizing the audio loudness).
A better documentation, an improved user experience and a more complete feature set are currently in development.

Usage
-----
1. Download the source code of *Blender.LectureEdit*.
2. Create a new Blender project and save it.
3. Create a *Source* folder next to your saved Blender project file.
   * Put the Microsoft PowerPoint file with the slides in the *Source* folder and give it the same name as the blender project, except for the file ending, which has to be *.pptx*.
   * Put a video recording of the speaker in the source file.
     The file name must begin with the same name as the Blender project file (without the file ending).
     After that, the file name must contain the affix * - Speaker* for a regular recording or * - Greenscreen* for a greenscreen recording.
     You can put numbers after this affix, if this recording is split to multiple files.
     At the end, there has to be the regular file ending of the video file.
   * If you have a video of the speaker's slides, you put it also in the *Source* folder and use the same naming scheme, but with the affix * - Slides*.
   * If you have a separate recording of the speaker's audio, you can again put it in the *Source* folder, rename it and use the affix * - Audio*.
4. Open the file *automation.py*, that you find in the *automation* folder of *Blender.LectureEdit*, with Blender's text editor.
5. Uncomment the processing step, that you want to do next in the Python file.
6. Run the processing step by going to Blender's Python console and run the command *bpy.data.texts["automation.py"].as_module()* to execute the code in the Python file.

Concepts
--------
*Blender.LectureEdit* creates multiple scenes in your Blender project, each of which serves a distinct purpose:
* *Sync* is for synchronizing the different audio and video files.
  It's sequence editor will contain the audio track of the speaker as the first track.
  In the subsequent tracks, the beginning and the end of the audio tracks of the other videos will be added.
  You can now adjust them to be in sync with the speaker video.
  With that, *BlenderLectureEdit* can figure out, how the other videos have to be shifted and/or scaled in time to be in sync with the speaker's audio.
* *Cut* is for cutting the video.
  Use the sequence editor to crop the video to those parts, that you are interested in.
  You can of course also remove parts in the middle.
  You can export the audio track from this scene in order to process it with an external normalization tool.
* *Slides* contains the video of the lecture slides.
  Use the sequence editor to set markers, whenever a slide transition occurs or when an animation has been started manually.
* *Greenscreen* is for doing the processing of the greenscreen recording.
  Use the compositing editor to pick the color for the keying and to adjust the colors of the resulting video of the speaker (often people look somewhat pale in a greenscreen video).
* *Merge* is for combining all of the videos into one scene.
  Use this scene to export the final video.

*Blender.LectureEdit* automatically creates a folder with the name *Intermediate* next to the *Source* folder.
This folder contains files, with information about the video editing, most of which is redundant to the Blender project file.
However, some of these files are meant to be edited for processing steps, that are done outside of Blender:
* The file *lecture_presentation.pptx* is the presentation with the timings for the slide transitions and the animations.
  Open this file in Microsoft PowerPoint and export it as a video with the file name *lecture_presentation.mp4* to create the video with the slides, that is used in the final edit.
* The file *rough_audio.flac* contains the raw audio track of the speaker.
  You can edit this track with external tools and save the result as *lecture_audio.flac*, so it is used in the final edit.
* The file *speaker_visibility* contains a list of slides and animations with a Boolean flag for each of them.
  Set the flag to *false*, when the speaker shall be blended out for that part of the presentation.

Credits
-------
*Blender.LectureEdit* has been created and is maintained in the scope of the `CYSTINET-Africa <https://www.cysti.net>`_ project.
This project is a coalition of five universities in Tanzania, Zambia, Mosambique and Munich to do research on medical and economic aspects of the *Taenia solium* tapeworm.
One goal of this project is to create an eLearning course about *Taenia solium* for students of veterinary and human medicine.
Blender and *Blender.LectureEdit* are used to edit the lecture videos for this course.
