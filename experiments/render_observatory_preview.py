"""Pillow preview of observatory presentation using a genuine saved world.

NOTE: This is a static visual QA mock matching the viewer layout/palette. It is
NOT a screenshot of the running Pygame application.
"""
from __future__ import annotations

from pathlib import Path
import sys
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from biosphere.viewer import layout_for, terrain_rgb
from biosphere.simulation import World

ROOT = Path(__file__).resolve().parents[1]
checkpoint = ROOT / 'results/experiment_004/checkpoints/seed_701_islands.npz'
out = ROOT / 'results/experiment_005/observatory_visual_preview.png'
w = World.load(checkpoint)
recent = []
history = [(w.tick,w.population)]
for i in range(80):
    w.step()
    if w.tick%5==0: history.append((w.tick,w.population))
    for ev in w.last_events:
        if 'x' in ev:
            recent.append(ev)
recent=recent[-200:]
W,H=1400,880
L=layout_for(W,H,w.config.width,w.config.height)
ox,oy,pw,ph=L.map_rect
sx,sy,sw,sh=L.side_rect
im=Image.new('RGB',(W,H),(10,18,24)); d=ImageDraw.Draw(im)
font_candidates = ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf')
font_bold_candidates = ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf')
def f(size,bold=False):
    paths=font_bold_candidates if bold else font_candidates
    for path in paths:
        if Path(path).exists(): return ImageFont.truetype(path,size)
    return ImageFont.load_default()
F14,F12,F23,F26 = f(14),f(12),f(23,True),f(26,True)
GOLD=(247,205,116);GREEN=(144,224,167);TXT=(233,239,232);MUTE=(151,169,172);PANEL=(20,33,40)
def text(t,x,y,font=F14,color=TXT):
    d.text((int(x),int(y)),str(t),font=font,fill=color)
def rect(x0,y0,x1,y1,fill=PANEL,r=10,line=None):
    d.rounded_rectangle((int(x0),int(y0),int(x1),int(y1)),radius=r,fill=fill,outline=line)
text('THE ACCIDENTAL BIOSPHERE',24,15,F26,TXT)
text('FIELD OBSERVATORY   /   EXPERIMENTAL ARTIFICIAL LIFE',25,54,F12,GREEN)
text(f'SEED {w.seed}   |   ISLANDS   |   WRAP BOUNDARIES', W-394,23,F14,MUTE)
d.line((24,86,W-24,86),fill=(38,61,66))
colors=terrain_rgb(w.food,w.capacity)
base=Image.fromarray(colors,'RGB').resize((pw,ph),Image.Resampling.BILINEAR)
im.paste(base,(ox,oy)); d=ImageDraw.Draw(im)
d.rounded_rectangle((ox-2,oy-2,ox+pw+2,oy+ph+2),radius=8,outline=(77,110,104),width=2)
# Generate actual organism positions and headings from the saved simulation.
scale = L.pixel_scale
for i in range(w.population):
    px,py=ox+int(w.x[i]*scale),oy+int(w.y[i]*scale)
    if not (ox+3<px<ox+pw-3 and oy+3<py<oy+ph-3): continue
    ang=float(w.angle[i]); vx,vy=math.cos(ang),math.sin(ang)
    g=int(w.generation[i]); body=max(3,min(7,int(scale*.42)))
    col=(min(255,123+15*g),max(116,206-5*g),min(245,190+2*g))
    tip=(px+vx*body*1.4,py+vy*body*1.4)
    a=(px-vx*body*.5-vy*body*.7,py-vy*body*.5+vx*body*.7)
    b=(px-vx*body*.5+vy*body*.7,py-vy*body*.5-vx*body*.7)
    d.line((px-vx*body*1.6,py-vy*body*1.6,px,py),fill=(18,33,43),width=2)
    d.polygon((tip,a,b),fill=col)
selected=int(np.argmax(w.generation))
selpx,selpy=ox+int(w.x[selected]*scale),oy+int(w.y[selected]*scale)
d.ellipse((selpx-20,selpy-20,selpx+20,selpy+20),outline=GOLD,width=3)
for ev in recent[-25:]:
    if ev['tick'] < w.tick - 22: continue
    ex=ox+int(ev['x']*scale);ey=oy+int(ev['y']*scale)
    rad=4+(w.tick-ev['tick'])*.4
    d.ellipse((ex-rad,ey-rad,ex+rad,ey+rad),outline=GREEN if ev['kind']=='birth' else (241,130,112),width=1)
