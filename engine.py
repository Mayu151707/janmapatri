import libephemeris as swe
from datetime import datetime, timedelta
import math

SIGNS=['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces']
NAKSHATRAS=['Ashwini','Bharani','Krittika','Rohini','Mrigashira','Ardra','Punarvasu','Pushya','Ashlesha','Magha','Purva Phalguni','Uttara Phalguni','Hasta','Chitra','Swati','Vishakha','Anuradha','Jyeshtha','Mula','Purva Ashadha','Uttara Ashadha','Shravana','Dhanishta','Shatabhisha','Purva Bhadrapada','Uttara Bhadrapada','Revati']
PLANETS=[('Sun',swe.SUN),('Moon',swe.MOON),('Mars',swe.MARS),('Mercury',swe.MERCURY),('Jupiter',swe.JUPITER),('Venus',swe.VENUS),('Saturn',swe.SATURN),('Rahu',swe.MEAN_NODE)]
DASHA_ORDER=['Ketu','Venus','Sun','Moon','Mars','Rahu','Jupiter','Saturn','Mercury']
DASHA_YEARS={'Ketu':7,'Venus':20,'Sun':6,'Moon':10,'Mars':7,'Rahu':18,'Jupiter':16,'Saturn':19,'Mercury':17}

def norm(x): return x%360
def sign_info(lon):
 lon=norm(lon); si=int(lon//30); deg=lon%30
 return {'sign':SIGNS[si], 'sign_index':si+1,'degree':deg,'formatted':f'{int(deg)}° {int((deg%1)*60):02d}′'}
def chart(birth_iso, lat, lon, tz_offset):
 # input local time; timezone offset hours from UTC
 dt=datetime.fromisoformat(birth_iso)
 utc=dt-timedelta(hours=float(tz_offset))
 hour=utc.hour+utc.minute/60+utc.second/3600
 jd=swe.julday(utc.year,utc.month,utc.day,hour)
 swe.set_sid_mode(swe.SIDM_LAHIRI)
 flags=swe.FLG_SWIEPH|swe.FLG_SPEED|swe.FLG_SIDEREAL
 planets=[]
 for name,body in PLANETS:
  xx,ret=swe.calc_ut(jd,body,flags)
  plon=norm(xx[0]); info=sign_info(plon); nakidx=int(plon/(360/27)); pada=int((plon%(360/27))/(360/108))+1
  planets.append({'name':name,'longitude':plon,'sign':info['sign'],'sign_index':info['sign_index'],'degree':info['degree'],'degree_text':info['formatted'],'nakshatra':NAKSHATRAS[nakidx],'nakshatra_index':nakidx+1,'pada':pada,'retrograde':xx[3]<0,'speed':xx[3]})
 # Ketu opposite Rahu
 rahu=next(p for p in planets if p['name']=='Rahu'); ketulon=norm(rahu['longitude']+180); info=sign_info(ketulon); ni=int(ketulon/(360/27)); pada=int((ketulon%(360/27))/(360/108))+1
 planets.append({'name':'Ketu','longitude':ketulon,'sign':info['sign'],'sign_index':info['sign_index'],'degree':info['degree'],'degree_text':info['formatted'],'nakshatra':NAKSHATRAS[ni],'nakshatra_index':ni+1,'pada':pada,'retrograde':True,'speed':-rahu['speed']})
 # Compute Ascendant using tropical house calculation, then apply Lahiri ayanamsa manually.
 # This avoids a compatibility issue in some LibEphemeris builds where houses_ex with
 # FLG_SIDEREAL can transform the geographic longitude and raise a range error.
 lat_f, lon_f = float(lat), float(lon)
 if not (-90.0 <= lat_f <= 90.0):
  raise ValueError(f'Birth-place latitude is invalid: {lat_f}. Expected -90 to 90 degrees.')
 if not (-180.0 <= lon_f <= 180.0):
  raise ValueError(f'Birth-place longitude is invalid: {lon_f}. Expected -180 to 180 degrees.')
 cusps, ascmc=swe.houses(jd,lat_f,lon_f,b'W')
 tropical_asc=norm(ascmc[0])
 ay=swe.get_ayanamsa_ut(jd)
 asc=norm(tropical_asc-ay); lagna=sign_info(asc)
 for p in planets:
  p['house']=(p['sign_index']-lagna['sign_index'])%12+1
 moon=next(p for p in planets if p['name']=='Moon')
 # Vimshottari birth balance based Moon's nakshatra fraction
 nsize=360/27; nidx=int(moon['longitude']/nsize); fraction=(moon['longitude']%nsize)/nsize
 startlord=DASHA_ORDER[nidx%9]; balance=DASHA_YEARS[startlord]*(1-fraction)
 startidx=DASHA_ORDER.index(startlord); sequence=[DASHA_ORDER[(startidx+i)%9] for i in range(9)]
 # birth dasha timeline with approximate calendar years; use year length 365.2425
 start_date=dt
 dasha=[]; cursor=start_date-timedelta(days=DASHA_YEARS[startlord]*fraction*365.2425)
 for lord in sequence:
  yrs=DASHA_YEARS[lord]; end=cursor+timedelta(days=yrs*365.2425)
  dasha.append({'lord':lord,'start':cursor.date().isoformat(),'end':end.date().isoformat(),'years':yrs,'birth_balance_years':round(balance,2) if lord==startlord else None})
  cursor=end
 return {'input':{'birth_local':birth_iso,'latitude':float(lat),'longitude':float(lon),'timezone_offset':float(tz_offset)},'ayanamsa':'Lahiri','house_system':'Whole sign','julian_day':jd,'lagna':{'longitude':asc,**lagna},'moon':moon,'planets':planets,'dasha':dasha,'panchang':panchang_for(dt,float(tz_offset),lat_f,lon_f,planets[0]['longitude'],moon['longitude'])}

VARA=['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday']
VARA_LORD=['Sun','Moon','Mars','Mercury','Jupiter','Venus','Saturn']
TITHIS=['Pratipada','Dwitiya','Tritiya','Chaturthi','Panchami','Shashthi','Saptami','Ashtami','Navami','Dashami','Ekadashi','Dwadashi','Trayodashi','Chaturdashi']
YOGAS=['Vishkambha','Priti','Ayushman','Saubhagya','Shobhana','Atiganda','Sukarma','Dhriti','Shula','Ganda','Vriddhi','Dhruva','Vyaghata','Harshana','Vajra','Siddhi','Vyatipata','Variyana','Parigha','Shiva','Siddha','Sadhya','Shubha','Shukla','Brahma','Indra','Vaidhriti']
KARANA_MOV=['Bava','Balava','Kaulava','Taitila','Gara','Vanija','Vishti']

def _jd_to_dt(jd):
 return datetime(2000,1,1,12)+timedelta(days=jd-2451545.0)

def _sun_times(local_date,lat,lon,tz):
 # Local sunrise and sunset for a calendar date at a place; (None,None) if not found.
 try:
  jd0=swe.julday(local_date.year,local_date.month,local_date.day,0)-tz/24.0
  geo=(float(lon),float(lat),0.0)
  s1,r=swe.rise_trans(jd0,swe.SUN,swe.CALC_RISE,geo)
  if s1!=0: return None,None
  s2,t=swe.rise_trans(r[0],swe.SUN,swe.CALC_SET,geo)
  if s2!=0: return None,None
  return _jd_to_dt(r[0])+timedelta(hours=tz),_jd_to_dt(t[0])+timedelta(hours=tz)
 except Exception:
  return None,None

def _tyk(sun,moon):
 el=(moon-sun)%360; ti=int(el//12); k=int(el//6)
 name='Purnima' if ti==14 else 'Amavasya' if ti==29 else TITHIS[ti%15]
 kn='Kimstughna' if k==0 else 'Shakuni' if k==57 else 'Chatushpada' if k==58 else 'Naga' if k==59 else KARANA_MOV[(k-1)%7]
 return {'tithi':name,'tithi_number':ti+1,'paksha':'Shukla' if ti<15 else 'Krishna','yoga':YOGAS[int(((sun+moon)%360)//(360/27))],'karana':kn}

def _periods(sr,ss,wd):
 d=(ss-sr)/8
 seg=lambda n:'%s-%s'%((sr+d*(n-1)).strftime('%H:%M'),(sr+d*n).strftime('%H:%M'))
 a=sr+(ss-sr)*7/15; b=sr+(ss-sr)*8/15
 return {'rahu_kaal':seg([8,2,7,5,6,4,3][wd]),'yamaganda':seg([4,3,2,1,7,6,5][wd]),'gulika':seg([7,6,5,4,3,2,1][wd]),'abhijit':'%s-%s'%(a.strftime('%H:%M'),b.strftime('%H:%M'))}

def panchang_for(dt_local,tz,lat,lon,sun,moon):
 sr,ss=_sun_times(dt_local.date(),lat,lon,tz)
 day=dt_local.date()
 vday=day if (sr is None or dt_local>=sr) else day-timedelta(days=1)   # Vedic day starts at sunrise
 wd=(vday.weekday()+1)%7
 out=_tyk(sun,moon)
 out.update({'vara':VARA[wd],'vara_lord':VARA_LORD[wd],'sunrise':sr.strftime('%H:%M') if sr else None,'sunset':ss.strftime('%H:%M') if ss else None})
 if sr and ss: out.update(_periods(sr,ss,(day.weekday()+1)%7))
 return out

def transits(when=None,lat=22.5726,lon=88.3639,tz=5.5):
 # Current sidereal (Lahiri) sky plus Panchang for a place. Used by the Daily page.
 from datetime import timezone
 dt=when or datetime.now(timezone.utc)
 jd=swe.julday(dt.year,dt.month,dt.day,dt.hour+dt.minute/60+dt.second/3600)
 swe.set_sid_mode(swe.SIDM_LAHIRI)
 flags=swe.FLG_SWIEPH|swe.FLG_SPEED|swe.FLG_SIDEREAL
 out=[]
 def row(name,lon_,retro):
  info=sign_info(lon_); ni=int(norm(lon_)/(360/27))
  return {'name':name,'longitude':norm(lon_),'sign':info['sign'],'sign_index':info['sign_index'],'degree_text':info['formatted'],'nakshatra':NAKSHATRAS[ni],'retrograde':retro}
 for name,body in PLANETS:
  xx,ret=swe.calc_ut(jd,body,flags)
  out.append(row(name,xx[0],xx[3]<0))
 out.append(row('Ketu',out[-1]['longitude']+180,True))
 local=(dt+timedelta(hours=tz)).replace(tzinfo=None)
 return {'as_of':dt.isoformat(),'ayanamsa':'Lahiri','planets':out,'panchang':panchang_for(local,tz,lat,lon,out[0]['longitude'],out[1]['longitude'])}
