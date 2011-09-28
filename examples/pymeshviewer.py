#!/usr/bin/env python
# coding: utf-8

import sys
import tkinter
import tkinter.filedialog
import togl
import opengl
import opengl.rokuro
import triangle


class Frame(tkinter.Frame):
    def __init__(self, width, height, master=None, **kw):
        super(Frame, self).__init__(master, **kw)
        self.master.title('pymeshio viewer')
        self.current='.'
        # setup menu
        menu_bar = tkinter.Menu(self)
        self.master.config(menu=menu_bar)

        menu_file = tkinter.Menu(menu_bar, tearoff=False)
        menu_bar.add_cascade(label='FILE', menu=menu_file, underline=0)

        menu_file.add_command(label='Open', under=0, command=self.onOpen)

        # setup opengl widget
        self.glworld=opengl.BaseController(opengl.rokuro.RokuroView(25), triangle.Triangle(5))
        glwidget=togl.Widget(self, self.glworld, width=width, height=height)
        glwidget.pack(fill=tkinter.BOTH, expand=True)

        # event binding
        self.bind('<Key>', self.onKeyDown)
        self.bind('<MouseWheel>', lambda e: self.glworld.onWheel(-e.delta) and glwidget.onDraw())

    def onOpen(self):
        filename=tkinter.filedialog.askopenfilename(
                filetypes=[
                    ('poloygon model files', '*.mqo;*.pmd'),
                    ], 
                initialdir=self.current)
        print('open: %s' % filename)

    def onKeyDown(self, event):
        key=event.keycode
        if key==27:
            # Escape
            sys.exit()
        if key==81:
            # q
            sys.exit()
        else:
            print("keycode: %d" % key)


if __name__ == '__main__':
    f = Frame(width=600, height=600)
    f.pack(fill=tkinter.BOTH, expand=True)
    f.focus_set()
    f.mainloop()

