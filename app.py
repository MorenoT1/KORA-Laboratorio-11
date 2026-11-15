import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(layout="wide")
st.title("KORA - Clientes")
st.caption("Elaborado con datos de clientes de Agosto 2025 a Septiembre 2026")

df_clientes = pd.read_csv("KORA_clientes.csv", parse_dates=["fecha_registro"])
df_pedidos = pd.read_csv("KORA_pedidos.csv", parse_dates=["fecha_pedido"])

st.sidebar.header("FILTROS")
filtro_canal = st.sidebar.multiselect(label="CANALES",
                            options=df_clientes.canal_adquisicion.unique(),
                            default=df_clientes.canal_adquisicion.unique())
filtro_ciudad = st.sidebar.multiselect(label="CIUDAD",
                            options=df_clientes.ciudad.unique(),
                            default=df_clientes.ciudad.unique())
 
df_intermedio = (df_pedidos.groupby("id_cliente", as_index=False).agg(n_pedidos=("id_pedido", "count")))

df_clientes_filtrado = df_clientes[df_clientes.canal_adquisicion.isin(filtro_canal) &
                        df_clientes.ciudad.isin(filtro_ciudad)]

df_final = df_clientes_filtrado.merge(df_intermedio, how="left", on="id_cliente")


df_resumen = (df_pedidos.groupby("id_cliente", as_index=False).agg(
            ingreso_total=("ingreso_neto_cop", "sum"),ultima_compra=("fecha_pedido", "max")))

df_final = df_final.merge(df_resumen, how="left", on="id_cliente")
df_final["n_pedidos"] = df_final.n_pedidos.fillna(0).astype(int)
df_final["ingreso_total"] = df_final.ingreso_total.fillna(0)
fecha_corte = pd.Timestamp("2026-10-31")
df_final["dias_sin_compra"] = (fecha_corte - df_final.ultima_compra).dt.days

def segmento(f):
    if f.n_pedidos == 0:
        return "Sin compra"
    if f.dias_sin_compra > 90:
        return "En pausa"
    if f.n_pedidos >= 3:
        return "Fieles"
    if f.n_pedidos == 1:
        return "Primerizos"
    return "En desarrollo"

if len(df_final) > 0:
    df_final["segmento"] = df_final.apply(segmento, axis=1)
else:
    df_final["segmento"] = ""

segmentos = ["Sin compra", "Primerizos", "En desarrollo", "Fieles", "En pausa"]

filtro_segmento = st.sidebar.multiselect(label="SEGMENTO",options=segmentos,default=segmentos)
filtro_preferencia = st.sidebar.multiselect(label="PREFERENCIA DECLARADA",
                                    options=df_clientes.preferencia_declarada.unique(),
                                    default=df_clientes.preferencia_declarada.unique())

df_final = df_final[df_final.segmento.isin(filtro_segmento) &
    df_final.preferencia_declarada.isin(filtro_preferencia)].copy()

compradores = df_final.query("n_pedidos > 0").shape[0]
pedidos = df_final.n_pedidos.sum()
ingreso = df_final.ingreso_total.sum()
una_compra = df_final.query("n_pedidos == 1").shape[0]
recompradores = df_final.query("n_pedidos >= 2").shape[0]

if compradores > 0:
    recompra = round(recompradores / compradores * 100, 1)
    porcentaje_una_compra = round(una_compra / compradores * 100, 1)
    valor_recompra = str(recompra) + "%"
    valor_una_compra = str(porcentaje_una_compra) + "%"
else:
    valor_recompra = "N/D"
    valor_una_compra = "N/D"

if pedidos > 0:
    ticket = ingreso / pedidos
else:
    ticket = 0

st.subheader("Indicadores generales")
a, b, c, d = st.columns(4)
with a:
    st.metric(label="COMPRADORES", value=compradores, border=True)
with b:
    st.metric(label="PEDIDOS", value=int(pedidos), border=True)
with c:
    st.metric(label="INGRESO NETO", value=f"${ingreso / 1e6:.1f} M", border=True)
with d:
    st.metric(label="RECOMPRA", value=valor_recompra, border=True)

st.subheader("Clientes por segmento")
tabla = df_final.groupby("segmento").size().reset_index(name="clientes")
if not tabla.empty:
    fig = px.bar(tabla, x="segmento", y="clientes", text="clientes")
    st.plotly_chart(fig, width="stretch")
else:
    st.info("No hay clientes para esta selección.")

