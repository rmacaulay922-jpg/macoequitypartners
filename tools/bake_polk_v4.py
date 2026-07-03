import json, re, datetime
RAW='C:/Users/rmaca/Downloads/polk_leads_v1.json'
ENR='C:/Users/rmaca/Downloads/polk_enrich_v1.json'
OUT='C:/Users/rmaca/OneDrive/Documents/GitHub/macoequitypartners/polk-leads.js'
raw=json.load(open(RAW)); enr=json.load(open(ENR)); NOW=datetime.date(2026,7,1)
def parse_loc(loc):
    m=re.match(r'^(.*?)\s{2,}([A-Z][A-Z .]+?)\s+(\d{5})(?:-\d+)?\s*$', loc.strip())
    if m: return m.group(1).strip().title(), m.group(2).strip().title(), m.group(3)
    m2=re.search(r'(\d{5})\s*$', loc); return loc.strip().title(), '', (m2.group(1) if m2 else '')
def classify(own):
    o=' '+own.upper()+' '
    if ' LLC ' in o or ' INC ' in o or 'CORP' in o or ' CO ' in o or 'COMPANY' in o or ' LP ' in o or ' LTD ' in o: return 'entity'
    if 'ESTATE OF' in o or ' HEIRS' in o or 'LIFE ESTATE' in o or 'LIFE EST ' in o or o.rstrip().endswith(' EST'): return 'probate'
    if 'TRUST' in o or o.rstrip().endswith(' TR') or ' TR ' in o: return 'trust'
    return 'other'
def strap(pid):
    p=re.sub(r'\D','',pid)
    return (p[0:2]+'-'+p[2:4]+'-'+p[4:6]+'-'+p[6:12]+'-'+p[12:18]) if len(p)==18 else pid
def mail_state(m3):
    m=re.search(r'\b([A-Z]{2})\s+\d{5}',(m3 or '').upper()); return m.group(1) if m else ''
def norm(s): return re.sub(r'[^A-Z0-9]','',(s or '').upper())
def yr(t):
    try: return datetime.date.fromtimestamp(t/1000).year
    except Exception: return None
leads=[]
for r in raw:
    pid,loc,own,mkt,asr,ex,tax,bld,ac=r
    if not mkt or mkt<40000: continue
    addr,city,zc=parse_loc(loc); tag=classify(own); bratio=(bld/mkt) if mkt else 1
    e=enr.get(pid) or {}; m=(e.get('m') or {}); s=(e.get('s') or {})
    m1=re.sub(r'\s+',' ',(m.get('m1') or '')).strip().title(); m3=re.sub(r'\s+',' ',(m.get('m3') or '')).strip().title()
    mst=mail_state(m.get('m3'))
    us_addr=bool(re.search(r'\b[A-Z]{2}\s+\d{5}', (m.get('m3') or '').upper()))
    foreign=bool(m3) and not us_addr
    oos=(bool(mst) and mst!='FL') or foreign
    absentee=(not oos) and bool(m1) and norm(m1)[:12]!=norm(addr)[:12]
    lt=s.get('lt') or {}; ls=s.get('ls') or {}
    ls_yr=yr(ls.get('t')) if ls else None; lt_yr=yr(lt.get('t')) if lt else None
    held=(NOW.year-ls_yr) if ls_yr else None
    recent_transfer=bool(lt_yr and lt_yr>=2023 and (lt.get('pr') or 999999)<=100)
    sc={'probate':42,'entity':26,'trust':22,'other':10}[tag]
    if oos: sc+=22
    elif absentee: sc+=12
    if held is not None: sc+= 18 if held>=25 else (12 if held>=15 else (6 if held>=8 else 0))
    if recent_transfer: sc+=8
    if bratio<0.5: sc+=16
    elif bratio<0.62: sc+=9
    if 120000<=mkt<=300000: sc+=15
    elif 80000<=mkt<120000 or 300000<mkt<=380000: sc+=8
    if ac and ac>0.45: sc+=5
    sc=min(sc,100)
    L={'pid':pid,'st':strap(pid),'a':addr,'c':city,'z':zc,'o':own.title(),
       'mkt':int(mkt),'asr':int(asr or 0),'tax':int(tax or 0),'bld':int(bld or 0),'lnd':max(0,int(mkt)-int(bld or 0)),'lot':round(ac,3) if ac else 0,
       'tag':tag,'sc':sc}
    if m1: L['m1']=m1
    if m3: L['m3']=m3
    if mst: L['mst']=mst
    elif foreign: L['mst']='Foreign'
    if oos: L['oos']=1
    elif absentee: L['abs']=1
    if ls_yr: L['lsY']=ls_yr; L['lsP']=int(ls.get('pr') or 0); L['held']=held
    if recent_transfer: L['rt']=lt_yr
    leads.append(L)
seen={}; uniq=[]
for l in sorted(leads,key=lambda x:(-x['sc'],-x['mkt'])):
    if l['pid'] in seen: continue
    seen[l['pid']]=1; uniq.append(l)
from collections import Counter
print("total:",len(uniq),"| OOS:",sum(1 for l in uniq if l.get('oos')),"| absentee:",sum(1 for l in uniq if l.get('abs')),"| local:",sum(1 for l in uniq if not l.get('oos') and not l.get('abs')))
print("foreign->OOS:",sum(1 for l in uniq if l.get('mst')=='Foreign'),"| max score:",max(l['sc'] for l in uniq))
meta={'source':'Polk County Property Appraiser (map.polkflpa.gov)','snapshot':'2026-07-01',
 'method':'Non-homestead single-family homes (DOR 0100) owned by an estate, trust, heirs, or investment entity across the farmed Polk submarkets. Enriched with owner mailing address and full sale history from the county service, then scored on absentee/out-of-state (incl. foreign) ownership, hold length, and recent estate transfers. Values = county market/just, assessed & taxable. Polk publishes no open comp or code-violation feed, so ARV and violation data are not available.',
 'markets':sorted(set(l['c'] for l in uniq)),'count':len(uniq),
 'tagLabels':{'probate':'Estate / probate','trust':'Trust-owned','entity':'LLC / entity','other':'Non-homestead'}}
out='// Polk County lead snapshot v4 — PA map service + mailing/sales enrichment (foreign-owner + score-cap fixes). See POLK_META.\n'
out+='window.POLK_META='+json.dumps(meta)+';\n'
out+='window.POLK_LEADS='+json.dumps(uniq,separators=(',',':'))+';\n'
open(OUT,'w',encoding='utf-8').write(out)
print("wrote polk-leads.js (%d KB)"%(len(out)//1024))
