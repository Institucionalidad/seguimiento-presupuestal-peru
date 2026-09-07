"""
Genera los cubos agregados (JSON) que alimentan el tablero de seguimiento de
ejecucion presupuestal a partir de ppto_mef.parquet.

Uso:
    python build_dashboard_data.py

Lee "../ppto_mef.parquet" (la copia vigente) y escribe un JSON por vista en
./data/. Los JSON son pequenos (agregados, no el detalle fila a fila) para
poder incrustarlos directamente en el HTML del tablero.
"""
import json
import re
from pathlib import Path

import pyarrow.parquet as pq
import pyarrow.compute as pc
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
PARQUET_PATH = BASE_DIR.parent / "ppto_mef.parquet"
OUT_DIR = BASE_DIR / "data"
OUT_DIR.mkdir(exist_ok=True)

MESES_ORDEN = [
    "1. Enero", "2. Febrero", "3. Marzo", "4. Abril", "5. Mayo", "6. Junio",
    "7. Julio", "8. Agosto", "9. Setiembre", "10. Octubre", "11. Noviembre", "12. Diciembre",
]


def mes_sort_key(m):
    try:
        return int(str(m).split(".")[0])
    except ValueError:
        return -1


def dump(name, obj):
    path = OUT_DIR / f"{name}.json"
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"  -> {name}.json ({path.stat().st_size / 1024:.1f} KB)")


def find_corte_date():
    """Busca la fecha de corte en el nombre del archivo original (ddmmyyyy)."""
    candidates = list((BASE_DIR.parent / "2. Bases de datos originales").glob("consulta_amigable_*.parquet"))
    if candidates:
        m = re.search(r"_(\d{2})(\d{2})(\d{4})\.parquet$", candidates[0].name)
        if m:
            dd, mm, yyyy = m.groups()
            return f"{yyyy}-{mm}-{dd}"
    return None


print("Leyendo columnas necesarias de ppto_mef.parquet ...")
COLS = [
    "AÑO", "MES", "NIVEL_GOB", "DEPARTAMENTO_META", "SECTOR", "PLIEGO", "FUNCION",
    "CATEGORIA_GTO", "GENERICA", "TIPO_ACT_PROY", "PRODUCTO_PROYECTO",
    "PIA", "PIM", "CERTIFICADO", "COMPROMETIDO", "DEVENGADO", "GIRADO",
]
tabla = pq.read_table(PARQUET_PATH, columns=COLS)
print(f"  {tabla.num_rows:,} filas leidas")

df = tabla.to_pandas()
del tabla

anio = int(df["AÑO"].iloc[0])
meses_con_dato = sorted(
    [m for m in df.loc[df["MES"] != "0", "MES"].unique().tolist()],
    key=mes_sort_key,
)
ultimo_mes_num = mes_sort_key(meses_con_dato[-1]) if meses_con_dato else 0

corte = find_corte_date()
if corte:
    from datetime import date
    y, m, d = (int(x) for x in corte.split("-"))
    dia_del_anio = date(y, m, d).timetuple().tm_yday
    dias_anio = 366 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 365
else:
    dia_del_anio, dias_anio = None, 365

df_anual = df[df["MES"] == "0"]  # PIA/PIM viven aqui
df_mensual = df[df["MES"] != "0"]  # flujos de ejecucion viven aqui

print("Construyendo cubos ...")

# ---------------------------------------------------------------- kpis ----
kpis = {
    "anio": anio,
    "fecha_corte": corte,
    "ultimo_mes_con_dato": meses_con_dato[-1] if meses_con_dato else None,
    "dia_del_anio": dia_del_anio,
    "dias_anio": dias_anio,
    "pia": float(df_anual["PIA"].sum()),
    "pim": float(df_anual["PIM"].sum()),
    "certificado": float(df_mensual["CERTIFICADO"].sum()),
    "comprometido": float(df_mensual["COMPROMETIDO"].sum()),
    "devengado": float(df_mensual["DEVENGADO"].sum()),
    "girado": float(df_mensual["GIRADO"].sum()),
}
dump("kpis", kpis)

# --------------------------------------------------------- serie_mensual ----
g = (
    df_mensual.groupby(["MES", "NIVEL_GOB"], as_index=False)[
        ["CERTIFICADO", "COMPROMETIDO", "DEVENGADO", "GIRADO"]
    ].sum()
)
g = g.sort_values(by="MES", key=lambda s: s.map(mes_sort_key))
dump("serie_mensual", g.to_dict(orient="records"))

# ----------------------------------------------------------- nivel_gob ----
piapim_ng = df_anual.groupby("NIVEL_GOB", as_index=False)[["PIA", "PIM"]].sum()
ejec_ng = df_mensual.groupby("NIVEL_GOB", as_index=False)[["CERTIFICADO", "COMPROMETIDO", "DEVENGADO", "GIRADO"]].sum()
nivel_gob = piapim_ng.merge(ejec_ng, on="NIVEL_GOB", how="outer").fillna(0.0)
dump("nivel_gob", nivel_gob.to_dict(orient="records"))

