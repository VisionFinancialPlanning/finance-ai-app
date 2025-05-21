# Interfaz web para el MVP de finanzas personales con IA (actualizado a API Chat v1)

import streamlit as st
import pandas as pd
import openai
import io

# Configura tu API Key de OpenAI aquí
oai_key = st.secrets["openai_key"] if "openai_key" in st.secrets else ""
if oai_key:
    openai.api_key = oai_key
else:
    st.warning("Agrega tu OpenAI API Key en los secretos de Streamlit.")

# Función que usa IA (ChatCompletion) para categorizar según la descripción
def categorizar_gasto_ai(descripcion):
    prompt = f"""
    Categoriza esta transacción bancaria en una categoría financiera común (como 'Comida', 'Transporte', 'Salud', 'Vivienda', 'Entretenimiento', 'Servicios', 'Transferencias', 'Ingresos', 'Deuda', 'Compras').
    Solo responde con la categoría:

    Descripción: {descripcion}
    """

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente que clasifica transacciones financieras."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=10
    )
    return response.choices[0].message['content'].strip()

# App principal
st.title("💸 Clasificador Inteligente de Finanzas Personales")
st.markdown("Sube tu archivo de transacciones (Excel o CSV) y el sistema clasificará tus gastos usando IA.")

archivo = st.file_uploader("Sube tu archivo de transacciones", type=["xlsx", "csv"])

if archivo is not None:
    if archivo.name.endswith(".xlsx"):
        df = pd.read_excel(archivo)
    else:
        df = pd.read_csv(archivo)

    if 'Note' not in df.columns:
        st.error("Tu archivo debe contener una columna llamada 'Note' con la descripción del gasto.")
    else:
        st.info("Clasificando gastos con IA, esto puede tomar unos segundos...")
        df['Categoria AI'] = df['Note'].fillna('').apply(categorizar_gasto_ai)
        st.success("¡Listo! Aquí están tus datos clasificados:")
        st.dataframe(df)

        output = io.StringIO()
        df_export = df[['Date', 'Amount', 'Categoria AI']]
        df_export.columns = ['Date', 'Amount', 'Category']
        df_export.to_csv(output, index=False)
        st.download_button("Descargar archivo para Spendee", data=output.getvalue(), file_name="export_spendee.csv", mime="text/csv")
