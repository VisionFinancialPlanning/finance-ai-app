# Interfaz web para el MVP de finanzas personales con IA (optimizado con batch, categorías personalizadas y contexto regional Panamá y El Salvador)

import streamlit as st
import pandas as pd
import openai
import io

# Configura tu API Key de OpenAI aquí
openai.api_key = st.secrets.get("openai_key", "")

# Categorías personalizadas
CATEGORIAS = [
    "Hogar",
    "Prov. Mantenimiento y Reparaciones",
    "Prov. Artículos de Hogar",
    "Prov. Aguinaldo de empleados",
    "Supermercado",
    "Seguros",
    "Transporte",
    "Entretenimiento",
    "Vacaciones y Viajes",
    "Deudas",
    "SHOPPING",
    "Gastos Médicos",
    "Gastos Varios",
    "Inversiones a largo plazo",
    "Educación",
    "Transferencias"
]

# Función optimizada para clasificar múltiples descripciones con contexto local

def clasificar_batch(descripciones):
    prompt = f"Clasifica las siguientes transacciones. Devuélveme solo una categoría por línea, usando únicamente alguna de estas categorías:\n- " + "\n- ".join(CATEGORIAS) + "\n\n"
    prompt += (
        "Ten en cuenta estos ejemplos de comercios y servicios en Panamá y El Salvador:\n"
        "- ENSA (Panamá): Hogar\n"
        "- Naturgy (Panamá): Hogar\n"
        "- CASAPLAN, EPA, Rodelag: Artículos de Hogar o Reparaciones\n"
        "- Pricesmart, Súper 99, Super Selectos, Rey, Romero: Supermercado\n"
        "- Yappy, Nequi, Transferencias BAC: Transferencias\n"
        "- Uber, DiDi, Tigo Money: Transporte o Transferencias\n"
        "- Davivienda, Banco Agrícola, BAC, Credomatic: si es pago de tarjeta, clasificar como Deudas.\n"
        "Asegúrate de clasificar correctamente cualquier transacción que sea una transferencia bancaria o entre cuentas como 'Transferencias'.\n\n"
    )
    prompt += "\n".join([f"{i+1}. {desc}" for i, desc in enumerate(descripciones)])

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente que clasifica transacciones bancarias para Panamá y El Salvador."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1500
        )
        salida = response.choices[0].message.content.strip().split("\n")
        categorias = [line.strip().split(". ", 1)[-1] for line in salida if line.strip()]
        return categorias
    except Exception as e:
        return [f"Error: {str(e)}"] * len(descripciones)

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
        st.info("Clasificando gastos con IA en bloques...")
        descripciones = df[columna_nota].fillna('').astype(str).tolist()
        categorias = clasificar_batch(descripciones)
        df['Categoria AI'] = categorias[:len(df)]

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