pedidos_f = df_pedidos[df_pedidos.id_cliente.isin(df_final.id_cliente)].copy()

st.subheader("Ingresos por categoría")
if not pedidos_f.empty:
    cat = pedidos_f.groupby("categoria", as_index=False)["ingreso_neto_cop"].sum()
    cat["millones"] = cat.ingreso_neto_cop / 1e6
    fig = px.bar(
        cat.sort_values("millones"),
        x="millones", y="categoria", orientation="h",
        labels={"millones": "Ingresos (millones de COP)", "categoria": "Categoría"}
    )
    st.plotly_chart(fig, width="stretch")
else:
    st.info("No hay pedidos para esta selección.")

st.subheader("Pedidos por mes")
if not pedidos_f.empty:
    pedidos_f["mes"] = pedidos_f.fecha_pedido.dt.to_period("M").astype(str)
    serie = pedidos_f.groupby("mes").size().reset_index(name="pedidos")
    fig = px.line(serie, x="mes", y="pedidos", markers=True)
    st.plotly_chart(fig, width="stretch")
else:
    st.info("No hay pedidos para esta selección.")

st.subheader("Segunda compra por canal")
st.write("La tasa de recompra mide los compradores con dos o más pedidos sobre el total de "
    "compradores. No basta con esa tasa: también importa cuántos clientes tienen "
    "exactamente una compra. Usamos barras porque permiten comparar los canales fácilmente.")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="UNA COMPRA", value=una_compra, border=True)
with col2:
    st.metric(label="% UNA COMPRA", value=valor_una_compra, border=True)
with col3:
    st.metric(label="TICKET PROMEDIO", value=f"${ticket:,.0f}", border=True)

df_compradores = df_final.query("n_pedidos > 0").copy()
df_compradores["recompra"] = df_compradores.n_pedidos >= 2
df_compradores["una_compra"] = df_compradores.n_pedidos == 1

df_canales = (df_compradores.groupby("canal_adquisicion", as_index=False).agg(
        compradores=("id_cliente", "count"),
        recompradores=("recompra", "sum"),
        una_compra=("una_compra", "sum")))

if not df_canales.empty:df_canales["tasa_recompra"] = (df_canales.recompradores / df_canales.compradores * 100).round(1)

izquierda, derecha = st.columns(2)

with izquierda:
    st.markdown("**Tasa de recompra por canal**")
    if not df_canales.empty:
        fig = px.bar(df_canales.sort_values("tasa_recompra"),
            x="tasa_recompra",y="canal_adquisicion",orientation="h",
            text="tasa_recompra",hover_data=["compradores", "recompradores"],
            labels={"tasa_recompra": "Recompra (%)", "canal_adquisicion": "Canal"})
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No hay compradores en esta selección.")

with derecha:
    st.markdown("**Clientes con una compra por canal**")
    if not df_canales.empty:
        fig = px.bar(df_canales.sort_values("una_compra"),
            x="una_compra",y="canal_adquisicion",orientation="h",
            text="una_compra",labels={"una_compra": "Clientes con una compra", "canal_adquisicion": "Canal"})
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No hay compradores en esta selección.")

st.subheader("Resultados")
if not df_canales.empty:
    mayor = df_canales.sort_values("una_compra", ascending=False).iloc[0]
    menor = df_canales.sort_values("tasa_recompra").iloc[0]

    if mayor.canal_adquisicion == menor.canal_adquisicion:
        st.write(f"En esta selección, {mayor.canal_adquisicion} tiene más clientes con una "
            "compra y la menor tasa de recompra. Esto no siempre tiene que coincidir.")
    else:
        st.write(f"El mayor volumen está en {mayor.canal_adquisicion}, pero la menor "
            f"tasa de recompra está en {menor.canal_adquisicion}. No son lo mismo.")

    if mayor.una_compra > 0:
        st.subheader("Canal recomendado")
        st.write(f"Recomendamos comenzar por {mayor.canal_adquisicion}, con "
            f"{mayor.una_compra} clientes que han comprado una sola vez y "
            f"{mayor.tasa_recompra}% de recompra. Es un canal con una buena "
            "cantidad de posibles segundas compras. Sin embargo, no sabemos por "
            "qué estos clientes no han regresado. Probaríamos una campaña con un "
            "grupo de control y compararíamos la tasa de segunda compra a 30 días.")
    else:
        st.info("No hay clientes con una compra para recomendar un canal.")
else:
    st.info("No hay compradores para analizar.")