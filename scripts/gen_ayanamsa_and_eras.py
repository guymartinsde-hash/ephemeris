import json
import os
import swisseph as swe

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
swe.set_ephe_path(os.path.join(BASE, 'ephe'))

Y0, Y1 = -10000, 2100

# current hardcoded FB-based era boundaries (from index.html ERAS const)
# names kept ASCII-only here to sidestep source-encoding issues; order matches
# index.html's ERAS array exactly, which is all that matters for consumption.
ERAS_FB = [
    ('Leao', -10519, -8371),
    ('Cancer', -8371, -6223),
    ('Gemeos', -6223, -4075),
    ('Touro', -4075, -1927),
    ('Aries', -1927, 221),
    ('Peixes', 221, 2369),
    ('Aquario', 2369, 4517),
]


def ayanamsa(sidm, year):
    jd = swe.julday(year, 1, 1, 0.0, swe.GREG_CAL)
    swe.set_sid_mode(sidm)
    return swe.get_ayanamsa_ut(jd)


def build_ayan_series(sidm, y0, y1):
    return [round(ayanamsa(sidm, y), 4) for y in range(y0, y1 + 1)]


def main():
    print('Computing ayanamsa series (Lahiri + Fagan-Bradley), -10000..2100 ...')
    ayan_lahiri = build_ayan_series(swe.SIDM_LAHIRI, Y0, Y1)
    ayan_fb = build_ayan_series(swe.SIDM_FAGAN_BRADLEY, Y0, Y1)

    # Lahiri and Fagan-Bradley share the exact same precession RATE in Swiss Ephemeris —
    # they differ by a constant offset (~0.883°, verified identical at every sampled year
    # from -10000 to 4000). So era boundaries just shift by a constant number of years;
    # no need for per-boundary root-finding (which is also unsafe near the ~360->0 wrap).
    y1, y2 = -10000, -1000  # safe interval, doesn't cross the ~year-300 wrap point
    rate = (ayanamsa(swe.SIDM_FAGAN_BRADLEY, y2) - ayanamsa(swe.SIDM_FAGAN_BRADLEY, y1)) / (y2 - y1)
    offset = ayanamsa(swe.SIDM_FAGAN_BRADLEY, 0) - ayanamsa(swe.SIDM_LAHIRI, 0)
    shift = offset / rate
    print(f'  precession rate={rate:.6f} deg/yr, FB-Lahiri offset={offset:.4f} deg, '
          f'era shift={shift:.2f} years')

    eras_lahiri = []
    for name, start, end in ERAS_FB:
        ls, le = round(start + shift), round(end + shift)
        eras_lahiri.append((name, ls, le))
        print(f'  {name}: FB[{start},{end}] -> Lahiri[{ls},{le}]')

    out = {
        'y0': Y0, 'y1': Y1,
        'lahiri': ayan_lahiri,
        'fagan-bradley': ayan_fb,
        'eras_lahiri': eras_lahiri,
    }
    out_path = os.path.join(BASE, 'data', 'ayanamsa.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, separators=(',', ':'), ensure_ascii=False)
    print(f'wrote {out_path} ({os.path.getsize(out_path)/1e6:.2f} MB)')


if __name__ == '__main__':
    main()
