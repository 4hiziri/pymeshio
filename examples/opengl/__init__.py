#!/usr/bin/env python
# coding: utf-8

from OpenGL.GL import *
import re
from .baseview import *


DELEGATE_PATTERN=re.compile('^on[A-Z]')

class BaseController(object):
    def __init__(self, view, root):
        self.view=view
        self.root=root
        self.isInitialized=False
        self.delegate(view)
        self.delegate(root)

    def delegate(self, to):
        for name in dir(to):  
            if DELEGATE_PATTERN.match(name):
                method = getattr(to, name)  
                setattr(self, name, method)

    def onUpdate(*args):pass
    def onLeftDown(*args):pass
    def onLeftUp(*args):pass
    def onMiddleDown(*args):pass
    def onMiddleUp(*args):pass
    def onRightDown(*args):pass
    def onRightUp(*args):pass
    def onMotion(*args):pass
    def onResize(*args):pass
    def onWheel(*args):pass
    def onKeyDown(*args):pass
    def onInitialize(*args):pass

    def initialize(self):
        self.view.onResize()
        glEnable(GL_DEPTH_TEST)
        # ���������̌Ăяo��
        self.onInitialize()

    def draw(self):
        if not self.isInitialized:
            self.initialize()
            self.isInitialized=True
        # OpenGL�o�b�t�@�̃N���A
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        # ���e�s��̃N���A
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        self.view.updateProjection()
        # ���f���r���[�s��̃N���A
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        # OpenGL�`��
        self.view.updateView()
        self.root.draw()
        glFlush()

