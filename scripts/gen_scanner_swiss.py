import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(BASE, 'data', 'tropical')
OUT = os.path.join(BASE, 'data', 'scanner_swiss.json')

N = 24  # samples per year, matching the existing 24-point sampling in computeMutationsFor/findAspects

MAIN_BODIES = [
    ('jup', 'Jupiter'),
    ('sat', 'Saturno'),
    ('ura', 'Urano'),
    ('nep', 'Netuno'),
    ('plu', 'Plutao'),
    ('nod', 'NodoN'),
]
QUI = ('qui', 'Quiron')

Y0, Y1 = -10000, 2100
QY0, QY1 = 676, 2100


def sample_year(vals, n_days, n):
    out = []
    for k in range(N):
        idx = int(k / N * n_days)
        if idx >= n_days:
            idx = n_days - 1
        out.append(vals[idx])
    return out


def main():
    bodies = {k: [] for k, _ in MAIN_BODIES}
    qui_vals = []

    for y in range(Y0, Y1 + 1):
        d = json.load(open(os.path.join(DATA, f'{y}.json')))
        n_days = len(d['Sol'])
        for k, jkey in MAIN_BODIES:
            samples = sample_year(d[jkey], n_days, N)
            bodies[k].extend(round(v, 2) for v in samples)
        if QY0 <= y <= QY1:
            samples = sample_year(d[QUI[1]], n_days, N)
            qui_vals.extend(round(v, 2) for v in samples)
        if (y - Y0) % 1000 == 0:
            print(f'{y} done', flush=True)

    out = {
        'y0': Y0, 'y1': Y1, 'n': N,
        'bodies': bodies,
        'qui': {'y0': QY0, 'y1': QY1, 'n': N, 'vals': qui_vals},
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, separators=(',', ':'))
    size = os.path.getsize(OUT)
    print(f'wrote {OUT} ({size/1e6:.2f} MB)')


if __name__ == '__main__':
    main()
