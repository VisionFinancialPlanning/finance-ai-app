import streamlit as st
import pandas as pd
import openai
import io

openai.api_key = st.secrets.get("openai_key", "")

CATEGORIAS = [
    "Hogar", "Prov. Mantenimiento y Reparaciones", "Prov. Artículos de Hogar", "Prov. Aguinaldo de empleados",
    "Supermercado", "Seguros", "Transporte", "Entretenimiento", "Vacaciones y Viajes", "Deudas", "SHOPPING",
    "Gastos Médicos", "Gastos Varios", "Inversiones a largo plazo", "Educación", "Transferencias",
    "Transferencias entrantes", "Salario", "Other"
]

def clasificar_batch(descripciones):
    categorias_totales = []
    bloque = 50
    for i in range(0, len(descripciones), bloque):
        subset = descripciones[i:i + bloque]
        instrucciones = f"""Clasifica las siguientes transacciones. Devuélveme solo una categoría por línea, usando únicamente alguna de estas categorías:
{chr(10).join(CATEGORIAS)}

Ten en cuenta estos ejemplos de comercios y servicios comunes en Centroamérica:
ENSA, Naturgy: Hogar
Pricesmart, Súper 99, Super Selectos, Walmart, Orgánica, Riba Smith, El Rey, Xtra, La Colonia, Maxi Despensa: Supermercado
Wix, Microsoft, Netflix, Adobe, Canva, Docusign, Facebook: Suscripciones
Centro de alergias, Hospital Nacional, Laboratorios Centroamericanos: Gastos Médicos
Yappy, Nequi, SINPE, Transferencia entre cuentas: Transferencias
Uber, DiDi, ENA corredores, Gasolina Terpel, Uno, Puma, Tigo: Transporte
Davivienda, Banco Agrícola, BAC, Credomatic, Banrural: Deudas
Corte Argentino, Dominos, Pizza Hut, Starbucks, KFC, Rausch, McDonalds: Entretenimiento
Asegúrate de que si la nota contiene la palabra "Uber", se clasifique como Transporte. Si contiene otra palabra, clasifícala según el contexto general, sin asumir automáticamente que es Transporte.
Si dos notas tienen el mismo texto (por ejemplo, dos transacciones que dicen "Uber"), deben recibir la misma categoría.
Si es ingreso: Salario, Transferencias entrantes u Other
Si el monto es positivo en 'amount' o 'monto': es ingreso; si es negativo: es gasto
"""
        lista_transacciones = "\n".join([f"{j+1}. {desc}" for j, desc in enumerate(subset)])
        prompt = instrucciones + "\n" + lista_transacciones

        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Eres un asistente experto en clasificar finanzas personales en Centroamérica."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=1500
            )
            salida = response.choices[0].message.content.strip().split("\n")
            categorias = salida[:len(subset)]
            while len(categorias) < len(subset):
                categorias.append("No clasificado")
            categorias_totales.extend(categorias)
        except Exception as e:
            categorias_totales.extend([f"Error: {str(e)}"] * len(subset))

    return categorias_totales

# Interfaz Streamlit
st.title("💸 Clasificador Inteligente de Finanzas Personales")
st.markdown("Sube tu archivo de transacciones (Excel o CSV) y el sistema clasificará tus gastos usando IA.")

archivo = st.file_uploader("Sube tu archivo de transacciones", type=["xlsx", "xls", "csv"])

if archivo is not None:
    if archivo.name.endswith(".xlsx") or archivo.name.endswith(".xls"):
        df = pd.read_excel(archivo, header=None)
        df.columns = df.iloc[0]
        df = df[1:].reset_index(drop=True)
        df = df.dropna(how='all')
        df = df.loc[:, ~df.columns.isna()]
        df.columns = df.columns.fillna("Unknown")
        df.columns = df.columns.astype(str)
        if df.columns.duplicated().any():
            df.columns = pd.io.parsers.ParserBase({'names': df.columns})._maybe_dedup_names(df.columns)
    else:
        df = pd.read_csv(archivo)

    columnas = df.columns.str.lower()
    columna_nota = next((col for col in df.columns if str(col).lower() in ['note', 'nota', 'descripcion', 'descripción', 'detalle', 'concepto', 'glosa']), None)
    columna_fecha = next((col for col in df.columns if str(col).lower() in ['date', 'fecha', 'fecha operación', 'fecha transacción', 'f. operación', 'f. transacción', 'f. mov']), None)
    columna_monto = next((col for col in df.columns if str(col).lower() in ['amount', 'monto', 'dolares', 'usd', 'importe', 'valor', 'debit', 'credit', 'debitos', 'creditos']), None)

    if not columna_nota:
        st.error("Tu archivo debe contener una columna con la descripción del gasto, como 'Nota', 'Descripción', 'Detalle', 'Concepto' o similares.")
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
                columna_fecha: 'Fecha',
                columna_monto: 'Monto',
                columna_nota: 'Nota',
                'Categoria AI': 'Categoría'
            })
            df_export.to_csv(output, index=False)
            st.download_button("Descargar archivo completo (Spendee + nota + todo)", data=output.getvalue(), file_name="export_spendee.csv", mime="text/csv")
        else:
            st.error("Error: El número de categorías no coincide con el número de transacciones. Por favor, intenta nuevamente.")

