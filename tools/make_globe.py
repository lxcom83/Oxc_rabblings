import math, random, os, sys, collections
seed = int(sys.argv[2]) if len(sys.argv)>2 else 11
random.seed(seed)
OUT = sys.argv[1]
STEP_X, STEP_Y = 4.0, 4.0
NX, NY = int(360/STEP_X), int(180/STEP_Y)

# ---- landmasses: name, lon, lat, rx, ry (degrees), biome weights (forest, farm, mountain, desert, polar)
CONT = [("Ashfall",   60, 35, 32, 24, dict(forest=2, farm=2, mountain=3, desert=5, polar=0)),
        ("Thornmarch",150, 10, 40, 26, dict(forest=6, farm=3, mountain=2, desert=1, polar=0)),
        ("Gloamreach",250,-15, 34, 25, dict(forest=4, farm=2, mountain=3, desert=2, polar=1)),
        ("Cinderspine",320, 42, 24, 18, dict(forest=2, farm=1, mountain=5, desert=1, polar=3)),
        ("Shards",    110,-48, 28, 13, dict(forest=1, farm=1, mountain=4, desert=2, polar=3))]
ISL = [(random.uniform(5,355), random.uniform(-58,62), random.uniform(2.5,6), random.uniform(2,4.5)) for _ in range(30)]

# ---- smooth value noise
def mk_noise(sz, s):
    r = random.Random(s); g=[[r.random() for _ in range(sz)] for _ in range(sz)]
    def f(x,y):
        x*=sz/360.0; y=(y+90)*sz/180.0
        xi=int(math.floor(x)); yi=int(math.floor(y)); tx=x-xi; ty=y-yi
        tx=tx*tx*(3-2*tx); ty=ty*ty*(3-2*ty)
        a=g[yi%sz][xi%sz]; b=g[yi%sz][(xi+1)%sz]; c=g[(yi+1)%sz][xi%sz]; d=g[(yi+1)%sz][(xi+1)%sz]
        return (a*(1-tx)+b*tx)*(1-ty)+(c*(1-tx)+d*tx)*ty
    return f
n_coast = mk_noise(40, seed+1); n_fine = mk_noise(90, seed+2)

def land_val(lon,lat):
    v=-9; owner=None
    for c in CONT:
        n,cx,cy,rx,ry,_=c
        dx=(lon-cx+180)%360-180; dy=lat-cy
        d=math.hypot(dx/rx,dy/ry)
        s=1.0-d + (n_coast(lon,lat)-0.5)*0.9 + (n_fine(lon,lat)-0.5)*0.35
        if s>v: v=s; owner=c
    for (cx,cy,rx,ry) in ISL:
        dx=(lon-cx+180)%360-180; dy=lat-cy
        d=math.hypot(dx/rx,dy/ry)
        s=1.0-d + (n_fine(lon,lat)-0.5)*0.5
        if s>v: v=s; owner=None
    return v, owner

# ---- jittered lattice (shared vertices => seamless)
V={}
for j in range(NY+1):
    for i in range(NX+1):
        jx=0 if i in (0,NX) else random.uniform(-.8,.8)
        jy=0 if j in (0,NY) else random.uniform(-.8,.8)
        V[(i,j)]=(round(i*STEP_X+jx,2), round(-90+j*STEP_Y+jy,2))

# ---- biome patches: voronoi seeds, each with a random biome from the local weights
SEEDS=[]
for _ in range(260):
    lon=random.uniform(0,360); lat=random.uniform(-80,80)
    SEEDS.append((lon,lat))
def nearest_seed(lon,lat):
    best=None;bd=1e9
    for k,(sx,sy) in enumerate(SEEDS):
        dx=(lon-sx+180)%360-180; dy=lat-sy
        d=dx*dx*math.cos(math.radians(lat))**2+dy*dy+ (n_fine(lon+7,lat)-0.5)*20
        if d<bd: bd=d;best=k
    return best
SEED_ROLL={}
BIOMES=["forest","farm","mountain","desert","polar"]
def pick(w):
    keys=[k for k in BIOMES if w.get(k,0)>0]; ws=[w[k] for k in keys]
    return random.choices(keys,ws)[0]
def climate(lat,w):
    w=dict(w); a=abs(lat)
    if a<50: w["polar"]=0
    if a>66: w["polar"]=w.get("polar",0)+9
    elif a>54: w["polar"]=w.get("polar",0)+2; w["mountain"]=w.get("mountain",0)+2
    return w
GENERIC=dict(forest=3,farm=2,mountain=3,desert=2,polar=1)

