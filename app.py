# Interfaz web para el MVP de finanzas personales con IA (optimizado con batch, categorías personalizadas y contexto regional ampliado para Centroamérica)

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
    "Transferencias",
    "Transferencias entrantes",
    "Salario",
    "Other"
]

# Función optimizada para clasificar múltiples descripciones con contexto regional ampliado

def clasificar_batch(descripciones):
    prompt = f"Clasifica las siguientes transacciones. Devuélveme solo una categoría por línea, usando únicamente alguna de estas categorías:\n" + "\n".join(CATEGORIAS) + "\n\n"
    prompt += (
        "Ten en cuenta estos ejemplos de comercios y servicios comunes en Centroamérica (Panamá, El Salvador, Guatemala, Honduras, Nicaragua, Costa Rica):\n"
        "ENSA, Naturgy: Hogar\n"
        "CASAPLAN, EPA, Rodelag, Cemaco, Construrama, Novex: Artículos de Hogar o Reparaciones\n"
        "Pricesmart, Súper 99, Super Selectos, Rey, Romero, Mini Market, Orgánica, La Colonia, Walmart, Perimercados: Supermercado\n"
        "Wix, Microsoft, Spotify, Netflix, Amazon, iCloud, Docusign, Disney+, YouTube Premium: Gastos Varios o Suscripciones\n"
        "Centro de alergias, Clínicas médicas, Hospitales, Laboratorios: Gastos Médicos\n"
        "Yappy, Nequi, Transferencias BAC, Sinpe, Tigo Money: Transferencias\n"
        "Uber, DiDi, ENA corredores, Transmetro, TuBus, Movilízate: Transporte\n"
        "Davivienda, Banco Agrícola, BAC, Credomatic, Banrural, Banco Industrial: si es pago de tarjeta o crédito, clasificar como Deudas.\n"
        "Corte Argentino, restaurantes o comida rápida: Entretenimiento\n"
        "Si la transacción es un ingreso, como crédito de salario, bonificación, devolución de compra o transferencia recibida, clasificar como: 'Salario', 'Transferencias entrantes' u 'Other'.\n"
        "Si la columna del archivo se llama 'debit' o 'debitos', considera que es un gasto. Si se llama 'credit' o 'creditos', considera que es un ingreso.\n"
        "Si solo hay una columna llamada 'amount' o 'monto', considera que los valores negativos son gastos y los positivos ingresos.\n"
        "También considera que algunas hojas de Excel pueden tener encabezados combinados. Lee la fila correcta con datos.\n"
        "Clasifica correctamente cualquier transferencia bancaria entre cuentas como 'Transferencias'.\n\n"
    )
    prompt += "\n".join([f"{i+1}. {desc}" for i, desc in enumerate(descripciones)])

    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente que clasifica transacciones bancarias para usuarios en Centroamérica. Sé preciso y usa solo las categorías indicadas."},
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

archivo = st.file_uploader("Sube tu archivo de transacciones", type=["xlsx", "xls", "csv"])

if archivo is not None:
    if archivo.name.endswith(".xlsx") or archivo.name.endswith(".xls"):
        # leer con encabezado en la primera fila con datos válidos
        df = pd.read_excel(archivo, header=None)
        df.columns = df.iloc[0]  # toma la primera fila como encabezado
        df = df[1:].reset_index(drop=True)
        df = df.dropna(how='all')  # elimina filas completamente vacías
        df = df.loc[:, ~df.columns.isna()]  # elimina columnas vacías
        df.columns = df.columns.fillna("Unknown")
        df.columns = df.columns.astype(str)
        if df.columns.duplicated().any():
            df.columns = pd.io.parsers.ParserBase({'names': df.columns})._maybe_dedup_names(df.columns)
    else:
        df = pd.read_csv(archivo)

    columnas = df.columns.str.lower()
    columna_nota = next((col for col in df.columns if str(col).lower() in ['note', 'nota']), None)
    columna_fecha = next((col for col in df.columns if str(col).lower() in ['date', 'fecha']), None)
    columna_monto = next((col for col in df.columns if str(col).lower() in ['amount', 'monto', 'debit', 'credit', 'debitos', 'creditos']), None)

    if not columna_nota:
        st.error("Tu archivo debe contener una columna llamada 'Note' o 'Nota' con la descripción del gasto.")
    else:
        st.info("Clasificando gastos con IA en bloques...")
        descripciones = df[columna_nota].fillna('').astype(str).tolist()
        categorias = clasificar_batch(descripciones)
        if len(categorias) == len(df):
            df['Categoria AI'] = categorias

            st.success("¡Listo! Aquí están tus datos clasificados:")
            try:
                st.dataframe(df)
            except Exception as e:
                st.warning(f"No se pudo mostrar la tabla completa. {str(e)}")

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
