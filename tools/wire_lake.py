# Wire the Lake County (Clermont) market into portal.html. Idempotent — run after lake-leads.js exists.
import io, sys
P=r"C:\Users\rmaca\OneDrive\Documents\GitHub\macoequitypartners\portal.html"
s=io.open(P,encoding='utf-8').read()
if 'lake-leads.js' in s:
    print('already wired'); sys.exit(0)
def once(old,new):
    global s
    if s.count(old)!=1: raise SystemExit('anchor not unique/found: '+old[:48])
    s=s.replace(old,new,1)
once("var COLLIER_REC={pa:'https://www.collierappraiser.com/',",
     "var LAKE_REC={pa:'https://www.lakecopropappr.com/',tax:'https://www.laketax.com/',probate:'https://lakecountyclerk.org/',code:'https://www.lakecountyfl.gov/offices/code_enforcement/',records:'https://lakecountyclerk.org/official_records/'};\n"
     "var COLLIER_REC={pa:'https://www.collierappraiser.com/',")
once("  collier:{label:'Collier · Naples',        kind:'leads', src:'COLLIER_LEADS', meta:'COLLIER_META', rec:COLLIER_REC, tabs:['brief','polk','pipeline']},\n",
     "  collier:{label:'Collier · Naples',        kind:'leads', src:'COLLIER_LEADS', meta:'COLLIER_META', rec:COLLIER_REC, tabs:['brief','polk','pipeline']},\n"
     "  lake:   {label:'Lake · Clermont',         kind:'leads', src:'LAKE_LEADS',    meta:'LAKE_META',    rec:LAKE_REC,    tabs:['brief','polk','pipeline']},\n")
once('        <option value="collier">Market: Collier · Naples</option>\n',
     '        <option value="collier">Market: Collier · Naples</option>\n        <option value="lake">Market: Lake · Clermont</option>\n')
once('<script src="polk-leads.js?v=5"></script>',
     '<script src="polk-leads.js?v=5"></script>\n<script src="lake-leads.js?v=1"></script>')
io.open(P,'w',encoding='utf-8',newline='').write(s)
print('Lake market wired')