rect(ox+11,oy+11,ox+199,oy+42,(15,31,37),7)
text('● FOOD STOCK  |  1x',ox+21,oy+17,F14,GREEN)
commands=['Ⅱ PAUSE','STEP','− SPEED','+ SPEED','− ZOOM','+ ZOOM','FOLLOW','FEED BRUSH','HEATMAP','SAVE']
gap=6; bw=int((pw-gap*(len(commands)-1))/len(commands))
for i,title in enumerate(commands):
    x=ox+i*(bw+gap)
    rect(x,L.toolbar_y,x+bw,L.toolbar_y+33,PANEL,8)
    tw=d.textbbox((0,0),title,font=F12)[2]
    text(title,x+(bw-tw)/2,L.toolbar_y+9,F12,TXT)
text('WORLD STATUS',sx,sy,F14,GREEN)
rect(sx,sy+28,sx+sw-9,sy+154)
for k,(label,value) in enumerate((('ALIVE',w.population),('TICK',w.tick),('BORN',w.total_births),('DIED',w.total_deaths))):
    x = sx+15+(k%2)*(sw-18)/2;y=sy+37+(k//2)*61
    text(label,x,y,F12,MUTE);text(f'{value:,}',x,y+15,F23,TXT)
line_y=sy+174
text('POPULATION TREND',sx,line_y,F14,GREEN)
gy=line_y+24
rect(sx,gy,sx+sw-9,gy+73)
if len(history)>1:
    m=max(v for _,v in history)*1.12
    first=history[0][0];last=history[-1][0]
    coords=[(sx+8+(t-first)/(last-first)*(sw-25),gy+64-n/m*55) for t,n in history]
    d.line(coords,fill=GREEN,width=2,joint='curve')
text('SPECIMEN INSPECTOR',sx,gy+89,F14,GREEN)
iy=gy+112
rect(sx,iy,sx+sw-9,iy+163)
idx=selected
text(f'# {int(w.ids[idx])}    •    GENERATION {int(w.generation[idx])}',sx+12,iy+12,F14,GOLD)
text(f'Energy {float(w.energy[idx]):.1f}     Age {int(w.age[idx])} / {w.config.lifespan}',sx+12,iy+38,F14,TXT)
text(f'Parent #{int(w.parents[idx])}     Intake {float(w.last_intake[idx]):.2f}',sx+12,iy+61,F14,MUTE)
turn,speed,_=w.controls()
text(f'Speed {float(speed[idx]):.2f}    Turn {float(turn[idx]):+.2f} rad',sx+12,iy+85,F14,MUTE)
text('ENERGY',sx+12,iy+111,F12,MUTE)
rect(sx+91,iy+116,sx+sw-27,iy+126,(42,57,59),4)
barw=(sw-118)*min(1,float(w.energy[idx])/w.config.reproduction_threshold)
rect(sx+91,iy+116,sx+91+barw,iy+126,GREEN,4)
text('L follow · scroll zoom · right-drag pan',sx+12,iy+139,F12,MUTE)
event_y=iy+179
text('LATEST EVENTS',sx,event_y,F14,GREEN)
rect(sx,event_y+23,sx+sw-9,event_y+130)
for i,ev in enumerate(recent[-3:][::-1]):
    text(f'T{ev["tick"]:>5}   {ev["kind"].upper()}  #{ev["id"]}',sx+10,event_y+32+i*25,F12,MUTE)
text(f'LIVE   1 tick/frame   ·  growth {w.config.growth_rate:.3f}   ·  movement cost {w.config.move_cost:.2f}   ·  H help  /  J journal  /  I islands  /  B walls  /  R restart',27,H-18,F12,GREEN)
text('STATIC DESIGN PREVIEW · NOT A PYGAME WINDOW SCREENSHOT',W-446,H-35,F12,(207,156,111))
out.parent.mkdir(parents=True,exist_ok=True)
im.save(out)
print(out)
