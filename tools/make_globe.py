import math, random, os, sys, collections
seed = int(sys.argv[2]) if len(sys.argv)>2 else 11
random.seed(seed)
OUT = sys.argv[1]
STEP_X, STEP_Y = 4.0, 4.0
NX, NY = int(360/STEP_X), int(180/STEP_Y)

# ---- landmasses: name, lon, lat, rx, ry (degrees), biome weights (forest, farm, mountain, desert, polar)
CONT = [("Ashfall",    55, 32, 38, 28, dict(forest=1, farm=2, mountain=3, desert=5, polar=0, vortex=1, slag=3), "DESERT"),
        ("Thornmarch", 150,  8, 42, 30, dict(forest=5, farm=3, mountain=2, desert=1, polar=0, vortex=0, fen=4), "JUNGLE"),
        ("Gloamreach", 250,-12, 40, 30, dict(forest=3, farm=2, mountain=3, desert=2, polar=1, vortex=2, fen=3, slag=1), "FOREST"),
        ("Cinderspine",330, 42, 26, 22, dict(forest=2, farm=1, mountain=4, desert=1, polar=3, vortex=2, slag=4), "MOUNT"),
        ("Shards",     105,-50, 34, 16, dict(forest=1, farm=1, mountain=3, desert=2, polar=3, vortex=2, slag=3), "POLAR"),
        ("Veilmoor",   200, 50, 24, 18, dict(forest=4, farm=2, mountain=2, desert=0, polar=2, vortex=2, fen=4), "FOREST"),
        ("Drowned Reach",300,-45,26, 16, dict(forest=2, farm=2, mountain=3, desert=1, polar=2, vortex=3, fen=2, slag=2), "MOUNT")]
ISL = [(random.uniform(5,355), random.uniform(-62,66), random.uniform(3,8), random.uniform(2.5,5)) for _ in range(60)]

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

GAP=0.20   # score margin below which a cell between two landmasses becomes sea channel
def land_val(lon,lat,ch=True):
    sc=[]
    for k,c in enumerate(CONT):
        n,cx,cy,rx,ry,_,_f=c
        rx*=1.18; ry*=1.18
        dx=(lon-cx+180)%360-180; dy=lat-cy
        d=math.hypot(dx/rx,dy/ry)
        sc.append((1.0-d*0.70 + (n_coast(lon,lat)-0.5)*0.8 + (n_fine(lon,lat)-0.5)*0.35, ("c",k)))
    for k,(cx,cy,rx,ry) in enumerate(ISL):
        dx=(lon-cx+180)%360-180; dy=lat-cy
        d=math.hypot(dx/rx,dy/ry)
        sc.append((1.0-d*0.8 + (n_fine(lon,lat)-0.5)*0.5, ("i",k)))
    sc.sort(key=lambda t:-t[0])
    v,oid=sc[0]; v2=sc[1][0]
    own=CONT[oid[1]] if oid[0]=="c" else None
    # channel between two landmasses
    vv=v
    if v2>-0.45: vv=v+0.5*(v2+0.45)       # fill valleys between neighbouring landmasses
    if ch and v2>0.0 and v-v2<GAP: return -9,own,oid
    v=vv
    return v, own, oid



# ---- fill enclosed seas (lakes / holes ringed by land) so continents read as solid land
FW,FH=180,90
def _isl(i,j): return land_val((i+.5)*2,-90+(j+.5)*2)[0]>=-0.06 or abs(-90+(j+.5)*2)>=81
LAND=[[_isl(i,j) for i in range(FW)] for j in range(FH)]
comp={}; comps=[]
for j in range(FH):
    for i in range(FW):
        if LAND[j][i] or (i,j) in comp: continue
        cid=len(comps); q=[(i,j)]; comp[(i,j)]=cid; cells=[]
        while q:
            x,y=q.pop(); cells.append((x,y))
            for nx,ny in (((x+1)%FW,y),((x-1)%FW,y),(x,y+1),(x,y-1)):
                if 0<=ny<FH and not LAND[ny][nx] and (nx,ny) not in comp: comp[(nx,ny)]=cid; q.append((nx,ny))
        comps.append(cells)
