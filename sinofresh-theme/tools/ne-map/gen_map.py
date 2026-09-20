#!/usr/bin/env python3
"""Generate professional NE-110m SVG map block and swap into front-page.html."""
import json, math, re

TOPO = json.load(open('/tmp/package/land-110m.json'))
tr = TOPO['transform']; sx, sy = tr['scale']; tx, ty = tr['translate']
arcs=[]
for a in TOPO['arcs']:
    x=y=0; pts=[]
    for dx,dy in a:
        x+=dx; y+=dy; pts.append((x*sx+tx, y*sy+ty))
    arcs.append(pts)
def rc(idxs):
    pts=[]
    for i in idxs:
        a = arcs[i] if i>=0 else list(reversed(arcs[~i]))
        if pts and pts[-1]==a[0]: pts.extend(a[1:])
        else: pts.extend(a)
    return pts
land=TOPO['objects']['land']
flat=[]
for g in land['geometries']:
    for poly in g['arcs']:
        flat.append([rc(r) for r in poly])
kept=[p for p in flat if max(q[1] for q in p[0]) > -60]

def dp(points, tol):
    n=len(points)
    if n < 4: return points
    keep=[False]*n; keep[0]=keep[n-1]=True
    stack=[(0,n-1)]
    while stack:
        a,b=stack.pop()
        if b<=a+1: continue
        ax,ay=points[a]; bx,by=points[b]
        dx,dy=bx-ax,by-ay
        degenerate=(dx==0 and dy==0)
        dmax,imax=-1.0,-1
        for i in range(a+1,b):
            px,py=points[i]
            d=math.hypot(px-ax,py-ay) if degenerate else abs(dx*(py-ay)-dy*(px-ax))/math.hypot(dx,dy)
            if d>dmax: dmax,imax=d,i
        if dmax>tol:
            keep[imax]=True; stack.append((a,imax)); stack.append((imax,b))
    return [p for p,k in zip(points,keep) if k]

W, TOP, BOT = 1000.0, 84.0, -56.0
H = 389
def P(lon,lat):
    return round((lon+180)/360*W,1), round((TOP-lat)/(TOP-BOT)*H,1)

TOL=0.2
land_parts=[]
def split_antimeridian(pts):
    """把跨 180° 经线的环拆成多个子环，边界处插值到 lon=±180。"""
    segs=[]; cur=[pts[0]]
    for i in range(len(pts)-1):
        a=pts[i]; b=pts[i+1]
        if abs(b[0]-a[0])>180:
            dlon=b[0]-a[0]
            # 闭合点用离开侧（a 所在一侧），新子环起点用进入侧（b 所在一侧）
            lon_exit=-180.0 if dlon>0 else 180.0
            lon_enter=-lon_exit
            t=(lon_exit-a[0])/(lon_enter-a[0])
            lat_cross=a[1]+t*(b[1]-a[1])
            cur.append((lon_exit,lat_cross))
            segs.append(cur)
            cur=[(lon_enter,lat_cross), b]
        else:
            cur.append(b)
    segs.append(cur)
    return segs

for p in kept:
    for r in p:
        pts = r[:-1] if r[0]==r[-1] else r[:]
        if len(pts) < 4: continue
        ds=[]
        for seg in split_antimeridian(pts):
            if len(seg) < 4: continue
            sr = dp(seg, TOL)
            if len(sr) < 3: continue
            coords=[P(*q) for q in sr]
            xs=[c[0] for c in coords]; ys=[c[1] for c in coords]
            if max(xs)-min(xs) > 500 and max(ys)-min(ys) < 8:
                continue  # NE 110m sliver artifact: full-width flat strip in open ocean
            ds.append('M'+'L'.join(f'{x},{y}' for x,y in coords)+'Z')
        if not ds: continue
        land_parts.append('<path class="sf-map__land" d="'+''.join(ds)+'"/>')
land_svg=''.join(land_parts)

COUNTRIES = [
    ('United States',-97,38,True),('Canada',-106,56,False),('Mexico',-102,23,False),
    ('United Kingdom',-2,54,False),('Germany',10,51,True),('France',2,46,False),
    ('Netherlands',5,52,False),('Belgium',4,51,False),('Spain',-4,40,False),
    ('Italy',12,42,False),('Portugal',-8,39,False),('Ireland',-8,53,False),
    ('Denmark',10,56,False),('Sweden',15,62,False),('Norway',10,62,False),
    ('Finland',26,64,False),('Poland',20,52,False),('Czech Republic',15,50,False),
    ('Austria',14,47,False),('Switzerland',8,47,False),
    ('Australia',134,-25,True),('New Zealand',174,-41,False),('Japan',138,36,True),
    ('South Korea',128,36,False),('Singapore',104,1,False),('Malaysia',102,4,False),
    ('Thailand',101,15,False),('Vietnam',108,16,False),('Indonesia',118,-2,False),
    ('Philippines',122,13,False),('India',77,20,False),('United Arab Emirates',54,24,False),
    ('Saudi Arabia',45,24,False),
]
ox,oy=P(116,40)
parts=[]
# origin: two halo rings + main dot (r=8)
parts.append(f'<circle class="sf-map__halo sf-map__pulse" cx="{ox}" cy="{oy}" r="13" style="animation-delay:-.2s"/>')
parts.append(f'<circle class="sf-map__halo sf-map__halo--far sf-map__pulse" cx="{ox}" cy="{oy}" r="20" style="animation-delay:-.6s"/>')
parts.append(f'<circle class="sf-map__dot sf-map__dot--origin sf-map__pulse" cx="{ox}" cy="{oy}" r="8"/>')
# 33 destinations; the 4 arc-anchor countries get r=4.5 + dest class
for idx,(name,lon,lat,is_dest) in enumerate(COUNTRIES):
    x,y=P(lon,lat)
    delay=round(-0.15*idx,2)
    if is_dest:
        parts.append(f'<circle class="sf-map__dot sf-map__dot--dest sf-map__pulse" cx="{x}" cy="{y}" r="4.5" style="animation-delay:{delay}s"/>')
    else:
        parts.append(f'<circle class="sf-map__dot sf-map__pulse" cx="{x}" cy="{y}" r="3" style="animation-delay:{delay}s"/>')
dots_svg=''.join(parts)

svg=(f'<svg class="sf-map" viewBox="0 0 {int(W)} {H}" role="img" '
     f'aria-label="World map showing SINO FRESH export markets: 33 countries across North America, Europe, Oceania and Asia, with China as the manufacturing origin" '
     f'focusable="false"><title>SINO FRESH global reach: exporting to 33 countries across four continents</title>'
     f'{land_svg}{dots_svg}</svg>')

print('land rings:', len(land_parts), '| dots:', len(COUNTRIES)+3, '| svg bytes:', len(svg))

tpl='/Users/meng/WorkBuddy/sinofresh外贸网站建设/sinofresh-theme/templates/front-page.html'
h=open(tpl).read()
m=re.search(r'<svg class="sf-map".*?</svg>', h, re.S)
assert m, 'old svg not found'
h=h[:m.start()]+svg+h[m.end():]
open(tpl,'w').write(h)
print('front-page.html updated; new size:', len(h))
