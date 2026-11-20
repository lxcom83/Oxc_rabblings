"""Paint the Rabblings globe texture sheet (indexed to GEOhybrid-1.pal).
Layout: 29 columns x 3 rows of 32x32 tiles (row = zoom detail). Tile id = column.
Usage: python3 make_tiles.py <old_sheet.png> <palette.pal> <out.png> [preview.png]"""
import sys, math, random
import numpy as np
from PIL import Image
old=Image.open(sys.argv[1]); pal=[tuple(int(x) for x in l.split()) for l in open(sys.argv[2]).read().split('\n')[3:] if l.strip()]
NCOL=29; rng_global=np.random.RandomState(7)
def vnoise(rs,g,oct=3):
    out=np.zeros((32,32)); amp=1.0; tot=0
    ys,xs=np.mgrid[0:32,0:32]
    for o in range(oct):
        p=g*(2**o); lat=rs.rand(p,p)
        fx=xs*p/32.0; fy=ys*p/32.0
        x0=np.floor(fx).astype(int); y0=np.floor(fy).astype(int); tx=fx-x0; ty=fy-y0
        tx=tx*tx*(3-2*tx); ty=ty*ty*(3-2*ty)
        a=lat[y0%p,x0%p]; b=lat[y0%p,(x0+1)%p]; c=lat[(y0+1)%p,x0%p]; d=lat[(y0+1)%p,(x0+1)%p]
        out+=amp*((a*(1-tx)+b*tx)*(1-ty)+(c*(1-tx)+d*tx)*ty); tot+=amp; amp*=0.5
    return out/tot
def ramp(n,block,lo,hi,rs=None,jit=1):
    """map n in 0..1 to palette indices block*16+lo..hi with a little dither"""
    idx=lo+n*(hi-lo)
    if rs is not None and jit: idx=idx+rs.uniform(-jit,jit,n.shape)
    return (block*16+np.clip(np.round(idx),lo,hi)).astype(np.uint8)
def ridge(n): return 1-np.abs(n-0.5)*2     # 1 along thin curvy lines
def tile(kind,seed,g):
    rs=np.random.RandomState(seed); n1=vnoise(rs,g); n2=vnoise(rs,g+1); n3=vnoise(rs,g*2,2)
    t=np.zeros((32,32),np.uint8)
    if kind=="gloom":
        t=ramp(n1,1,2,11,rs); m=n2>0.58; t[m]=ramp(n3,15,2,4,rs)[m]; m=(n3>0.72); t[m]=ramp(n1,1,12,15,rs)[m]
    elif kind=="fen":
        t=ramp(n1,14,0,8,rs); m=n2>0.60; t[m]=ramp(n3,13,5,8,rs)[m]
        m=(rs.rand(32,32)>0.93)&~(n2>0.60); t[m]=ramp(n1,7,6,10,rs)[m]
    elif kind=="warren":
        t=ramp(n1,9,0,9,rs); m=n2>0.55; t[m]=ramp(n3,4,4,9,rs)[m]
        m=(rs.rand(32,32)>0.95); t[m]=9*16+13
    elif kind=="crag":
        t=ramp(n1,5,3,8,rs); m=ridge(n2)>0.86; t[m]=5*16+9
        m=n3>0.7; t[m]=ramp(n1,6,4,8,rs)[m]
    elif kind=="ash":
        t=ramp(n1,9,0,5,rs); m=n2>0.55; t[m]=ramp(n3,10,3,7,rs)[m]; m=n3>0.78; t[m]=ramp(n1,8,5,8,rs)[m]
    elif kind=="slag":
        t=ramp(n1,5,6,9,rs,0.6); m=n2>0.55; t[m]=ramp(n3,8,2,6,rs)[m]
        m=ridge(vnoise(rs,g+2,2))>0.90; t[m]=ramp(n1,8,0,2,rs)[m]
    elif kind=="vortex":
        ys,xs=np.mgrid[0:32,0:32]; cx,cy=15.5+rs.uniform(-4,4),15.5+rs.uniform(-4,4)
        dx=((xs-cx+16)%32)-16; dy=((ys-cy+16)%32)-16; r=np.sqrt(dx*dx+dy*dy)+1e-6; a=np.arctan2(dy,dx)
        sw=0.5+0.5*np.sin(3*a+r*0.55+n1*3.0)               # spiral arms
        t=ramp(n1,14,6,12,rs); m=sw>0.72; t[m]=ramp(n2,8,9,14,rs)[m]
        m=(ridge(n3)>0.88)&(sw>0.35); t[m]=ramp(n1,8,0,3,rs)[m]
    return t
RECIPES={0:("ash",1),7:("ash",2),8:("ash",3),
 1:("gloom",1),11:("gloom",2),3:("gloom",3),
 2:("fen",1),19:("fen",2),21:("fen",3),
 22:("warren",1),23:("warren",2),18:("warren",3),
 5:("crag",1),6:("crag",2),20:("crag",3),
 24:("slag",1),25:("slag",2),26:("slag",3),
 4:("vortex",1),27:("vortex",2),28:("vortex",3)}
sheet=Image.new('P',(NCOL*32,96)); flat=[c for col in pal for c in col]; flat+=[0]*(768-len(flat)); sheet.putpalette(flat)
for row,g in enumerate((3,4,6)):
    for col,(kind,sd) in RECIPES.items():
        t=tile(kind,sd*100+col*7,g); sheet.paste(Image.fromarray(t,'P'),(col*32,row*32))
    for col in (9,10,12,13,14,15,16,17):          # keep Factions ice + ocean tiles
        sheet.paste(old.crop((col*32,row*32,col*32+32,row*32+32)),(col*32,row*32))
sheet.save(sys.argv[3])
if len(sys.argv)>4:
    big=sheet.convert('RGB').crop((0,0,NCOL*32,32)).resize((NCOL*32*3,96),Image.NEAREST); big.save(sys.argv[4])
