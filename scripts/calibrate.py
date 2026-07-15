import json
import swisseph as swe
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
swe.set_ephe_path(os.path.join(BASE, 'ephe'))

BODIES = [
    ('Sol', swe.SUN),
    ('Lua', swe.MOON),
    ('Mercurio', swe.MERCURY),
    ('Venus', swe.VENUS),
    ('Marte', swe.MARS),
    ('Jupiter', swe.JUPITER),
    ('Saturno', swe.SATURN),
    ('Urano', swe.URANUS),
    ('Netuno', swe.NEPTUNE),
    ('Plutao', swe.PLUTO),
]

NODE_APOG_CANDIDATES = [
    ('NodoN_true', swe.TRUE_NODE),
    ('NodoN_mean', swe.MEAN_NODE),
    ('Lilith_oscu', swe.OSCU_APOG),
    ('Lilith_mean', swe.MEAN_APOG),
]

existing = json.load(open(os.path.join(BASE, 'data', 'tropical', '-3000.json')))

for hour in (0.0, 12.0):
    jd = swe.julday(-3000, 1, 1, hour, swe.GREG_CAL)
    print(f'--- hour={hour} JD={jd} ---')
    for name, bid in BODIES:
        lon = swe.calc_ut(jd, bid, swe.FLG_SWIEPH)[0][0] % 360
        expected = existing[name][0]
        print(f'{name:10s} computed={lon:8.2f} expected={expected:8.2f} diff={abs(lon-expected):.3f}')
    for name, bid in NODE_APOG_CANDIDATES:
        lon = swe.calc_ut(jd, bid, swe.FLG_SWIEPH)[0][0] % 360
        base = 'NodoN' if 'NodoN' in name else 'Lilith'
        expected = existing[base][0]
        print(f'{name:14s} computed={lon:8.2f} expected={expected:8.2f} diff={abs(lon-expected):.3f}')

# check leap year day-count consistency for a known leap/non-leap and ayanamsa
print()
print('ephe path used:', swe.get_library_path() if hasattr(swe, "get_library_path") else "n/a")
