import json
import os
import sys
import time
import swisseph as swe

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
    ('NodoN', swe.TRUE_NODE),
    ('Lilith', swe.OSCU_APOG),
]

SYSTEMS = {
    'tropical': None,
    'lahiri': swe.SIDM_LAHIRI,
    'fagan-bradley': swe.SIDM_FAGAN_BRADLEY,
}

FLAG = swe.FLG_SWIEPH


def is_leap(y):
    return (y % 4 == 0) and (y % 100 != 0 or y % 400 == 0)


def days_in_year(y):
    return 366 if is_leap(y) else 365


def gen_year(year):
    jd0 = swe.julday(year, 1, 1, 0.0, swe.GREG_CAL)
    n = days_in_year(year)

    trop = {name: [] for name, _ in BODIES}
    ayan = {sys_name: [] for sys_name in SYSTEMS if sys_name != 'tropical'}

    for d in range(n):
        jd = jd0 + d
        for name, bid in BODIES:
            lon = swe.calc_ut(jd, bid, FLAG)[0][0] % 360
            trop[name].append(round(lon, 2))
        for sys_name, sidm in SYSTEMS.items():
            if sidm is None:
                continue
            swe.set_sid_mode(sidm)
            ayan[sys_name].append(swe.get_ayanamsa_ut(jd))

    out = {}
    for sys_name in SYSTEMS:
        if sys_name == 'tropical':
            out[sys_name] = trop
        else:
            a = ayan[sys_name]
            out[sys_name] = {
                name: [round((v - a[i]) % 360, 2) for i, v in enumerate(vals)]
                for name, vals in trop.items()
            }
    return out


def write_year(year, out):
    for sys_name, data in out.items():
        path = os.path.join(BASE, 'data', sys_name, f'{year}.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, separators=(',', ':'))


if __name__ == '__main__':
    start = int(sys.argv[1])
    end = int(sys.argv[2])  # inclusive
    t0 = time.time()
    count = 0
    for year in range(start, end + 1):
        out = gen_year(year)
        write_year(year, out)
        count += 1
        if count % 50 == 0:
            elapsed = time.time() - t0
            rate = count / elapsed
            remaining = (end - start + 1 - count) / rate if rate > 0 else 0
            print(f'{year} done ({count}/{end-start+1}) '
                  f'{rate:.2f} yr/s, ETA {remaining/60:.1f} min', flush=True)
    print(f'TOTAL: {count} years in {(time.time()-t0)/60:.2f} min')
