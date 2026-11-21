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
  lon=norm(xx[0]); info=sign_info(lon); nakidx=int(lon/(360/27)); pada=int((lon%(360/27))/(360/108))
  planets.append({'name':name,'longitude':lon,'sign':info['sign'],'sign_index':info['sign_index'],'degree':info['degree'],'degree_text':info['formatted'],'nakshatra':NAKSHATRAS[nakidx],'nakshatra_index':nakidx+1,'pada':pada,'retrograde':xx[3]<0,'speed':xx[3]})
 # Ketu opposite Rahu
 rahu=next(p for p in planets if p['name']=='Rahu'); ketulon=norm(rahu['longitude']+180); info=sign_info(ketulon); ni=int(ketulon/(360/27)); pada=int((ketulon%(360/27))/(360/108))
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
 return {'input':{'birth_local':birth_iso,'latitude':float(lat),'longitude':float(lon),'timezone_offset':float(tz_offset)},'ayanamsa':'Lahiri','house_system':'Whole sign','julian_day':jd,'lagna':{'longitude':asc,**lagna},'moon':moon,'planets':planets,'dasha':dasha}
