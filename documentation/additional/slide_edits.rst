.. _slide_edits:

What has to be done, when the *PowerPoint* slides have changed?
===============================================================

If the slides have changed in *PowerPoint*, you may have to re-do everything, that is described in :ref:`slides` and :ref:`merge`.
However, if you have only made small changes to the slides like fixing a typo, you can skip the most laborious steps of the process.
The following flow chart might help you to figure out, which tasks have to be re-done.

.. graphviz::

   digraph SlideEdits{
      splines=false;

      start [shape=circle, style=filled, fillcolor=black];
      new_slides [label="added or removed\nslides or animations?"; shape=diamond];
      changed_layout [label="changed the\nlayout of a slide?"; shape=diamond];
      markers [label="update the markers\nin the Slides scene", shape=rect];
      create [label="run the\ncreate_presentation\ncommand"; shape=rect];
      export [label="export the video\nin PowerPoint"; shape=rect];
      setup [label="run the\nsetup command"; shape=rect];
      visibility [label="update the\nspeaker visibility"; shape=rect]
      render [label="render the video"; shape=rect];
      end [shape=doublecircle, style=filled, fillcolor=black];

      start -> new_slides;
      new_slides -> markers [taillabel="yes"];
      new_slides -> create [taillabel="no"];
      markers -> create -> export -> setup -> changed_layout;
      changed_layout -> visibility [taillabel="yes"];
      changed_layout -> render [taillabel="no"];
      visibility -> render -> end;

      {rank=same; new_slides; markers}
      {rank=same; changed_layout; visibility}
   }