IDS=dict(forest=[0,6,10,11], farm=[1,2,3,4], mountain=[5], desert=[7,8], polar=[9,12])
polys=[]; grid=collections.defaultdict(str); stats=collections.defaultdict(collections.Counter)
for j in range(NY):
    for i in range(NX):
        clon=(i+.5)*STEP_X; clat=-90+(j+.5)*STEP_Y
        v,own=land_val(clon,clat)
        polar_cap = abs(clat)>=82
        if v<0.04 and not polar_cap: continue
        k=nearest_seed(clon,clat)
        w=climate(clat, own[5] if own else GENERIC)
        if k not in SEED_ROLL: SEED_ROLL[k]=pick(w)
        b=SEED_ROLL[k]
        r=random.random()
        if r<0.14: b=pick(w)                       # fragmenting: individual cells break from the patch
        elif r<0.20: b=random.choice(BIOMES[:4])   # oddities: oasis in desert, crag in forest...
        if polar_cap: b="polar"
        tid=random.choice(IDS[b])
        a=V[(i,j)];bq=V[(i+1,j)];c=V[(i+1,j+1)];d=V[(i,j+1)]
        polys.append([tid,*a,*bq,*c,*d])
        grid[(i,j)]=b
        if not polar_cap: stats[own[0] if own else "Isles"][b]+=1

# ---- textures: each texture id mixes several battlescape terrains (names verified against vanilla xcom1 globe.rul)
MIX={ "forest":[("FOREST",45),("JUNGLE",25),("MOUNT",15),("CULTA",15)],
      "farm":  [("CULTA",50),("FOREST",20),("JUNGLE",10),("MOUNT",10),("DESERT",10)],
      "mountain":[("MOUNT",55),("FOREST",15),("POLAR",15),("DESERT",15)],
      "desert":[("DESERT",55),("MOUNT",25),("CULTA",10),("JUNGLE",10)],
      "polar": [("POLAR",60),("MOUNT",30),("FOREST",10)] }
# continent flavour (lon1,lon2,lat1,lat2)
FLAV=[("DESERT",30,[28,92,11,59]),("JUNGLE",30,[108,192,-16,36]),("FOREST",30,[216,284,-40,10]),("MOUNT",30,[296,344,24,60]),("POLAR",25,[82,138,-62,-34])]
tx=["  textures:"]
for b,ids in IDS.items():
    for tid in ids:
        tx.append("    - id: %d"%tid); tx.append("      terrain:")
        for n,wt in MIX[b]:
            tx.append("        - name: %s"%n); tx.append("          weight: %d"%wt)
        for n,wt,ar in FLAV:
            tx.append("        - name: %s"%n); tx.append("          weight: %d"%wt); tx.append("          area: [%s]"%", ".join(map(str,ar)))

yml=["globe:","  polygons:"]
for p in polys: yml.append("    - ["+", ".join(str(x) for x in p)+"]")
yml+=["  polylines:","    - [0, -85, 1, -85]"]+tx
os.makedirs(OUT+"/Ruleset",exist_ok=True)
open(OUT+"/Ruleset/globe.rul","w").write("\n".join(yml)+"\n")
open(OUT+"/metadata.yml","w").write("""id: RabblingsGeoscape
name: Rabblings Geoscape (globe test)
description: Replaces the Earth globe with a placeholder Rabblings world with mixed biomes. Test build, use a new game.
version: 0.0.2
author: Luke83
isMaster: false
master: xcom1
""")
open(OUT+"/README.txt","w").write("""Rabblings Geoscape - globe test v0.0.2 (placeholder world, mixed biomes)
Install: copy this folder into OXCE's mods folder (Android: /sdcard/openxcom/mods/), Options > Mods, enable, restart, start a NEW game.
Regions/countries/cities are still vanilla Earth (mismatch expected).
Each globe texture now maps to a weighted mix of battlescape terrains, plus continent flavour boxes.
""")
print(len(polys),"polygons")
for k,c in stats.items():
    t=sum(c.values()); print(k, t, {b:round(100*c[b]/t) for b in BIOMES})
# patch size metric: distinct biomes within +-3 cells
dv=[]
for (i,j),b in grid.items():
    s={grid[(x,y)] for x in range(i-3,i+4) for y in range(j-3,j+4) if (x,y) in grid}
    dv.append(len(s))
print("avg distinct biomes within 3 cells:", round(sum(dv)/len(dv),2))
import json; json.dump({"polys":polys},open("/home/claude/gen/polys.json","w"))
