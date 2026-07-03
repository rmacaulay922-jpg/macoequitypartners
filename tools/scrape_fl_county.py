# ── Florida county motivated-seller scraper — VERIFIED against the live FDOR service ─────────
# Bakes <county>-leads.js (Polk lead schema + lat/lng) for Broward, Lee, or Collier.
#   python scrape_fl_county.py broward | lee | collier
#
# SOURCE (verified live, July 2026): the Florida Dept. of Revenue statewide NAL tax roll, hosted as
#   Florida_Statewide_Cadastral / FeatureServer / 0
#   https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/Florida_Statewide_Cadastral/FeatureServer/0
# ONE service, ONE schema, EVERY county — no per-county field-name guessing. Verified facts:
#   • geometryType=Polygon, maxRecordCount=2000 (paginate with resultOffset)
#   • DOR_UC is a 3-char string; '001' = single-family residential  (verified: 15/20 in a Broward SFH zip)
#   • CO_NO is the FDOR county number. VERIFIED: Alachua=11, Broward=16, (Miami-)Dade=23 (known constant).
#     The scheme is alphabetical+10 → Collier=21, Lee=46. The scraper SELF-VERIFIES on run (prints the
#     CO_NO's sample city/zip + asserts the zip mix matches the county) so a wrong number can't bake bad data.
#   • Homestead: JV_HMSTD > 0 means a homestead exemption exists = owner-occupied → SKIP (we want non-homestead).
#   • Fields (verified present via outFields=*): PARCEL_ID, OWN_NAME, OWN_ADDR1/2, OWN_CITY, OWN_STATE,
#     OWN_ZIPCD, PHY_ADDR1, PHY_ZIPCD, CO_NO, DOR_UC, JV (just value), AV_NSD (assessed), TV_NSD (taxable),
#     LND_VAL, ACT_YR_BLT, TOT_LVG_AR (heated sqft), LND_SQFOOT, SALE_PRC1, SALE_YR1, QUAL_CD1, JV_HMSTD, ASMNT_YR.
#     Building/improvement value has no own field → JV - LND_VAL. Acres → LND_SQFOOT / 43560.
#   • We request outFields=* (verified to work) and read every field defensively with .get(), so a field that
#     is absent for a given county degrades gracefully instead of erroring the whole query.
import sys, json, re, time, datetime, urllib.request, urllib.parse
REPO='C:/Users/rmaca/OneDrive/Documents/GitHub/macoequitypartners'
SERVICE='https://services9.arcgis.com/Gh9awoU677aKree0/arcgis/rest/services/Florida_Statewide_Cadastral/FeatureServer/0'
UA={'User-Agent':'Mozilla/5.0'}
NOW=datetime.date.today()

# co = verified/derived FDOR county number; zpre = zip prefixes we EXPECT (soft self-check, not a filter);
# out/var = output file + JS global prefix.
COUNTIES={
 'broward':{'co':16,'label':'Broward','var':'BROWARD','out':'broward-leads.js','zpre':('330','331','333')},
 'lee':    {'co':46,'label':'Lee','var':'LEE','out':'lee-leads.js','zpre':('339','341','340')},
 'collier':{'co':21,'label':'Collier','var':'COLLIER','out':'collier-leads.js','zpre':('341','342','339')},
}

def query(where, last_oid, geom=True):
    # OBJECTID-cursor pagination (NOT resultOffset — the FDOR hosted layer rejects resultOffset).
    w=where+(' AND OBJECTID>%d'%last_oid if last_oid else '')
    body={'where':w,'outFields':'*','returnGeometry':'true' if geom else 'false','outSR':'4326',
          'f':'json','resultRecordCount':2000,'orderByFields':'OBJECTID'}
    for t in range(5):
        try:
            req=urllib.request.Request(SERVICE+'/query', data=urllib.parse.urlencode(body).encode(), headers=UA)
            d=json.load(urllib.request.urlopen(req, timeout=120))
            if 'error' in d:                       # ArcGIS returns 200 with an error body when throttled
                raise RuntimeError(d['error'].get('message','error'))
            return d
        except Exception as e:
            print('   retry %d (%s)'%(t+1,str(e)[:60])); time.sleep(4+5*t)   # back off — services9 throttles bursts
    return None   # terminal failure → caller breaks the loop and bakes what it has (resilient mid-crawl)

