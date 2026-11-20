import math, random, os, sys, collections
seed = int(sys.argv[2]) if len(sys.argv)>2 else 11
random.seed(seed)
OUT = sys.argv[1]
STEP_X, STEP_Y = 4.0, 4.0
NX, NY = int(360/STEP_X), int(180/STEP_Y)

# ---- landmasses: name, lon, lat, rx, ry (degrees), biome weights (forest, farm, mountain, desert, polar)
CONT = [("Ashfall",    55, 32, 38, 28, dict(forest=2, farm=2, mountain=3, desert=5, polar=0, vortex=1), "DESERT"),
        ("Thornmarch", 150,  8, 42, 30, dict(forest=6, farm=3, mountain=2, desert=1, polar=0, vortex=0), "JUNGLE"),
        ("Gloamreach", 250,-12, 40, 30, dict(forest=4, farm=2, mountain=3, desert=2, polar=1, vortex=2), "FOREST"),
        ("Cinderspine",330, 42, 26, 22, dict(forest=2, farm=1, mountain=5, desert=1, polar=3, vortex=2), "MOUNT"),
        ("Shards",     105,-50, 34, 16, dict(forest=1, farm=1, mountain=4, desert=2, polar=3, vortex=2), "POLAR"),
        ("Veilmoor",   200, 50, 24, 18, dict(forest=5, farm=2, mountain=2, desert=0, polar=2, vortex=2), "FOREST"),
        ("Drowned Reach",300,-45,26, 16, dict(forest=2, farm=2, mountain=4, desert=1, polar=2, vortex=3), "MOUNT")]
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
def land_val(lon,lat):
    sc=[]
    for k,c in enumerate(CONT):
        n,cx,cy,rx,ry,_,_f=c
        rx*=1.18; ry*=1.18
        dx=(lon-cx+180)%360-180; dy=lat-cy
        d=math.hypot(dx/rx,dy/ry)
        sc.append((1.0-d*0.72 + (n_coast(lon,lat)-0.5)*0.9 + (n_fine(lon,lat)-0.5)*0.35, ("c",k)))
    for k,(cx,cy,rx,ry) in enumerate(ISL):
        dx=(lon-cx+180)%360-180; dy=lat-cy
        d=math.hypot(dx/rx,dy/ry)
        sc.append((1.0-d*0.8 + (n_fine(lon,lat)-0.5)*0.5, ("i",k)))
    sc.sort(key=lambda t:-t[0])
    v,oid=sc[0]; v2=sc[1][0]
    own=CONT[oid[1]] if oid[0]=="c" else None
    # channel between two landmasses
    if v2>0.0 and v-v2<GAP: v=-9
    return v, own, oid

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
BIOMES=["forest","farm","mountain","desert","polar","vortex"]
def pick(w):
    keys=[k for k in BIOMES if w.get(k,0)>0]; ws=[w[k] for k in keys]
    return random.choices(keys,ws)[0]
def climate(lat,w):
    w=dict(w); a=abs(lat)
    if a<50: w["polar"]=0
    if a>66: w["polar"]=w.get("polar",0)+9
    elif a>54: w["polar"]=w.get("polar",0)+2; w["mountain"]=w.get("mountain",0)+2
    return w
GENERIC=dict(forest=3,farm=2,mountain=3,desert=2,polar=1,vortex=1)

IDS=dict(forest=[1,11,3], farm=[2,19,21,22], mountain=[5,6,20,24], desert=[0,7,8,18,23], polar=[9,10], vortex=[4])  # tile ids in the Factions texture sheet
polys=[]; grid={}; stats=collections.defaultdict(collections.Counter)
# 1) land cells -> two triangles each (random diagonal)
tris=[]   # (vertex keys tuple of 3, centre lon, centre lat, owner, polar_cap)
for j in range(NY):
    for i in range(NX):
        clon=(i+.5)*STEP_X; clat=-90+(j+.5)*STEP_Y
        v,own,oid=land_val(clon,clat)
        cap = abs(clat)>=82
        if v<0.0 and not cap: continue
        p00,p10,p11,p01=(i,j),(i+1,j),(i+1,j+1),(i,j+1)
        pair=((p00,p10,p11),(p00,p11,p01)) if random.random()<.5 else ((p00,p10,p01),(p10,p11,p01))
        for t,tri in enumerate(pair):
            cx=sum(V[k][0] for k in tri)/3; cy=sum(V[k][1] for k in tri)/3
            tris.append(dict(v=tri,cx=cx,cy=cy,own=own,oid=(None if cap else oid),cap=cap,cell=(i,j),cl=None))
# 2) adjacency through shared edges; remove cells where two different landmasses touch (guarantees a sea channel)
def build_adj():
    edge=collections.defaultdict(list)
    for n,t in enumerate(tris):
        a_,b_,c_=t["v"]
        for e in ((a_,b_),(b_,c_),(c_,a_)): edge[frozenset(e)].append(n)
    adj=collections.defaultdict(set)
    for lst in edge.values():
        for x in lst:
            for y in lst:
                if x!=y: adj[x].add(y)
    return adj
