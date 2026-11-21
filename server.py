from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode
import json, os, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
from timezonefinder import TimezoneFinder
from engine import chart, transits

BASE_DIR = Path(__file__).resolve().parent
TZF = TimezoneFinder()
PORT = int(os.environ.get('PORT', '10000'))
USER_AGENT = 'Janmapatri/5.0 (public Vedic astrology chart calculator)'

def json_bytes(payload):
    return json.dumps(payload, ensure_ascii=False).encode('utf-8')

def resolve_selected(selected, birth_local):
    if not selected:
        raise ValueError('Please select a birthplace from the suggestions list.')
    display = selected.get('display_name','Selected place')
    # Known-city safety overrides: protects against malformed geocoder coordinates.
    known_places = {
        'kolkata': (22.5726, 88.3639, 'Asia/Kolkata', 'Kolkata, West Bengal, India'),
        'calcutta': (22.5726, 88.3639, 'Asia/Kolkata', 'Kolkata, West Bengal, India'),
    }
    normalized = display.lower()
    key = next((k for k in known_places if k in normalized), None)
    if key:
        lat, lon, timezone, display = known_places[key]
    else:
        lat, lon = float(selected['lat']), float(selected['lon'])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError('The selected place has invalid coordinates. Please select another result.')
        timezone = selected.get('timezone') or TZF.timezone_at(lat=lat, lng=lon)
    if not timezone:
        raise ValueError('Could not resolve timezone for the selected place. Try a nearby major city.')
    local_dt = datetime.fromisoformat(birth_local).replace(tzinfo=ZoneInfo(timezone))
    offset = local_dt.utcoffset().total_seconds() / 3600
    return {'lat':lat, 'lon':lon, 'timezone_offset':offset, 'resolved_place':selected.get('display_name','Selected place'), 'timezone':timezone}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print('%s - %s' % (self.address_string(), fmt % args), flush=True)
    def send_json(self, status, payload):
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type')
        self.end_headers()
        self.wfile.write(body)
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type')
        self.end_headers()
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path in ('/health','/api/health'):
            return self.send_json(200,{'status':'ok','app':'Janmapatri','version':'5.0'})
        if parsed.path=='/api/transits':
            try:
                q=parse_qs(parsed.query); given='lat' in q and 'lon' in q
                lat=float(q['lat'][0]) if given else 22.5726; lon=float(q['lon'][0]) if given else 88.3639
                zone=TZF.timezone_at(lat=lat,lng=lon) or 'Asia/Kolkata'
                tz=datetime.now(ZoneInfo(zone)).utcoffset().total_seconds()/3600
                res=transits(lat=lat,lon=lon,tz=tz); res['place']='your birthplace' if given else 'Kolkata (default)'; res['timezone']=zone
                return self.send_json(200,res)
            except Exception as e: return self.send_json(500,{'error':str(e)})
        if parsed.path=='/api/places':
            query=parse_qs(parsed.query).get('q',[''])[0].strip()
            if len(query)<2: return self.send_json(200,{'results':[]})
            results=[]
            # Primary: Photon geocoder (global city/town autocomplete; no API key).
            try:
                params=urlencode({'q':query,'limit':8})
                req=urllib.request.Request('https://photon.komoot.io/api/?'+params,headers={'User-Agent':USER_AGENT,'Accept-Language':'en'})
                with urllib.request.urlopen(req,timeout=12) as response: raw=json.loads(response.read().decode('utf-8'))
                for feature in raw.get('features',[]):
                    props=feature.get('properties',{}); coords=feature.get('geometry',{}).get('coordinates',[])
                    if len(coords)<2: continue
                    lon,lat=float(coords[0]),float(coords[1])
                    zone=TZF.timezone_at(lat=lat,lng=lon)
                    if not zone: continue
                    parts=[props.get(k) for k in ('name','city','state','country')]
                    display=', '.join(dict.fromkeys(str(x) for x in parts if x))
                    results.append({'display_name':display or query,'lat':lat,'lon':lon,'timezone':zone})
            except Exception as e:
                print('Photon geocoding failed: '+repr(e),flush=True)
            # Fallback: Nominatim.
            if not results:
                try:
                    params=urlencode({'q':query,'format':'jsonv2','addressdetails':1,'limit':8})
                    req=urllib.request.Request('https://nominatim.openstreetmap.org/search?'+params,headers={'User-Agent':USER_AGENT,'Accept-Language':'en'})
                    with urllib.request.urlopen(req,timeout=12) as response: raw=json.loads(response.read().decode('utf-8'))
                    for item in raw:
                        lat,lon=float(item['lat']),float(item['lon'])
                        zone=TZF.timezone_at(lat=lat,lng=lon)
                        if not zone: continue
                        results.append({'display_name':item.get('display_name',item.get('name',query)),'lat':lat,'lon':lon,'timezone':zone})
                except Exception as e:
                    print('Nominatim geocoding failed: '+repr(e),flush=True)
            return self.send_json(200,{'results':results,'provider':'Photon' if results else 'none'})
        if parsed.path in ('/','/index.html'):
            try: body=(BASE_DIR/'index.html').read_bytes()
            except Exception: return self.send_json(500,{'error':'Website file missing.'})
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body); return
        self.send_json(404,{'error':'Not found'})
    def do_POST(self):
        if urlparse(self.path).path!='/api/chart': return self.send_json(404,{'error':'Not found'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            data=json.loads(self.rfile.read(length) or b'{}')
            if not all(data.get(k) for k in ('name','birth_local','place')): raise ValueError('Name, date/time and birthplace are required.')
            selected_place=data.get('selected_place')
            # Override by user-entered place text, not geocoder output.
            place_text=(str(data.get('place',''))+' '+str((selected_place or {}).get('display_name',''))).lower()
            if 'kolkata' in place_text or 'calcutta' in place_text:
                selected_place={'display_name':'Kolkata, West Bengal, India','lat':22.5726,'lon':88.3639,'timezone':'Asia/Kolkata'}
            resolved=resolve_selected(selected_place,data['birth_local'])
            result=chart(data['birth_local'],resolved['lat'],resolved['lon'],resolved['timezone_offset'])
            result['input'].update({'name':data['name'],'place':data['place'],'resolved_place':resolved['resolved_place'],'timezone':resolved['timezone']})
            return self.send_json(200,result)
        except Exception as e:
            return self.send_json(400,{'error':str(e)})

if __name__=='__main__':
    print(f'Janmapatri V5 listening on 0.0.0.0:{PORT}',flush=True)
    ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