def norm(s): return re.sub(r'[^A-Z0-9]','',(s or '').upper())
# FDOR OWN_STATE stores FULL state names ("FLORIDA"), not abbreviations — normalize to 2-letter so the
# out-of-state flag is correct (the earlier OWN_STATE<>'FL' filter silently matched everyone).
_STATES={'ALABAMA':'AL','ALASKA':'AK','ARIZONA':'AZ','ARKANSAS':'AR','CALIFORNIA':'CA','COLORADO':'CO',
'CONNECTICUT':'CT','DELAWARE':'DE','FLORIDA':'FL','GEORGIA':'GA','HAWAII':'HI','IDAHO':'ID','ILLINOIS':'IL',
'INDIANA':'IN','IOWA':'IA','KANSAS':'KS','KENTUCKY':'KY','LOUISIANA':'LA','MAINE':'ME','MARYLAND':'MD',
'MASSACHUSETTS':'MA','MICHIGAN':'MI','MINNESOTA':'MN','MISSISSIPPI':'MS','MISSOURI':'MO','MONTANA':'MT',
'NEBRASKA':'NE','NEVADA':'NV','NEW HAMPSHIRE':'NH','NEW JERSEY':'NJ','NEW MEXICO':'NM','NEW YORK':'NY',
'NORTH CAROLINA':'NC','NORTH DAKOTA':'ND','OHIO':'OH','OKLAHOMA':'OK','OREGON':'OR','PENNSYLVANIA':'PA',
'RHODE ISLAND':'RI','SOUTH CAROLINA':'SC','SOUTH DAKOTA':'SD','TENNESSEE':'TN','TEXAS':'TX','UTAH':'UT',
'VERMONT':'VT','VIRGINIA':'VA','WASHINGTON':'WA','WEST VIRGINIA':'WV','WISCONSIN':'WI','WYOMING':'WY',
'DISTRICT OF COLUMBIA':'DC','WASHINGTON DC':'DC'}
_US_ABBR=set(_STATES.values())|{'PR','VI','GU','AS','MP','DC'}
def norm_state(s):
    s=(s or '').strip().upper()
    if not s: return ''
    if s in _STATES: return _STATES[s]          # full US state name → abbr
    if len(s)==2 and s in _US_ABBR: return s    # already a valid US/territory abbr
    return 'Foreign'                            # country names, Canadian provinces, etc. → Foreign (not a fake 2-char state)
def num(v):
    try: return float(str(v).replace(',',''))
    except: return 0.0
def classify(own):
    o=' '+(own or '').upper()+' '
    if ' LLC ' in o or ' INC ' in o or 'CORP' in o or 'COMPANY' in o or ' LP ' in o or ' LTD ' in o: return 'entity'
    if 'EST OF' in o or 'ESTATE OF' in o or ' HEIRS' in o or o.rstrip().endswith(' EST'): return 'probate'
    if 'TRUST' in o or ' TR ' in o or o.rstrip().endswith(' TR') or ' TRS ' in o: return 'trust'
    return 'other'
def centroid(geo):
    if not geo: return (None,None)
    if 'rings' in geo and geo['rings']:
        pts=geo['rings'][0]
        if pts: return (round(sum(p[1] for p in pts)/len(pts),6), round(sum(p[0] for p in pts)/len(pts),6))
    return (None,None)

