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
    prompt = f"Clasifica las siguientes transacciones. Devuélveme solo una categoría por línea, usando únicamente alguna de estas categorías:\n" + "\n".join(CATEGORIAS) + "\n\n"
    prompt += (
        "Ten en cuenta estos ejemplos de comercios y servicios en Panamá y El Salvador:\n"
        "ENSA (Panamá): Hogar\n"
        "Naturgy (Panamá): Hogar\n"
        "CASAPLAN, EPA, Rodelag: Artículos de Hogar o Reparaciones\n"
        "Pricesmart, Súper 99, Super Selectos, Rey, Romero: Supermercado\n"
        "Yappy, Nequi, Transferencias BAC: Transferencias\n"
        "Uber, DiDi, Tigo Money: Transporte o Transferencias\n"
        "Davivienda, Banco Agrícola, BAC, Credomatic: si es pago de tarjeta, clasificar como Deudas.\n"
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
        if len(categorias) != len(descripciones):
            raise ValueError("La cantidad de categorías devueltas no coincide con las descripciones procesadas.")
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
        if len(categorias) == len(df):
            df['Categoria AI'] = categorias

            st.success("¡Listo! Aquí están tus datos clasificados:")
            st.dataframe(df)

            output = io.StringIO()
            df_export = df.copy()
            df_export = df_export.rename(columns={
                columna_fecha: 'Date',
                columna_monto: 'Amount',
                columna_nota: 'Note',
                'Categoria AI': 'Category'
            })
            df_export.to_csv(output, index=False)
            st.download_button("Descargar archivo completo (Spendee + nota + todo)", data=output.getvalue(), file_name="export_spendee.csv", mime="text/csv")
        else:
            st.error("Error: El número de categorías no coincide con el número de transacciones. Por favor, intenta nuevamente.")