for _round in range(8):
    adj=build_adj()
    kill=set()
    for x in adj:
        for y in adj[x]:
            if x<y and tris[x]["oid"] and tris[y]["oid"] and tris[x]["oid"]!=tris[y]["oid"]:
                kill.add(tris[x]["cell"]); kill.add(tris[y]["cell"])
    print("round",_round,"contacts to clear:",len(kill))
    if not kill: break
    tris=[t for t in tris if t["cell"] not in kill]
adj=build_adj()
# 3) grow clusters of 1-3 or 3-7 triangles
order=list(range(len(tris))); random.shuffle(order)
clusters=[]
for s0 in order:
    if tris[s0]["cl"] is not None: continue
    rr=random.random(); target=random.randint(2,5) if rr<.20 else (random.randint(6,12) if rr<.65 else random.randint(12,20))
    cid=len(clusters); members=[s0]; tris[s0]["cl"]=cid
    front=[s0]
    while len(members)<target:
        cand=[y for x in members for y in adj[x] if tris[y]["cl"] is None and tris[y]["cap"]==tris[s0]["cap"]]
        if not cand: break
        y=random.choice(cand); tris[y]["cl"]=cid; members.append(y)
    clusters.append(members)
# 4) single triangles only when there is no choice: fold singles into a neighbouring cluster
singles_left=0
for cid,m in enumerate(clusters):
    if len(m)==1:
        x=m[0]; nb=[tris[y]["cl"] for y in adj[x] if tris[y]["cl"]!=cid and tris[y]["cap"]==tris[x]["cap"] and len(clusters[tris[y]["cl"]])<24]
        if nb:
            to=random.choice(nb); clusters[to].append(x); tris[x]["cl"]=to; clusters[cid]=[]
        else: singles_left+=1
clusters=[m for m in clusters if m]
# 5) biome per cluster (voronoi patch + breakaways), emit polygons: merge a cell's two triangles into a quad when both are in the same cluster (50%)
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
    elif r<0.38: b=random.choice(["forest","farm","mountain","desert","vortex"])
    if cap: b="polar"
    for x in m:
        stats_key=(own[0] if own else "Isles")
        if not cap: stats[stats_key][b]+=1
        grid[(round(tris[x]["cx"]/STEP_X*2),round((tris[x]["cy"]+90)/STEP_Y*2))]=b
    byc=collections.defaultdict(list)
    for x in m: byc[tris[x]["cell"]].append(x)
    for cell,xs in byc.items():
        if len(xs)==2 and random.random()<.5:
            i,j=cell
            q=[V[(i,j)],V[(i+1,j)],V[(i+1,j+1)],V[(i,j+1)]]
            polys.append([random.choice(IDS[b])]+[c for p in q for c in p]); shapes["quad"]+=1
        else:
            for x in xs:
                polys.append([random.choice(IDS[b])]+[c for k in tris[x]["v"] for c in V[k]]); shapes["tri"]+=1
print("land (excl polar caps) %.0f%% of globe"%(100*sum(1 for t in tris if not t["cap"])/2/(NX*NY)));print("clusters:",len(clusters),"sizes:",dict(sorted(collections.Counter(len(m) for m in clusters).items())),"isolated singles:",singles_left)
print("shapes:",dict(shapes))

# ---- textures: each texture id mixes several battlescape terrains (names verified against vanilla xcom1 globe.rul)
MIX={ "forest":[("FOREST",45),("JUNGLE",25),("MOUNT",15),("CULTA",15)],
      "farm":  [("CULTA",50),("FOREST",20),("JUNGLE",10),("MOUNT",10),("DESERT",10)],
      "mountain":[("MOUNT",55),("FOREST",15),("POLAR",15),("DESERT",15)],
      "desert":[("DESERT",55),("MOUNT",25),("CULTA",10),("JUNGLE",10)],
      "polar": [("POLAR",60),("MOUNT",30),("FOREST",10)],
      "vortex":[("MOUNT",35),("DESERT",30),("FOREST",20),("JUNGLE",15)] }
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

yml=["globe:","  polygons:"]
for p in polys: yml.append("    - ["+", ".join(str(x) for x in p)+"]")
yml+=["  polylines:","    - [0, -85, 1, -85]"]+tx
os.makedirs(OUT+"/Ruleset",exist_ok=True)
open(OUT+"/Ruleset/globe.rul","w").write("\n".join(yml)+"\n")
open(OUT+"/metadata.yml","w").write("""id: RabblingsGeoscape
name: Rabblings Geoscape (globe test)
description: Replaces the Earth globe with a placeholder Rabblings world with mixed biomes. Test build, use a new game.
version: 0.0.6
author: Luke83
isMaster: false
master: xcom1
requiredExtendedVersion: "5.5.1"
""")
open(OUT+"/README.txt","w").write("""Rabblings Geoscape - globe test v0.0.6 (placeholder world, mixed biomes)
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
    s={grid[(x,y)] for x in range(i-6,i+7) for y in range(j-6,j+7) if (x,y) in grid}
    dv.append(len(s))
print("avg distinct biomes within ~12 deg:", round(sum(dv)/len(dv),2))
import json; json.dump({"polys":polys},open("/home/claude/gen/polys.json","w"))
