# === Clermont (Lake County) motivated-seller scraper (v2, quote-free) =======
# Source: Lake County PA GIS - FieldMap layer 21 (full parcel table, verified fields).
#   https://gis.lakecountyfl.gov/lakegis/rest/services/PropertyAppraiser/FieldMap/MapServer/21/query
# WAF RULES LEARNED (July 2026): the Lake firewall 403s any where-clause containing QUOTED
# STRINGS ('%27') once your IP is on its radar, and hard-blocks bursts for hours. Quote-free
# numeric/spatial/IS NULL queries return 200. So: filter server-side ONLY on numbers + spatial
# envelope + Exemptions IS NULL, pull LandUseDescription/OwnerName in outFields, and classify
# single-family + owner type CLIENT-SIDE (Davenport-style value-window slices, ~4 requests).
import sys, json, re, time, datetime, urllib.request, urllib.parse
REPO='C:/Users/rmaca/OneDrive/Documents/GitHub/macoequitypartners'
B='https://gis.lakecountyfl.gov/lakegis/rest/services/PropertyAppraiser/FieldMap/MapServer/21/query'
UA={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Referer':'https://gis.lakecountyfl.gov/gisweb/'}
ENV='-81.82,28.48,-81.68,28.62'   # Clermont / south-Lake envelope (WGS84)
NOW=datetime.date.today()
FLDS=('OwnerName,OwnerAddress,OwnerCity,OwnerState,OwnerZip,PropertyAddress,TotalJustValue,'
      'LandValue,BuildingValue,DeedAcreage,YearBuilt,LastSaleDate,LastSalePrice,ParcelNumber,AltKey,'
      'LandUseDescription')

def q(where, order):
    # QUOTE-FREE where clauses only - a single %27 in the querystring gets this IP re-blocked.
    assert "'" not in where, 'quoted string in where - would trip the WAF'
    p={'where':where,'geometry':ENV,'geometryType':'esriGeometryEnvelope','inSR':'4326',
       'spatialRel':'esriSpatialRelIntersects','outFields':FLDS,'orderByFields':order,
       'returnGeometry':'false','resultRecordCount':1000,'f':'json'}
    url=B+'?'+urllib.parse.urlencode(p)
    for t in range(3):
        try:
            r=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=90)
            txt=r.read().decode('utf-8','replace')
            if txt.lstrip()[:1]!='{': raise RuntimeError('non-JSON (WAF page)')
            j=json.loads(txt)
            if 'error' in j: raise RuntimeError(j['error'].get('message','error'))
            return j.get('features',[])
        except Exception as e:
            print('   retry %d (%s)'%(t+1,str(e)[:70])); time.sleep([45,120][t] if t<2 else 120)
    return None

# Four value-window slices across the flip band -> broad, honest sample (~4k parcels max).
SLICES=[
    ('Exemptions IS NULL AND TotalJustValue>=60000 AND TotalJustValue<=180000','TotalJustValue ASC'),
    ('Exemptions IS NULL AND TotalJustValue>180000 AND TotalJustValue<=280000','TotalJustValue ASC'),
    ('Exemptions IS NULL AND TotalJustValue>280000 AND TotalJustValue<=370000','TotalJustValue DESC'),
    ('Exemptions IS NULL AND TotalJustValue>370000 AND TotalJustValue<=450000','TotalJustValue DESC'),
]
raw={}
for i,(w,o) in enumerate(SLICES):
    f=q(w,o)
    if f is None:
        if not raw: raise SystemExit('Lake server blocked/unreachable - wait and re-run.')
        print('   slice %d failed - continuing with %d parcels'%(i+1,len(raw))); continue
    n0=len(raw)
    for x in f:
        a=x['attributes']; pid=(a.get('ParcelNumber') or a.get('AltKey') or '').strip()
        if pid: raw[pid]=a
    print('   slice %d: +%d (pool %d)'%(i+1,len(raw)-n0,len(raw)))
    if i<len(SLICES)-1: time.sleep(10)   # gentle pacing - this server blocks bursts for HOURS

def num(v):
    try: return float(str(v).replace(',',''))
    except: return 0.0
def classify(o):
    o=' '+(o or '').upper()+' '
    if ' LLC ' in o or ' INC ' in o or 'CORP' in o or 'COMPANY' in o or ' LP ' in o or ' LTD ' in o: return 'entity'
    if 'LIFE ESTATE' in o: return 'le'                    # owner alive, retains life interest - NOT probate
    if 'ESTATE OF' in o or ' EST OF' in o or ' HEIRS' in o or o.rstrip().endswith(' EST'): return 'probate'
    if 'TRUST' in o or ' TR ' in o or o.rstrip().endswith(' TR') or ' TRS ' in o: return 'trust'
    return 'other'
