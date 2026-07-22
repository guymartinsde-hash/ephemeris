#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════
EPHEMERIS SIDERAL — Gerador de Dados de Eclipses + Saros
═══════════════════════════════════════════════════════════════
Range: -5000 a +2100 (7100 anos)
Output: data/eclipses.json

Usa Swiss Ephemeris (pyswisseph) para calcular:
- Todos os eclipses solares e lunares no período
- Tipo: total, anular, híbrido, parcial
- Longitude eclíptica (tropical + correção sideral)
- Série Saros (calculada por encadeamento de ~6585.32 dias)
- Coordenadas geográficas do máximo (solar only)

Rodar no Cowork:
  pip install pyswisseph --break-system-packages
  python3 gen_eclipses.py
═══════════════════════════════════════════════════════════════
"""

import json
import os
import sys
import time

try:
    import swisseph as swe
except ImportError:
    print("ERRO: pyswisseph não instalado.")
    print("Instale com: pip install pyswisseph --break-system-packages")
    sys.exit(1)

# ═══ CONFIGURAÇÃO ═══
START_YEAR = -5000
END_YEAR   = 2100
AYAN_FIXED = 25.06  # Fagan-Bradley fixo (fallback)
OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "eclipses.json")

# Saros period em dias
SAROS_PERIOD = 6585.3211
SAROS_TOLERANCE = 1.5  # dias de tolerância pra encadear

# Eclipse type flags do Swiss Ephemeris — usar as constantes reais do módulo,
# não valores chutados: os bits verdadeiros são CENTRAL=1, NONCENTRAL=2,
# TOTAL=4, ANNULAR=8, PARTIAL=16, ANNULAR_TOTAL=32, PENUMBRAL=64 (só lunar).
# Uma versão anterior deste script usava 1/2/4/8 pra TOTAL/ANNULAR/PARTIAL/
# HYBRID, que na verdade colidem com CENTRAL/NONCENTRAL/TOTAL/ANNULAR —
# isso classificava todo eclipse errado (e por isso nenhum lunar era "total",
# já que CENTRAL/NONCENTRAL nunca se aplicam a eclipses lunares).
ECL_TOTAL     = swe.ECL_TOTAL
ECL_ANNULAR   = swe.ECL_ANNULAR
ECL_PARTIAL   = swe.ECL_PARTIAL
ECL_HYBRID    = swe.ECL_ANNULAR_TOTAL
ECL_PENUMBRAL = swe.ECL_PENUMBRAL


def jd_to_date(jd):
    """Julian Day → (year, month, day, hour)"""
    r = swe.revjul(jd)
    return int(r[0]), int(r[1]), int(r[2]), round(r[3], 2)


def ecl_type_name(flag):
    """Flag do Swiss Ephemeris → nome do tipo"""
    if flag & ECL_TOTAL:
        return "total"
    if flag & ECL_HYBRID:
        return "hybrid"
    if flag & ECL_ANNULAR:
        return "annular"
    if flag & ECL_PARTIAL:
        return "partial"
    if flag & ECL_PENUMBRAL:
        return "penumbral"
    return "unknown"


def tropical_to_sidereal(lon_tropical, year):
    """Converte longitude tropical → sideral Fagan-Bradley"""
    # Tenta usar ayanamsa dinâmico do Swiss Ephemeris
    try:
        swe.set_sid_mode(swe.SIDM_FAGAN_BRADLEY)
        jd = swe.julday(year, 7, 1, 0.0)
        ayan = swe.get_ayanamsa_ut(jd)
    except:
        ayan = AYAN_FIXED
    sid = (lon_tropical - ayan) % 360.0
    return round(sid, 2)


def sign_index(lon_sid):
    """Longitude sideral → índice do signo (0-11)"""
    return int(lon_sid / 30.0) % 12


def find_solar_eclipses(start_year, end_year):
    """Encontra todos os eclipses solares no período"""
    eclipses = []
    jd = swe.julday(start_year, 1, 1, 0.0)
    jd_end = swe.julday(end_year, 12, 31, 0.0)
    count = 0

    while jd < jd_end:
        try:
            retflag, tret = swe.sol_eclipse_when_glob(jd, swe.FLG_SWIEPH, 0)
            jd_max = tret[0]

            if jd_max >= jd_end:
                break

            etype = ecl_type_name(retflag)
            year, month, day, hour = jd_to_date(jd_max)

            # Longitude eclíptica do Sol no momento do eclipse
            sun_pos = swe.calc_ut(jd_max, swe.SUN, swe.FLG_SWIEPH)
            lon_trop = round(sun_pos[0][0], 2)
            lon_sid = tropical_to_sidereal(lon_trop, year)

            # Coordenadas geográficas do máximo (onde a sombra é central)
            geo_lon, geo_lat = 0.0, 0.0
            try:
                retflag2, geopos, attr = swe.sol_eclipse_where(jd_max, swe.FLG_SWIEPH)
                geo_lon = round(geopos[0], 2)
                geo_lat = round(geopos[1], 2)
            except:
                pass  # Alguns eclipses parciais não têm posição central

            eclipses.append({
                "jd":      round(jd_max, 4),
                "year":    year,
                "month":   month,
                "day":     day,
                "kind":    "solar",
                "type":    etype,
                "lon_trop": lon_trop,
                "lon_sid":  lon_sid,
                "sign":    sign_index(lon_sid),
                "geo_lon": geo_lon,
                "geo_lat": geo_lat,
                "saros":   0   # preenchido depois
            })

            count += 1
            if count % 500 == 0:
                print(f"  Solar: {count} eclipses, ano {year}...")

            jd = jd_max + 20  # mínimo 20 dias entre eclipses

        except Exception as e:
            jd += 30
            continue

    print(f"  Total eclipses solares: {count}")
    return eclipses


def find_lunar_eclipses(start_year, end_year):
    """Encontra todos os eclipses lunares no período"""
    eclipses = []
    jd = swe.julday(start_year, 1, 1, 0.0)
    jd_end = swe.julday(end_year, 12, 31, 0.0)
    count = 0

    while jd < jd_end:
        try:
            retflag, tret = swe.lun_eclipse_when(jd, swe.FLG_SWIEPH, 0)
            jd_max = tret[0]

            if jd_max >= jd_end:
                break

            etype = ecl_type_name(retflag)
            year, month, day, hour = jd_to_date(jd_max)

            # Longitude eclíptica da Lua no momento do eclipse
            moon_pos = swe.calc_ut(jd_max, swe.MOON, swe.FLG_SWIEPH)
            lon_trop = round(moon_pos[0][0], 2)
            lon_sid = tropical_to_sidereal(lon_trop, year)

            eclipses.append({
                "jd":      round(jd_max, 4),
                "year":    year,
                "month":   month,
                "day":     day,
                "kind":    "lunar",
                "type":    etype,
                "lon_trop": lon_trop,
                "lon_sid":  lon_sid,
                "sign":    sign_index(lon_sid),
                "saros":   0
            })

            count += 1
            if count % 500 == 0:
                print(f"  Lunar: {count} eclipses, ano {year}...")

            jd = jd_max + 20

        except Exception as e:
            jd += 30
            continue

    print(f"  Total eclipses lunares: {count}")
    return eclipses


def assign_saros_series(eclipses, kind):
    """
    Atribui número de série Saros por encadeamento.
    Eclipses separados por ~6585.32 dias pertencem à mesma série.
    """
    ecls = sorted([e for e in eclipses if e["kind"] == kind], key=lambda e: e["jd"])
    series_counter = 1

    for i, ecl in enumerate(ecls):
        if ecl["saros"] > 0:
            continue  # já atribuído

        # Inicia nova série
        ecl["saros"] = series_counter
        current_jd = ecl["jd"]

        # Encadeia pra frente
        for j in range(i + 1, len(ecls)):
            diff = ecls[j]["jd"] - current_jd
            if diff < SAROS_PERIOD - SAROS_TOLERANCE:
                continue
            if diff > SAROS_PERIOD + SAROS_TOLERANCE:
                break
            if ecls[j]["saros"] == 0:
                ecls[j]["saros"] = series_counter
                current_jd = ecls[j]["jd"]

        series_counter += 1

    assigned = sum(1 for e in ecls if e["saros"] > 0)
    orphans = sum(1 for e in ecls if e["saros"] == 0)
    print(f"  {kind}: {series_counter - 1} séries Saros, {assigned} encadeados, {orphans} órfãos")

    # Órfãos recebem série negativa (identificador provisório)
    neg = -1
    for e in ecls:
        if e["saros"] == 0:
            e["saros"] = neg
            neg -= 1

    return ecls


def build_saros_catalog(eclipses):
    """
    Constrói catálogo de séries Saros com metadados:
    - Primeiro e último eclipse da série
    - Número total de eclipses
    - Tipo predominante
    """
    catalog = {}
    for ecl in eclipses:
        key = f"{ecl['kind']}_{ecl['saros']}"
        if key not in catalog:
            catalog[key] = {
                "saros": ecl["saros"],
                "kind": ecl["kind"],
                "first_year": ecl["year"],
                "last_year": ecl["year"],
                "count": 0,
                "types": {}
            }
        cat = catalog[key]
        cat["count"] += 1
        cat["last_year"] = max(cat["last_year"], ecl["year"])
        cat["first_year"] = min(cat["first_year"], ecl["year"])
        t = ecl["type"]
        cat["types"][t] = cat["types"].get(t, 0) + 1

    # Tipo predominante
    for key, cat in catalog.items():
        cat["dominant_type"] = max(cat["types"], key=cat["types"].get)
        cat["duration_years"] = cat["last_year"] - cat["first_year"]

    return list(catalog.values())


def main():
    t0 = time.time()

    print("═" * 60)
    print("EPHEMERIS SIDERAL — Gerador de Eclipses + Saros")
    print(f"Range: {START_YEAR} a {END_YEAR}")
    print("═" * 60)
    print()

    # Inicializar Swiss Ephemeris
    # Tenta usar arquivos de efemérides se disponíveis
    ephe_paths = ["./ephe", ".", "/usr/share/swisseph/ephe"]
    for p in ephe_paths:
        if os.path.isdir(p):
            swe.set_ephe_path(p)
            break

    # ═══ ECLIPSES SOLARES ═══
    print("☀ Buscando eclipses solares...")
    solar = find_solar_eclipses(START_YEAR, END_YEAR)

    # ═══ ECLIPSES LUNARES ═══
    print("\n☾ Buscando eclipses lunares...")
    lunar = find_lunar_eclipses(START_YEAR, END_YEAR)

    # ═══ SÉRIES SAROS ═══
    print("\n⟳ Calculando séries Saros...")
    solar = assign_saros_series(solar + lunar, "solar")
    lunar = assign_saros_series(solar + lunar, "lunar")

    all_eclipses = sorted(solar + lunar, key=lambda e: e["jd"])

    # Remove duplicatas (assign_saros pode ter duplicado)
    seen = set()
    unique = []
    for e in all_eclipses:
        key = (e["jd"], e["kind"])
        if key not in seen:
            seen.add(key)
            unique.append(e)
    all_eclipses = unique

    # ═══ FILTRAR MAIORES (total + anular + híbrido) ═══
    major = [e for e in all_eclipses if e["type"] in ("total", "annular", "hybrid")]

    # ═══ CATÁLOGO SAROS ═══
    print("\n📖 Construindo catálogo Saros...")
    saros_catalog = build_saros_catalog(all_eclipses)
    saros_catalog.sort(key=lambda s: s["first_year"])

    # ═══ ÍNDICE POR ANO (pra lookup rápido no front) ═══
    by_year = {}
    for e in all_eclipses:
        y = e["year"]
        if y not in by_year:
            by_year[y] = []
        # Versão compacta pro índice
        by_year[y].append({
            "m": e["month"],
            "d": e["day"],
            "k": e["kind"][0],      # "s" ou "l"
            "t": e["type"][0],      # "t","a","h","p"
            "s": e["sign"],         # índice sideral 0-11
            "sr": e["saros"]        # série Saros
        })

    # ═══ OUTPUT ═══
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    output = {
        "range": [START_YEAR, END_YEAR],
        "ayanamsa": "fagan-bradley",
        "total_count": len(all_eclipses),
        "major_count": len(major),
        "saros_series_count": len(saros_catalog),
        "by_year": {str(k): v for k, v in by_year.items()},
        "saros_catalog": saros_catalog,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    # Também salvar versão "major only" mais leve
    major_by_year = {}
    for e in major:
        y = e["year"]
        if y not in major_by_year:
            major_by_year[y] = []
        major_by_year[y].append({
            "m": e["month"],
            "d": e["day"],
            "k": e["kind"][0],
            "t": e["type"][0],
            "s": e["sign"],
            "sr": e["saros"]
        })

    major_output = {
        "range": [START_YEAR, END_YEAR],
        "ayanamsa": "fagan-bradley",
        "count": len(major),
        "by_year": {str(k): v for k, v in major_by_year.items()},
    }

    major_file = os.path.join(OUTPUT_DIR, "eclipses_major.json")
    with open(major_file, "w") as f:
        json.dump(major_output, f, separators=(",", ":"))

    elapsed = time.time() - t0

    # ═══ SUMÁRIO ═══
    print("\n" + "═" * 60)
    print(f"✅ CONCLUÍDO em {elapsed:.1f}s")
    print(f"   Eclipses totais:  {len(all_eclipses)}")
    print(f"   Eclipses maiores: {len(major)} (total+anular+híbrido)")
    print(f"   Séries Saros:     {len(saros_catalog)}")
    print(f"   Arquivo completo: {OUTPUT_FILE} ({os.path.getsize(OUTPUT_FILE)/1024:.0f} KB)")
    print(f"   Arquivo major:    {major_file} ({os.path.getsize(major_file)/1024:.0f} KB)")
    print("═" * 60)

    # Stats rápidos
    solar_total = sum(1 for e in all_eclipses if e["kind"] == "solar" and e["type"] == "total")
    solar_annular = sum(1 for e in all_eclipses if e["kind"] == "solar" and e["type"] == "annular")
    lunar_total = sum(1 for e in all_eclipses if e["kind"] == "lunar" and e["type"] == "total")
    print(f"\n   Solares totais:   {solar_total}")
    print(f"   Solares anulares: {solar_annular}")
    print(f"   Lunares totais:   {lunar_total}")

    # Maior série Saros
    if saros_catalog:
        longest = max(saros_catalog, key=lambda s: s["count"])
        print(f"\n   Maior série Saros: #{longest['saros']} ({longest['kind']})")
        print(f"     {longest['count']} eclipses, {longest['first_year']} → {longest['last_year']}")
        print(f"     Duração: {longest['duration_years']} anos")


if __name__ == "__main__":
    main()