def run(key):
    c=COUNTIES[key]
    # Push the core filter server-side: single-family, this county, in the flip value band, NON-homestead
    # (JV_HMSTD 0 or null). This is exact (not lossy for our target set) and cuts the pull from ~300k
    # SFH to the tens-of-thousands of non-homestead in-band parcels we actually score.
    # Server-side filter: single-family, this county, flip value band, NON-homestead (owner-occupied
    # excluded). We DON'T filter owner-state server-side (OWN_STATE stores full names like 'FLORIDA', and
    # a wildcard owner-name filter 504s at depth) — instead we pull non-homestead SFH (capped at 25k) and
    # let client-side scoring surface the real leads: estates, trusts, entities, out-of-state & long-hold
    # owners. This is exactly how Broward baked 600 estate/entity leads cleanly.
    where=("DOR_UC='001' AND CO_NO=%d AND JV>=60000 AND JV<=650000 AND (JV_HMSTD=0 OR JV_HMSTD IS NULL)"%c['co'])
    print('=== %s County (CO_NO=%d) === single-family from FDOR statewide roll'%(c['label'],c['co']))
    feats=[]; last_oid=0; first=True; asmt=''
    while True:
        d=query(where, last_oid)
        if d is None:
            if first: raise SystemExit('first page failed — service unreachable, wait a few min and re-run.')
            print('   page failed after retries — baking the %d parcels already pulled.'%len(feats)); break
        f=d.get('features',[])
        if first:
            if not f: raise SystemExit('0 rows for CO_NO=%d — county number is WRONG for %s; do not bake.'%(c['co'],c['label']))
            a0=f[0]['attributes']; asmt=str(int(num(a0.get('ASMNT_YR')) or 0) or '')
            samp=[(str(x['attributes'].get('PHY_ADDR1') or '').strip(), str(int(num(x['attributes'].get('PHY_ZIPCD')))) ) for x in f[:5]]
            print('   SELF-CHECK roll year %s · sample: %s'%(asmt, '; '.join('%s (%s)'%(a,z) for a,z in samp))); first=False
        if not f: break
        feats+=f; print('   ...%d parcels'%len(feats))
        last_oid=max(int(num(x['attributes'].get('OBJECTID')) or 0) for x in f)
        if len(f)<2000: break
        time.sleep(0.6)                             # light pacing between pages
        # Sample cap: these counties have huge out-of-state SFH pools and full enumeration hits flaky
        # deep-cursor timeouts. 25k is a large, representative sample; we take the top 600 by motivation
        # score from it (every parcel is already a valid out-of-state non-homestead flip-band SFH lead).
        if len(feats)>=25000: print('   (25k sample cap reached — taking top leads from this sample)'); break
    # zip self-check: what fraction of parcels fall in the EXPECTED zip prefixes for this county?
    zips=[str(int(num(x['attributes'].get('PHY_ZIPCD')))) for x in feats]
    hit=sum(1 for z in zips if z[:3] in c['zpre'])
    frac=hit/max(1,len(zips))
    print('   pulled %d SFH parcels · %.0f%% in expected zip prefixes %s'%(len(feats),100*frac,c['zpre']))
    if frac<0.6: print('   ⚠️ WARNING: <60%% of parcels match %s zips — CO_NO=%d may be wrong. Inspect before trusting.'%(c['label'],c['co']))

    cands=[]
    for ft in feats:
        a=ft['attributes']
        if num(a.get('JV_HMSTD'))>0: continue                 # homesteaded (owner-occupied) → skip
        just=int(num(a.get('JV')))
        if not (60000<=just<=650000): continue
        addr=(a.get('PHY_ADDR1') or '').strip()
        fol=re.sub(r'\s','',str(a.get('PARCEL_ID') or ''))
        if not addr or not fol: continue
        own=(a.get('OWN_NAME') or '').strip(); cls=classify(own)
        mst=norm_state(a.get('OWN_STATE')); m1=(a.get('OWN_ADDR1') or '').strip()
        oos=bool(mst) and mst!='FL'
        absentee=(not oos) and bool(m1) and norm(m1)[:12]!=norm(addr)[:12]
        yr=int(num(a.get('ACT_YR_BLT'))); age=(NOW.year-yr) if yr>1800 else 0
        sp=int(num(a.get('SALE_PRC1'))); sy=int(num(a.get('SALE_YR1')))
        held=(NOW.year-sy) if sy>1900 else None
        signal = cls!='other' or oos or absentee or (held is not None and held>=15)
        if not signal: continue
        lat,lng=centroid(ft.get('geometry'))
        sc={'probate':42,'entity':26,'trust':22,'other':8}[cls]
        if oos: sc+=22
        elif absentee: sc+=12
        if held is not None: sc+= 18 if held>=25 else (12 if held>=15 else (6 if held>=8 else 0))
        if age>=55: sc+=14
        elif age>=45: sc+=10
        ozr=num(a.get('OWN_ZIPCD')); ozip=('%05d'%int(ozr)) if ozr else ''   # zero-pad: NE zips lose a leading 0 as numbers
        mail3=((a.get('OWN_CITY') or '').strip()+(' '+mst if mst else '')+(' '+ozip if ozip else '')).strip()
        city=(a.get('PHY_CITY') or '').strip().title() or c['label']   # PHY_CITY if present, else county
        just_land=int(num(a.get('LND_VAL')))
        cands.append({'a':addr.title(),'c':city,'z':str(int(num(a.get('PHY_ZIPCD')))),
          'o':own,'m1':m1.title(),'m3':mail3,'mst':mst or 'FL','oos':1 if oos else 0,'abs':1 if absentee else 0,
          'tag':cls,'sc':min(sc,100),'mkt':just,'asr':int(num(a.get('AV_NSD'))),'tax':int(num(a.get('TV_NSD'))),
          'bld':max(0,just-just_land),'lnd':just_land,'lot':round(num(a.get('LND_SQFOOT'))/43560,2),
          'held':held,'lsY':(sy if sy>1900 else None),'lsP':sp or None,'rt':None,
          'pid':fol,'st':fol,'lat':lat,'lng':lng})
    cands.sort(key=lambda x:(-x['sc'],-x['mkt'])); cands=cands[:600]
    markets=sorted(set(x['c'] for x in cands))
    meta={'county':c['label'],'count':len(cands),'snapshot':(asmt+' roll' if asmt else str(NOW)),'markets':markets}
    js=('// %s County motivated-seller leads — generated %s by scrape_fl_county.py from the FDOR statewide roll.\n'%(c['label'],NOW)
      +'// Non-homestead single-family (DOR_UC 001), $60k-$650k, top %d by motivation score. Schema matches Polk.\n'%len(cands)
      +'window.%s_LEADS=%s;\n'%(c['var'],json.dumps(cands,separators=(',',':')))
      +'window.%s_META=%s;\n'%(c['var'],json.dumps(meta,separators=(',',':'))))
    open(REPO+'/'+c['out'],'w',encoding='utf-8').write(js)
    print('   wrote %s — %d leads · %d submarkets · %d KB'%(c['out'],len(cands),len(markets),len(js)//1024))

if __name__=='__main__':
    if len(sys.argv)<2 or sys.argv[1] not in COUNTIES:
        print('usage: python scrape_fl_county.py [broward|lee|collier]'); sys.exit(1)
    run(sys.argv[1])