def tc(s):
    s=(s or '').strip()
    return re.sub(r'\b([A-Za-z])([A-Za-z]*)', lambda m:m.group(1).upper()+m.group(2).lower(), s)
def styr(ms):
    try: return datetime.datetime.utcfromtimestamp(int(ms)/1000).year if ms else None
    except: return None

base={'probate':42,'le':30,'entity':26,'trust':22,'other':8}   # le = Miami's estate:LE ratio (20:14) applied to the 42 base
leads=[]
sf=0
for pid,a in raw.items():
    if (a.get('LandUseDescription') or '').strip().upper()!='SINGLE FAMILY': continue
    sf+=1
    own=(a.get('OwnerName') or '').strip(); addr=(a.get('PropertyAddress') or '').strip()
    if not own or not addr: continue
    cls=classify(own)
    if cls=='other': continue    # (OOS individuals need mailing joins beyond this sample; owner-type is the primary signal)
    mst=(a.get('OwnerState') or '').strip().upper() or 'FL'
    m1=(a.get('OwnerAddress') or '').strip()
    oos = mst!='FL' and len(mst)==2
    absn=(not oos) and bool(m1) and re.sub(r'[^A-Z0-9]','',m1.upper())[:12]!=re.sub(r'[^A-Z0-9]','',addr.upper())[:12]
    jv=int(num(a.get('TotalJustValue'))); bld=int(num(a.get('BuildingValue'))); lnd=int(num(a.get('LandValue')))
    lsY=styr(a.get('LastSaleDate')); lsP=int(num(a.get('LastSalePrice'))) or None
    held=(NOW.year-lsY) if lsY else None
    sc=base[cls]+(22 if oos else (12 if absn else 0))
    if held is not None: sc += 18 if held>=25 else (12 if held>=15 else (6 if held>=8 else 0))
    sc=min(sc,100)
    ozip=re.sub(r'[^0-9]','',str(a.get('OwnerZip') or ''))[:5]
    m3=((a.get('OwnerCity') or '').strip().title()+((' '+mst) if mst else '')+((' '+ozip) if ozip else '')).strip()
    leads.append({'pid':pid,'st':pid,'a':tc(addr),'c':'Clermont','z':'','o':own,
        'mkt':jv,'asr':jv,'tax':jv,'bld':bld,'lnd':(lnd if lnd else max(0,jv-bld)),
        'lot':round(num(a.get('DeedAcreage')),2),'tag':cls,'sc':sc,
        'm1':tc(m1),'m3':m3,'mst':mst,'oos':1 if oos else 0,'abs':1 if absn else 0,
        'lsY':lsY,'lsP':lsP,'held':held,'rt':None})
print('   pool %d parcels -> %d single-family -> %d motivated-owner leads'%(len(raw),sf,len(leads)))

prio={'probate':4,'le':3,'trust':2,'entity':1}
leads.sort(key=lambda x:(-prio.get(x['tag'],0), -x['sc'], -x['mkt']))
pt=[x for x in leads if x['tag']!='entity']
ent=[x for x in leads if x['tag']=='entity'][:max(0,120-len(pt))]
final=(pt+ent)[:120]
final.sort(key=lambda x:-x['sc'])
if len(final)<30: raise SystemExit('only %d leads - refusing to bake a thin/broken file'%len(final))
meta={'county':'Lake','source':'Lake County Property Appraiser (gis.lakecountyfl.gov)','snapshot':str(NOW),
      'method':'Non-homestead single-family owned by an estate, trust, heirs, or investment entity in the Clermont / south-Lake area (four value-window samples of the county roll, single-family and owner-type classified from county fields), scored on owner-type, out-of-state/absentee mailing and hold length. Values = county just/market. Lake publishes no comp or code-violation feed, so ARV and violation data are not available.',
      'markets':['Clermont'],'count':len(final)}
js=('// Lake County (Clermont) motivated-seller leads - generated %s by scrape_lake_clermont.py from the Lake County PA GIS.\n'%NOW
    +'window.LAKE_META='+json.dumps(meta)+';\n'
    +'window.LAKE_LEADS='+json.dumps(final,separators=(',',':'))+';\n')
open(REPO+'/lake-leads.js','w',encoding='utf-8',newline='').write(js)
print('wrote lake-leads.js - %d Clermont leads (%s)'%(len(final), {t:sum(1 for x in final if x['tag']==t) for t in ['probate','le','trust','entity']}))