big=max(range(len(comps)),key=lambda c:len(comps[c]))
FILL=set()
for c,cells in enumerate(comps):
    if c!=big and len(cells)<=120: FILL.update(cells)     # up to ~240 sq deg of enclosed sea becomes land
print("enclosed sea cells filled:",len(FILL))

# ---- irregular variable-density point set + Delaunay: small triangles at coasts, big ones inland, no grid
import numpy as np
from scipy.spatial import Delaunay
def cosl(lat): return max(math.cos(math.radians(lat)),0.35)
def spacing(lon,lat):
    if abs(lat)>=80: return 5.0
    v=land_val(lon,lat,False)[0]
    if v<-0.45: return random.uniform(5.5,8.0)
    t=min(1.0,max(0.0,(abs(v-0.05)-0.0)/0.55))      # 0 at coast, 1 deep inland / deep sea
    return (1.5+3.2*t)*random.uniform(0.8,1.35)
PTS=[]; CELL=2.0; hashg=collections.defaultdict(list)
def ok(lon,lat,r):
    ci=int(lon//CELL); cj=int((lat+90)//CELL); R=int(r/CELL/ max(cosl(lat),0.35))+2
    for di in range(-R,R+1):
        for dj in range(-int(r/CELL)-2,int(r/CELL)+3):
            for (x,y) in hashg.get(((ci+di)%int(360/CELL),cj+dj),()):
                dx=(lon-x+180)%360-180
                if (dx*cosl(lat))**2+(lat-y)**2 < r*r: return False
    return True
def add(lon,lat):
    PTS.append((lon,lat)); hashg[(int(lon//CELL)%int(360/CELL),int((lat+90)//CELL))].append((lon,lat))
for lat in np.arange(-90,90.1,3.0):          # fixed seam columns + pole rows
    PTS.append((0.0,float(lat))); PTS.append((360.0,float(lat)))
for lon in np.arange(0,360.1,6.0):
    PTS.append((float(lon),-90.0)); PTS.append((float(lon),90.0))
for lat0,step in ((82,7.0),(85.5,9.0),(79,8.0)):
    for sg in (1,-1):
        lo=0.0
        while lo<360:
            PTS.append((round(lo+random.uniform(-1.5,1.5),2) if 0<lo<360 else lo, round(sg*(lat0+random.uniform(-1.2,1.2)),2))); lo+=step*random.uniform(.8,1.2)
for p in PTS: hashg[(int(p[0]//CELL)%int(360/CELL),int((p[1]+90)//CELL))].append(p)
tries=0; misses=0
while misses<30000:
    lon=random.uniform(0,360); lat=random.uniform(-88,88)
    r=spacing(lon,lat)
    if r is None: misses+=1; continue
    if ok(lon,lat,r): add(lon,lat); misses=0
    else: misses+=1
P=np.array([(round(x,2),round(y,2)) for x,y in PTS]); P=np.unique(P,axis=0)
DT=Delaunay(P)
print("points",len(P),"triangles",len(DT.simplices))
V={i:(float(P[i][0]),float(P[i][1])) for i in range(len(P))}
polys=[]; grid={}; stats=collections.defaultdict(collections.Counter)
tris=[]; SEA=[]; KILLED=set()
for s in DT.simplices:
    tri=tuple(int(k) for k in s)
    cx=sum(V[k][0] for k in tri)/3; cy=sum(V[k][1] for k in tri)/3
    xs=[V[k][0] for k in tri]
    if max(xs)-min(xs)>40: continue
    cap = abs(cy)>=81
    v,own,oid=land_val(cx,cy)
    if v<-0.06 and not cap and (int(cx//2)%FW,int((cy+90)//2)) in FILL:
        v,own,oid=land_val(cx,cy,False); v=max(v,0.05)
        if v<0.0: v,own,oid=0.05,None,None
    if v<-0.06 and not cap:
        SEA.append(tri); continue
    # reject long thin slivers
    tris.append(dict(v=tri,cx=cx,cy=cy,own=own,oid=(None if cap else oid),cap=cap,cell=len(tris),cl=None))
def build_adj(vertex=False):
    edge=collections.defaultdict(list)
    for n,t in enumerate(tris):
        a_,b_,c_=t["v"]
        keys=[(k,) for k in t["v"]] if vertex else [frozenset(e) for e in ((a_,b_),(b_,c_),(c_,a_))]
        for e in keys: edge[e].append(n)
    adj=collections.defaultdict(set)
    for lst in edge.values():
        for x in lst:
            for y in lst:
                if x!=y: adj[x].add(y)
    return adj
for _round in range(8):
    adj=build_adj(True)
    kill=set()
    for x in adj:
        for y in adj[x]:
            if x<y and tris[x]["oid"] and tris[y]["oid"] and tris[x]["oid"]!=tris[y]["oid"]:
                kill.add(x); kill.add(y)
    print("round",_round,"contacts to clear:",len(kill))
    if not kill: break
    SEA+=[t["v"] for n,t in enumerate(tris) if n in kill]; KILLED.update(t["v"] for n,t in enumerate(tris) if n in kill)
    tris=[t for n,t in enumerate(tris) if n not in kill]
    for n,t in enumerate(tris): t["cell"]=n

# ---- turn small enclosed sea patches (not rift channels) into land
def sea_components():
    em=collections.defaultdict(list)
    for n,tv in enumerate(SEA):
        for e in ((tv[0],tv[1]),(tv[1],tv[2]),(tv[2],tv[0])): em[frozenset(e)].append(n)
    seen=set(); out=[]
    for n0 in range(len(SEA)):
        if n0 in seen: continue
        q=[n0]; seen.add(n0); comp=[]
        while q:
            x=q.pop(); comp.append(x); tv=SEA[x]
            for e in ((tv[0],tv[1]),(tv[1],tv[2]),(tv[2],tv[0])):
                for y in em[frozenset(e)]:
                    if y not in seen: seen.add(y); q.append(y)
        out.append(comp)
    return out
vown=collections.defaultdict(list)
for t in tris:
    for k in t["v"]: vown[k].append(t)
conv=0; keep=[]; drop=set()
for comp in sea_components():
    tvs=[SEA[x] for x in comp]
    continue  # lakes are kept (disabled)
    if len(comp)>45 or any(tv in KILLED for tv in tvs): continue
    nb=[t for tv in tvs for k in tv for t in vown.get(k,[]) if t["oid"]]
    oids={t["oid"] for t in nb}
    if len(oids)!=1: continue                    # touches 0 or 2+ landmasses: leave as sea
    t0=nb[0]
    for x in comp:
        tv=SEA[x]; cx=sum(V[k][0] for k in tv)/3; cy=sum(V[k][1] for k in tv)/3
        tris.append(dict(v=tv,cx=cx,cy=cy,own=t0["own"],oid=t0["oid"],cap=False,cell=len(tris),cl=None)); drop.add(x); conv+=1
SEA=[tv for n,tv in enumerate(SEA) if n not in drop]
print("lake triangles converted to land:",conv)
adj=build_adj()
order=list(range(len(tris))); random.shuffle(order)
clusters=[]
for s0 in order:
    if tris[s0]["cl"] is not None: continue
    rr=random.random(); target=random.randint(2,5) if rr<.20 else (random.randint(6,12) if rr<.65 else random.randint(12,22))
    cid=len(clusters); members=[s0]; tris[s0]["cl"]=cid
    while len(members)<target:
        cand=[y for x in members for y in adj[x] if tris[y]["cl"] is None and tris[y]["cap"]==tris[s0]["cap"]]
        if not cand: break
        y=random.choice(cand); tris[y]["cl"]=cid; members.append(y)
    clusters.append(members)
singles_left=0
for cid,m in enumerate(clusters):
    if len(m)==1:
        x=m[0]; nb=[tris[y]["cl"] for y in adj[x] if tris[y]["cl"]!=cid and tris[y]["cap"]==tris[x]["cap"] and len(clusters[tris[y]["cl"]])<26]
        if nb:
            to=random.choice(nb); clusters[to].append(x); tris[x]["cl"]=to; clusters[cid]=[]
        else: singles_left+=1
clusters=[m for m in clusters if m]
def cross(o,a,b): return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
def try_quad(x,y):
    sh=set(tris[x]["v"])&set(tris[y]["v"])
    if len(sh)!=2: return None
    p,q=sorted(sh); r=[k for k in tris[x]["v"] if k not in sh][0]; s=[k for k in tris[y]["v"] if k not in sh][0]
    quad=[r,p,s,q]; pts=[V[k] for k in quad]
    sg=[cross(pts[i],pts[(i+1)%4],pts[(i+2)%4])>0 for i in range(4)]
    if not(all(sg) or not any(sg)): return None     # must be convex
    ang=[abs(cross(pts[i],pts[(i+1)%4],pts[(i+3)%4]))/ (math.dist(pts[i],pts[(i+1)%4])*math.dist(pts[i],pts[(i+3)%4])+1e-9) for i in range(4)]
    if min(ang)<0.35: return None                    # skip near-degenerate corners
    if max(ang)>0.99 and min(ang)>0.97: return None  # skip near-rectangles (look square)
    return quad

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
BIOMES=["forest","farm","mountain","desert","polar","vortex","fen","slag"]
def pick(w):
    keys=[k for k in BIOMES if w.get(k,0)>0]; ws=[w[k] for k in keys]
    return random.choices(keys,ws)[0]
def climate(lat,w):
    w=dict(w); a=abs(lat)
    if a<50: w["polar"]=0
    if a>66: w["polar"]=w.get("polar",0)+9
    elif a>54: w["polar"]=w.get("polar",0)+2; w["mountain"]=w.get("mountain",0)+2
    return w
GENERIC=dict(forest=3,farm=2,mountain=3,desert=2,polar=1,vortex=1,fen=2,slag=1)


IDS=dict(forest=[1,11,3], fen=[2,19,21], farm=[22,23,18], mountain=[5,6,20], desert=[0,7,8], slag=[24,25,26], polar=[9,10], vortex=[4,27,28])
shapes=collections.Counter()
for m in clusters:
    t0=tris[m[0]]
    cx=sum(tris[x]["cx"] for x in m)/len(m); cy=sum(tris[x]["cy"] for x in m)/len(m)
    own=t0["own"]; cap=t0["cap"]
    w=climate(cy, own[5] if own else GENERIC)
    k=nearest_seed(cx,cy)
    if k not in SEED_ROLL: SEED_ROLL[k]=pick(w)
    b=SEED_ROLL[k]; r=random.random()
    if r<0.30: b=pick(w)
    elif r<0.38: b=random.choice(["forest","farm","mountain","desert","vortex","fen","slag"])
    if cap: b="polar"
    for x in m:
        stats_key=(own[0] if own else "Isles")
        if not cap: stats[stats_key][b]+=1
        grid[(round(tris[x]["cx"]/2),round((tris[x]["cy"]+90)/2))]=b
    used=set(); mem=list(m); random.shuffle(mem)
    for x in mem:
        if x in used: continue
        if random.random()<.45:
            nbs=[y for y in adj[x] if y in m and y not in used]; random.shuffle(nbs)
            done=False
            for y in nbs:
                q=try_quad(x,y)
                if q:
                    polys.append([random.choice(IDS[b])]+[c for k in q for c in V[k]]); used.add(x); used.add(y); shapes["quad"]+=1; done=True; break
            if done: continue
        used.add(x); polys.append([random.choice(IDS[b])]+[c for k in tris[x]["v"] for c in V[k]]); shapes["tri"]+=1
print("land (excl caps): %.0f%% of area"%(100*sum(1 for t in tris if not t["cap"])*0+0));print("clusters:",len(clusters),"sizes:",dict(sorted(collections.Counter(len(m) for m in clusters).items())),"isolated singles:",singles_left)
print("shapes:",dict(shapes))

# ---- textures: each texture id mixes several battlescape terrains (names verified against vanilla xcom1 globe.rul)
MIX={ "forest":[("FOREST",45),("JUNGLE",25),("MOUNT",15),("CULTA",15)],
      "farm":  [("CULTA",50),("FOREST",20),("JUNGLE",10),("MOUNT",10),("DESERT",10)],
      "mountain":[("MOUNT",55),("FOREST",15),("POLAR",15),("DESERT",15)],
      "desert":[("DESERT",55),("MOUNT",25),("CULTA",10),("JUNGLE",10)],
      "polar": [("POLAR",60),("MOUNT",30),("FOREST",10)],
      "vortex":[("MOUNT",35),("DESERT",30),("FOREST",20),("JUNGLE",15)],
      "fen":[("JUNGLE",45),("FOREST",30),("CULTA",10),("MOUNT",15)],
      "slag":[("MOUNT",50),("DESERT",35),("FOREST",15)] }
# continent flavour (lon1,lon2,lat1,lat2)
FLAV=[(c[6],30,[round(c[1]-c[3]*.9),round(c[1]+c[3]*.9),round(c[2]-c[4]*.9),round(c[2]+c[4]*.9)]) for c in CONT]
tx=["  textures:"]
for b,ids in IDS.items():
    for tid in ids:
        tx.append("    - id: %d"%tid); tx.append("      terrain:")
        for n,wt in MIX[b]:
            tx.append("        - name: %s"%n); tx.append("          weight: %d"%wt)
        for n,wt,ar in FLAV:
            tx.append("        - name: %s"%n); tx.append("          weight: %d"%wt); tx.append("          area: [%s]"%", ".join(map(str,ar)))

# open sea is drawn as big quads FIRST (land polygons are drawn on top of them); ocean textures are draw-only (isOcean), no terrain, so no sea missions
# sea = the leftover Delaunay triangles (no overlap with land, so base/landing lookups hit real land); ocean textures are draw-only (isOcean), no terrain
ocean=[[random.choice([13,14,15,16])]+[c for k in tri for c in V[k]] for tri in SEA]
print("sea triangles:",len(ocean))
polys=polys+ocean
yml=["globe:","  oceanPalette: 13","  oceanShading: false","  countryColor: 239","  cityColor: 81","  baseColor: 133","  lineColor: 210","  polygons:"]
for p in polys: yml.append("    - ["+", ".join(str(x) for x in p)+"]")
tx+=[l for t in (13,14,15,16) for l in ("    - id: %d"%t,"      isOcean: true")]
yml+=["  polylines:","    - [0, -85, 1, -85]"]+tx
os.makedirs(OUT+"/Ruleset",exist_ok=True)
open(OUT+"/Ruleset/globe.rul","w").write("\n".join(yml)+"\n")
open(OUT+"/metadata.yml","w").write("""id: RabblingsGeoscape
name: Rabblings Geoscape (globe test)
description: Replaces the Earth globe with a placeholder Rabblings world with mixed biomes. Test build, use a new game.
version: 0.0.8
author: Luke83
isMaster: false
master: xcom1
requiredExtendedVersion: "5.5.1"
""")
open(OUT+"/README.txt","w").write("""Rabblings Geoscape - globe test v0.0.12 (placeholder world, mixed biomes)
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
print("avg distinct biomes within ~12 deg:", round(sum(dv)/len(dv),2))
import json; json.dump({"polys":polys},open("/home/claude/gen/polys.json","w"))

