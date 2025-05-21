# Interfaz web para el MVP de finanzas personales con IA (actualizado a OpenAI v1.0+ API)

import streamlit as st
import pandas as pd
import openai
import io

# Configura tu API Key de OpenAI aquí
openai.api_key = st.secrets.get("openai_key", "")

# Función que usa IA (ChatCompletion) para categorizar según la descripción
def categorizar_gasto_ai(descripcion):
    if not descripcion.strip():
        return "Sin descripción"

    prompt = f"""
    Categoriza esta transacción bancaria en una categoría financiera común. Escoge una de las siguientes: 'Comida', 'Transporte', 'Salud', 'Vivienda', 'Entretenimiento', 'Servicios', 'Transferencias', 'Ingresos', 'Deuda', 'Compras'.

    Descripción: {descripcion}
    Categoría:
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente que clasifica transacciones financieras."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=10
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"

# App principal
st.title("💸 Clasificador Inteligente de Finanzas Personales")
st.markdown("Sube tu archivo de transacciones (Excel o CSV) y el sistema clasificará tus gastos usando IA.")

archivo = st.file_uploader("Sube tu archivo de transacciones", type=["xlsx", "csv"])

if archivo is not None:
    if archivo.name.endswith(".xlsx"):
        df = pd.read_excel(archivo)
    else:
        df = pd.read_csv(archivo)

    columnas = df.columns.str.lower()
    columna_nota = next((col for col in df.columns if col.lower() in ['note', 'nota']), None)
    columna_fecha = next((col for col in df.columns if col.lower() in ['date', 'fecha']), None)
    columna_monto = next((col for col in df.columns if col.lower() in ['amount', 'monto']), None)

    if not columna_nota:
        st.error("Tu archivo debe contener una columna llamada 'Note' o 'Nota' con la descripción del gasto.")
    else:
        st.info("Clasificando gastos con IA, esto puede tomar unos segundos...")
        df['Categoria AI'] = df[columna_nota].fillna('').apply(categorizar_gasto_ai)
        st.success("¡Listo! Aquí están tus datos clasificados:")
        st.dataframe(df)

        output = io.StringIO()
        columnas_exportar = [col for col in [columna_fecha, columna_monto, 'Categoria AI'] if col in df.columns]

        if len(columnas_exportar) < 3:
            st.error("Tu archivo debe tener columnas llamadas 'Date'/'Fecha' y 'Amount'/'Monto' para poder exportar a Spendee.")
        else:
            df_export = df[columnas_exportar]
            df_export.columns = ['Date', 'Amount', 'Category']
            df_export.to_csv(output, index=False)
            st.download_button("Descargar archivo para Spendee", data=output.getvalue(), file_name="export_spendee.csv", mime="text/csv")
