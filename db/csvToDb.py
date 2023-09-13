import csv


def deg_to_dec(val: str):

    val = float(val[:-1]) / 100
    deg = int(val)
    frac = val % 1



    print(frac, frac * 60, frac * 3600)

    return deg + (frac * 60)

    # h_m, s = val.split(".")
    # h_m = h_m.strip("0")
    # h = int(h_m[0:2])
    # m = int(h_m[2:4])
    # print(f"----{val}---------------------------------")
    # print(val)
    # print("h_m", h_m)
    # print("m", m)
    # print(h, m, int(s))
    # print("--konec-----------------------------------")
    # return h + (m / 60.0) + (int(s) / 3600.0)

    # return val

    # return len(val or "")

# ZDAKOV: @49.504378,14.1808905

# 4930.250N / 100 -> cele cislo stupne, desetinne prevest do sedesatkove soustavy

with open("./poi.csv") as f:
    reader = csv.DictReader(f)

    for row in reader:
        if row['name'] != 'ZDAKOV':
            continue

        print(row['name'], row['lat'], row['lon'], deg_to_dec(row['lat']), deg_to_dec(row['lon']))