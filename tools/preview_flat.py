import sys,yaml
from PIL import Image,ImageDraw
d=yaml.safe_load(open(sys.argv[1]))['globe']['polygons']
S=4;im=Image.new('RGB',(360*S,180*S),(10,30,70));g=ImageDraw.Draw(im)
col={}
import random;random.seed(1)
for p in d:
    t=p[0]
    if t in (13,14,15,16):continue
    if t not in col:col[t]=tuple(random.randint(60,230) for _ in range(3))
    pts=[((p[i])*S,(90-p[i+1])*S) for i in range(1,len(p),2)]
    g.polygon(pts,fill=col[t],outline=(0,0,0))
im.save(sys.argv[2])
