.. _file_links:

File links
==========

In some situations, it is not practical, to store the original video files in the ``Source`` directory of the respective lecture.
For example, when there was a continuous recording at a conference, so that multiple talks are recorded in the same video file.
In such case, you might want to store the original videos in a common directory and just have a reference to them in the ``Source`` directories of your editing projects.
*Blender.LectureEdit* supports two mechanisms to support this feature.


Symbolic links
--------------

Symbolic links are a built-in feature of many operating systems to create a file, that simply refers to another file without occupying the disk space, that a copy of the file would require.
Since they are well supported by those operating systems, symbolic links are usually easy to create and convenient to use (e.g. double-clicking on the symbolic link will open the video file).

However, symbolic links are not universally supported.
They are not available in *Microsoft Windows* and many network storage systems like *Nextcloud* or samba shares do not support them either.
If you rely on such a system, *Blender.LectureEdit* allows to use link-files as a workaround.


link-files
----------

Link files are regular text files with the file extension ``.link`` and a single line of text in them, which defines the relative path from the link file to the actual video file.
Being regular text files, they can easily be stored on any system, but they do not offer the convenience, that symbolic links do.

In the relative path, that is written in the link-file, ``..`` refers to the parent directory of the current one (i.e. "one directory up").
So, if you have a file hierarchy like the following...

* *directory*: ``Chapter 1``

  * *directory*: ``Lecture 1``

    * *directory*: ``Source``

      * *file*: ``Lecture 1 - Speaker.link``

  * *directory*: ``Lecture 2``

    * ...

* *directory*: ``Chapter 2``

  * ...

* *directory*: ``Recordings``

  * *file*: ``Speaker recordings.mp4``

... the content of the file ``Lecture 1 - Speaker.link`` would be:

.. code-block::

   ../../../Recordings/Speaker recordings.mp4