# --------------------------------------------------------- departamento ----
pim_d = df_anual.groupby(["DEPARTAMENTO_META", "NIVEL_GOB"], as_index=False)["PIM"].sum()
ejec_d = df_mensual.groupby(["DEPARTAMENTO_META", "NIVEL_GOB", "MES"], as_index=False)[
    ["DEVENGADO", "GIRADO"]
].sum()
dump("departamento_pim", pim_d.to_dict(orient="records"))
dump("departamento_ejec", ejec_d.to_dict(orient="records"))

# --------------------------------------------------------------- sector ----
# SECTOR solo es una clasificacion real (ministerios) para Gobierno Nacional;
# en Regional son 2 bolsas genericas ("GOBIERNOS REGIONALES"/"MANCOMUNIDADES")
# y en Local el script de extraccion la reemplaza por el departamento.
mask_nacional = df["NIVEL_GOB"] == "1. GOBIERNO NACIONAL"
pim_s = df_anual[df_anual["NIVEL_GOB"] == "1. GOBIERNO NACIONAL"].groupby("SECTOR", as_index=False)["PIM"].sum()
ejec_s = df_mensual[df_mensual["NIVEL_GOB"] == "1. GOBIERNO NACIONAL"].groupby(["SECTOR", "MES"], as_index=False)[
    ["DEVENGADO", "GIRADO"]
].sum()
dump("sector_pim", pim_s.to_dict(orient="records"))
dump("sector_ejec", ejec_s.to_dict(orient="records"))

# -------------------------------------------------------------- funcion ----
pim_f = df_anual.groupby(["FUNCION", "NIVEL_GOB"], as_index=False)["PIM"].sum()
ejec_f = df_mensual.groupby(["FUNCION", "NIVEL_GOB", "MES"], as_index=False)[["DEVENGADO", "GIRADO"]].sum()
dump("funcion_pim", pim_f.to_dict(orient="records"))
dump("funcion_ejec", ejec_f.to_dict(orient="records"))

# ------------------------------------------------------- categoria/generica --
pim_c = df_anual.groupby(["CATEGORIA_GTO", "NIVEL_GOB"], as_index=False)["PIM"].sum()
ejec_c = df_mensual.groupby(["CATEGORIA_GTO", "NIVEL_GOB", "MES"], as_index=False)[["DEVENGADO"]].sum()
dump("categoria_pim", pim_c.to_dict(orient="records"))
dump("categoria_ejec", ejec_c.to_dict(orient="records"))

pim_g = df_anual.groupby(["GENERICA", "NIVEL_GOB"], as_index=False)["PIM"].sum()
ejec_g = df_mensual.groupby(["GENERICA", "NIVEL_GOB", "MES"], as_index=False)[["DEVENGADO"]].sum()
dump("generica_pim", pim_g.to_dict(orient="records"))
dump("generica_ejec", ejec_g.to_dict(orient="records"))

# ---------------------------------------------------------- top_pliegos ----
pim_pl = df_anual.groupby(["PLIEGO", "NIVEL_GOB"], as_index=False)["PIM"].sum()
dev_pl = df_mensual.groupby(["PLIEGO", "NIVEL_GOB"], as_index=False)[["DEVENGADO", "GIRADO"]].sum()
pliegos = pim_pl.merge(dev_pl, on=["PLIEGO", "NIVEL_GOB"], how="outer").fillna(0.0)
pliegos = pliegos[pliegos["PIM"] > 0].sort_values("PIM", ascending=False).head(60)
dump("top_pliegos", pliegos.to_dict(orient="records"))

# -------------------------------------------------------- top_proyectos ----
df_proy = df[df["TIPO_ACT_PROY"] == "2. PROYECTO"]
proy_anual = df_proy[df_proy["MES"] == "0"]
proy_mensual = df_proy[df_proy["MES"] != "0"]
pim_pr = proy_anual.groupby(["PRODUCTO_PROYECTO", "SECTOR", "NIVEL_GOB"], as_index=False)["PIM"].sum()
dev_pr = proy_mensual.groupby(["PRODUCTO_PROYECTO", "SECTOR", "NIVEL_GOB"], as_index=False)[["DEVENGADO"]].sum()
proyectos = pim_pr.merge(dev_pr, on=["PRODUCTO_PROYECTO", "SECTOR", "NIVEL_GOB"], how="outer").fillna(0.0)
proyectos = proyectos[proyectos["PIM"] > 0].sort_values("PIM", ascending=False).head(60)
dump("top_proyectos", proyectos.to_dict(orient="records"))

print("Listo.")
