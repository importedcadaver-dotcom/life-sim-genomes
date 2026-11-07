"""Pillow-backed QA preview of the production viewer draw path, NOT pygame.

This is a diagnostic adapter, not a Pygame replacement and not a runtime QA claim.
No changes to evolution. Limited to the subset of Pygame drawing calls used by
biosphere.viewer. Uses real viewer code to catch layout exceptions and clipping.

Requires Pillow (only for this QA harness). Run:
    python tools/pygame_preview_stub.py --size 1020x685 --out results/qa/minimal.png
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys
import types
import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np

_FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
_MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'

class Rect:
    def __init__(self, *args):
        if len(args)==1: args=args[0]
        self.x,self.y,self.w,self.h=map(int,args)
    @property
    def center(self):return (self.x+self.w//2,self.y+self.h//2)
    @property
    def centerx(self):return self.x+self.w//2
    @property
    def right(self):return self.x+self.w
    @property
    def bottom(self):return self.y+self.h
    def collidepoint(self,*args):
        if len(args)==1: args=args[0]
        x,y=args
        return self.x<=x<self.right and self.y<=y<self.bottom
    def __iter__(self):return iter((self.x,self.y,self.w,self.h))

class Surface:
    def __init__(self,img):self.img=img;self.clip=None
    def get_size(self):return self.img.size
    def fill(self, color): ImageDraw.Draw(self.img).rectangle((0,0,*self.img.size),fill=tuple(color))
    def set_clip(self,rect):self.clip=rect
    def get_rect(self,**kwargs):
        w,h=self.img.size
        if 'center' in kwargs:
            cx,cy=kwargs['center'];return Rect(cx-w//2,cy-h//2,w,h)
        return Rect(0,0,w,h)
    def blit(self,surf,pos):
        if isinstance(pos,Rect):pos=(pos.x,pos.y)
        x,y=map(int,pos);im=surf.img
        region=Rect(x,y,im.width,im.height)
        if self.clip:
            x0=max(x,self.clip.x,0);y0=max(y,self.clip.y,0)
            x1=min(x+im.width,self.clip.right,self.img.width);y1=min(y+im.height,self.clip.bottom,self.img.height)
        else:
            x0=max(0,x);y0=max(0,y);x1=min(x+im.width,self.img.width);y1=min(y+im.height,self.img.height)
        if x1<=x0 or y1<=y0:return
        crop=im.crop((x0-x,y0-y,x1-x,y1-y))
        if crop.mode=='RGBA':self.img.paste(crop,(x0,y0),crop)
        else:self.img.paste(crop,(x0,y0))

class Font:
    def __init__(self,name,size,bold=False):
        self.font=ImageFont.truetype((_MONO if 'consolas' in name else _FONT),int(size))
        self.size_n=int(size)
    def size(self,text):
        # Font dimensions emulate pygame with extra leading.
        rect=self.font.getbbox(str(text));return (max(1,rect[2]-rect[0]), self.size_n+3)
    def render(self,text,aa,color):
        text=str(text);w,h=self.size(text)
        im=Image.new('RGBA',(w+2,h+4),(0,0,0,0))
        ImageDraw.Draw(im).text((0,0),text,font=self.font,fill=tuple(color)+(255,))
        return Surface(im)

class Draw:
    @staticmethod
    def rect(screen,color,rect,width=0,border_radius=0):
        if not isinstance(rect,Rect):rect=Rect(rect)
        if rect.w<=0 or rect.h<=0: return
        box=(rect.x,rect.y,rect.right-1,rect.bottom-1)
        dr=ImageDraw.Draw(screen.img)
        if width:dr.rounded_rectangle(box, radius=max(0,border_radius), outline=tuple(color),width=width)
        else:dr.rounded_rectangle(box,radius=max(0,border_radius),fill=tuple(color))
    @staticmethod
    def circle(screen,color,center,radius,width=0):
        x,y=map(int,center);r=int(radius)
        if r<=0:return
        dr=ImageDraw.Draw(screen.img);bounds=(x-r,y-r,x+r,y+r)
        if width:dr.ellipse(bounds,outline=tuple(color),width=int(width))
        else:dr.ellipse(bounds,fill=tuple(color))
    @staticmethod
    def line(screen,color,a,b,width=1):
        ImageDraw.Draw(screen.img).line([tuple(map(int,a)),tuple(map(int,b))],fill=tuple(color),width=max(1,int(width)))
    @staticmethod
    def lines(screen,color,closed,pts,width=1):
        if not pts:return
        seq=[tuple(map(int,p)) for p in pts];seq=seq+[seq[0]] if closed else seq
        ImageDraw.Draw(screen.img).line(seq,fill=tuple(color),width=max(1,int(width)))
    @staticmethod
    def polygon(screen,color,pts,width=0):
        seq=[tuple(map(int,p)) for p in pts]
        dr=ImageDraw.Draw(screen.img)
        if width:dr.line(seq+[seq[0]],fill=tuple(color),width=int(width))
        else:dr.polygon(seq,fill=tuple(color))

@dataclass
class Event:
    type:int
    key:int|None=None
    pos:tuple[int,int]|None=None
    button:int|None=None
    y:int=0
    w:int=0
    h:int=0


def build_fake_pygame(size, keys=(), mouse=None, auto_click=None):
    pg=types.ModuleType('pygame')
    pg.RESIZABLE=1;pg.QUIT=2;pg.KEYDOWN=3;pg.MOUSEWHEEL=4;pg.MOUSEBUTTONDOWN=5;pg.MOUSEBUTTONUP=6;pg.MOUSEMOTION=7;pg.VIDEORESIZE=8
    names=('SPACE','n','j','EQUALS','KP_PLUS','MINUS','KP_MINUS','z','x','f','l','t','s','h','r','i','b','m','c','a','o','p','u','k','y','PAGEDOWN','PAGEUP','v','g','TAB','LEFTBRACKET','RIGHTBRACKET','ESCAPE','q','e','d','w','1','2','3','4','5')
    for index,name in enumerate(names):setattr(pg,'K_'+name,101+index)
    pg.Rect=Rect;pg.draw=Draw
    main_screen=Surface(Image.new('RGB',size,(10,18,24)))
    pg.init=lambda:None;pg.quit=lambda:None
    pg.display=types.SimpleNamespace(set_mode=lambda dims,flags: Surface(Image.new('RGB',dims,(10,18,24))),set_caption=lambda t:None,flip=lambda:None)
    pg.font=types.SimpleNamespace(SysFont=lambda name,size,bold=False:Font(name,size,bold))
    pg.mouse=types.SimpleNamespace(get_pos=lambda:(-100,-100))
    pg.transform=types.SimpleNamespace(smoothscale=lambda surface,dims: Surface(surface.img.resize(dims, Image.Resampling.BILINEAR)))
    pg.surfarray=types.SimpleNamespace(make_surface=lambda arr: Surface(Image.fromarray(np.transpose(arr,(1,0,2)), 'RGB')))
    pg.image=types.SimpleNamespace(save=lambda screen,path:screen.img.save(path))
    class Clock:
        def get_time(self):return 28
        def tick(self,fps):return 28
    pg.time=types.SimpleNamespace(Clock=Clock)
    calls=[0]
    def get_events():
        n=calls[0];calls[0]+=1
        if n==0:
            return [Event(pg.KEYDOWN,key=getattr(pg,'K_'+k)) for k in keys]
        return []
    pg.event=types.SimpleNamespace(get=get_events,Event=lambda kind,**kwargs:Event(kind,**kwargs))
    return pg

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--size',default='1400x880')
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--seed',type=int,default=701)
    ap.add_argument('--resume',type=Path)
    ap.add_argument('--keys',nargs='*',default=[])
    ap.add_argument('--max-population',type=int,default=900)
    ap.add_argument('--qa-script',type=Path)
    ap.add_argument('--qa-report',type=Path)
    args=ap.parse_args()
    width,height=map(int,args.size.lower().split('x'))
    pg=build_fake_pygame((width,height),args.keys)
    sys.modules['pygame']=pg
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from biosphere.viewer import view
    p=types.SimpleNamespace(seed=args.seed,resume=args.resume,max_population=args.max_population,
        boundary_mode='wrap',patch_shift_interval=0,move_cost=.065,resource_layout='hills',resource_background=None,
        island_count=8,island_sigma=2.8,island_peak=10.,smoke_frames=8,screenshot=args.out,qa_report=args.qa_report,qa_script=args.qa_script,
        window_width=width,window_height=height)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    view(p)
    print(f'Pillow preview from real viewer draw code: {args.out} ({width}x{height}); NOT pygame QA')

if __name__=='__main__':main()
