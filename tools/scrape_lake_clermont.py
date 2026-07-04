# === Clermont (Lake County) motivated-seller scraper ========================
# Source: Lake County Property Appraiser GIS (public, fully queryable — no firewall).
#   https://gis.lakecountyfl.gov/lakegis/rest/services/PropertyAppraiser/FieldMap/MapServer/21  (leaf: full parcel table)
# Layer 21 fields (verified): OwnerName, OwnerAddress/City/State/Zip (mailing), PropertyAddress,
#   TotalJustValue/LandValue/BuildingValue, LastSalePrice/LastSaleDate, Exemptions (homestead: non-null=homesteaded),
#   LandUseDescription ('SINGLE FAMILY'), DeedAcreage, YearBuilt, ParcelNumber, AltKey.
# GOTCHA: the server rate-limits a burst of requests (403 / WAF page) — this makes only 1-2 spaced requests.
#   Run:  python tools/scrape_lake_clermont.py   (re-run after a few min if it 403s)
import sys, json, re, time, datetime, urllib.request, urllib.parse
REPO='C:/Users/rmaca/OneDrive/Documents/GitHub/macoequitypartners'
B='https://gis.lakecountyfl.gov/lakegis/rest/services/PropertyAppraiser/FieldMap/MapServer/21/query'
UA={'User-Agent':'Mozilla/5.0','Referer':'https://gis.lakecountyfl.gov/gisweb/'}
ENV='-81.82,28.48,-81.68,28.62'   # Clermont / south-Lake envelope (WGS84)
NOW=datetime.date.today()
# Only motivated owners, server-side (LIKE works here). Non-homestead single-family in the flip band.
OWNER="(OwnerName LIKE '%ESTATE%' OR OwnerName LIKE '%HEIRS%' OR OwnerName LIKE '%TRUST%' OR OwnerName LIKE '% LLC%' OR OwnerName LIKE '% INC%' OR OwnerName LIKE '%CORP%')"
WHERE="LandUseDescription='SINGLE FAMILY' AND Exemptions IS NULL AND TotalJustValue>=60000 AND TotalJustValue<=450000 AND "+OWNER
FLDS="OwnerName,OwnerAddress,OwnerCity,OwnerState,OwnerZip,PropertyAddress,TotalJustValue,LandValue,BuildingValue,DeedAcreage,YearBuilt,LastSaleDate,LastSalePrice,ParcelNumber,AltKey,OBJECTID"

def q(offset):
    p={'where':WHERE,'geometry':ENV,'geometryType':'esriGeometryEnvelope','inSR':'4326',
       'spatialRel':'esriSpatialRelIntersects','outFields':FLDS,'orderByFields':'OBJECTID',
       'returnGeometry':'false','resultRecordCount':1000,'resultOffset':offset,'f':'json'}
    url=B+'?'+urllib.parse.urlencode(p)
    for t in range(4):
        try:
            r=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=90)
            txt=r.read().decode('utf-8','replace')
            if txt.lstrip()[:1]!='{': raise RuntimeError('non-JSON (rate-limited?)')
            return json.loads(txt)
        except Exception as e:
            print('   retry %d (%s)'%(t+1,str(e)[:70])); time.sleep([30,90,180][t] if t<3 else 180)
    return None

def num(v):
    try: return float(str(v).replace(',',''))
    except: return 0.0
def classify(o):
    o=' '+(o or '').upper()+' '
    if ' LLC ' in o or ' INC ' in o or 'CORP' in o or 'COMPANY' in o or ' LP ' in o or ' LTD ' in o: return 'entity'
    if 'ESTATE' in o or ' HEIRS' in o or o.rstrip().endswith(' EST'): return 'probate'
    if 'TRUST' in o or ' TR ' in o or o.rstrip().endswith(' TR') or ' TRS ' in o: return 'trust'
    return 'other'
def tc(s):
    s=(s or '').strip()
    return re.sub(r'\b([A-Za-z])([A-Za-z]*)', lambda m:m.group(1).upper()+m.group(2).lower(), s)
def strap(p): return (p or '').strip()
def styr(ms):
    try: return datetime.datetime.utcfromtimestamp(int(ms)/1000).year if ms else None
    except: return None

feats=[]; off=0
while True:
    d=q(off)
    if d is None:
        if not feats: raise SystemExit('Lake server unreachable / rate-limited — wait a few minutes and re-run.')
        print('   page failed — baking what we have (%d)'%len(feats)); break
    f=d.get('features',[])
    if off==0 and not f: raise SystemExit('0 rows — check the filter/envelope.')
    feats+=[x['attributes'] for x in f]; print('   ...%d parcels'%len(feats))
    if len(f)<1000 or not d.get('exceededTransferLimit'): break
    off+=1000; time.sleep(6)
    if off>=3000: print('   cap 3k'); break

base={'probate':42,'entity':26,'trust':22,'other':8}
leads=[]
for a in feats:
    own=(a.get('OwnerName') or '').strip(); addr=(a.get('PropertyAddress') or '').strip()
    if not own or not addr: continue
    cls=classify(own)
    if cls=='other': continue
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
    leads.append({'pid':strap(a.get('ParcelNumber') or a.get('AltKey')), 'st':strap(a.get('ParcelNumber') or a.get('AltKey')),
        'a':tc(addr), 'c':'Clermont', 'z':'', 'o':own, 'mkt':jv, 'asr':jv, 'tax':jv, 'bld':bld,
        'lnd':(lnd if lnd else max(0,jv-bld)), 'lot':round(num(a.get('DeedAcreage')),2), 'tag':cls, 'sc':sc,
        'm1':tc(m1), 'm3':m3, 'mst':mst, 'oos':1 if oos else 0, 'abs':1 if absn else 0,
        'lsY':lsY, 'lsP':lsP, 'held':held, 'rt':None})

# de-dup by pid, prioritise probate>trust>entity then value, keep top 120
seen={}; uniq=[]
for l in leads:
    if l['pid'] and l['pid'] not in seen: seen[l['pid']]=1; uniq.append(l)
prio={'probate':3,'trust':2,'entity':1}
uniq.sort(key=lambda x:(-prio.get(x['tag'],0), -x['sc'], -x['mkt']))
pt=[x for x in uniq if x['tag']!='entity']
ent=[x for x in uniq if x['tag']=='entity'][:max(0,120-len(pt))]
final=(pt+ent)[:120]
final.sort(key=lambda x:-x['sc'])
markets=['Clermont']
meta={'county':'Lake','source':'Lake County Property Appraiser (gis.lakecountyfl.gov)','snapshot':str(NOW),
      'method':'Non-homestead single-family (LandUse SINGLE FAMILY, no exemption) owned by estate/trust/heirs/entity in the Clermont / south-Lake area, scored on owner-type, out-of-state/absentee mailing and hold length. Values = county just/market. Lake publishes no comp or code-violation feed, so ARV and violations are not available.',
      'markets':markets,'count':len(final)}
js=('// Lake County (Clermont) motivated-seller leads — generated %s by scrape_lake_clermont.py from the Lake County PA GIS.\n'%NOW
    +'window.LAKE_META='+json.dumps(meta)+';\n'
    +'window.LAKE_LEADS='+json.dumps(final,separators=(',',':'))+';\n')
open(REPO+'/lake-leads.js','w',encoding='utf-8',newline='').write(js)
print('wrote lake-leads.js — %d Clermont leads (%s)'%(len(final), {t:sum(1 for x in final if x['tag']==t) for t in ['probate','trust','entity']}))
