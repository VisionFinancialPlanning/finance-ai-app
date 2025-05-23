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

PALABRAS_CLAVE = {
    "Transporte": ["uber", "didi", "ena", "terpel", "puma", "gasolina", "texaco"],
    "Supermercado": ["pricesmart", "súper 99", "riba smith", "xtra", "orgánica", "maxi despensa", "la colonia", "rey", "riba"],
    "Suscripciones": ["netflix", "spotify", "amazon", "adobe", "microsoft", "facebook", "canva", "wix"],
    "Gastos Médicos": ["alergias", "hospital", "laboratorio", "clínica", "médico", "odontólogo", "medicina"],
    "Entretenimiento": ["pizza hut", "kfc", "dominos", "starbucks", "cine", "restaurante", "mcdonalds", "paseo"],
    "Hogar": ["ensa", "naturgy", "alcaldía", "agua", "internet", "electricidad", "gas", "tigo","digicel","mas movil","movistar"],
    "Deudas": ["davivienda", "credito", "bac", "pago tarjeta", "cuota", "intereses"],
    "Transferencias": ["yappy", "nequi", "sinpe", "transferencia", "mismo titular"],
    "Salario": ["salario", "pago planilla"],
    "Transferencias entrantes": ["abono", "ingreso recibido", "remesa"]
}

HISTORIAL_CATEGORIAS = {}

def clasificar_batch(descripciones):
    categorias_totales = []
    nuevas = []
    posiciones_nuevas = []

    for i, desc in enumerate(descripciones):
        desc_lower = desc.lower()
        if desc in HISTORIAL_CATEGORIAS:
            categorias_totales.append(HISTORIAL_CATEGORIAS[desc])
        else:
            asignada = None
            for categoria, palabras in PALABRAS_CLAVE.items():
                if any(palabra in desc_lower for palabra in palabras):
                    asignada = categoria
                    break
            if asignada:
                HISTORIAL_CATEGORIAS[desc] = asignada
                categorias_totales.append(asignada)
            else:
                categorias_totales.append(None)
                nuevas.append(desc)
                posiciones_nuevas.append(i)

    if nuevas:
        instrucciones = f"""Clasifica las siguientes transacciones. Devuélveme solo una categoría por línea, usando únicamente alguna de estas categorías:
{chr(10).join(CATEGORIAS)}

Ten en cuenta que los siguientes son solo ejemplos de comercios y servicios comunes en Centroamérica. Usa este listado como guía, pero también debes categorizar correctamente otras marcas o nombres nuevos que no estén mencionados:
ENSA, Naturgy, Tigo, Mas movil: Hogar
Pricesmart, Súper 99, Super Selectos, Walmart, Orgánica, Riba Smith, El Rey, Xtra, La Colonia, Maxi Despensa: Supermercado
Wix, Microsoft, Netflix, Adobe, Canva, Docusign, Facebook, facebk: Suscripciones
Centro de alergias, Hospital Nacional, Laboratorios Centroamericanos: Gastos Médicos
Yappy, Nequi, SINPE, Transferencia entre cuentas: Transferencias
Uber, DiDi, ENA corredores, Gasolina Terpel, Uno, Puma: Transporte
Davivienda, Banco Agrícola, BAC, Credomatic, Banrural: Deudas
Corte Argentino, Dominos, Pizza Hut, Starbucks, KFC, Rausch, McDonalds: Entretenimiento
Asegúrate de que si la nota contiene la palabra \"Uber\", se clasifique como Transporte. Si contiene otra palabra, clasifícala según el contexto general, sin asumir automáticamente que es Transporte.
Si dos notas tienen el mismo texto (por ejemplo, dos transacciones que dicen \"Uber\"), deben recibir la misma categoría.
Si es ingreso: Salario, Transferencias entrantes u Other
Si el monto es positivo en 'amount' o 'monto': es ingreso; si es negativo: es gasto"""

        lista_transacciones = "\n".join([f"{j+1}. {desc}" for j, desc in enumerate(nuevas)])
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
            for i, categoria in enumerate(salida[:len(nuevas)]):
                categorias_totales[posiciones_nuevas[i]] = categoria
                HISTORIAL_CATEGORIAS[nuevas[i]] = categoria
            for j in range(len(nuevas), len(posiciones_nuevas)):
                categorias_totales[posiciones_nuevas[j]] = "No clasificado"
        except Exception as e:
            for i in posiciones_nuevas:
                categorias_totales[i] = f"Error: {str(e)}"

    return categorias_totales

# Interfaz Streamlit
st.title("🔍 Categorizador de Transacciones Personales con IA")
st.markdown("Vision Financial Planning IA")

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
            st.download_button("Descargar como CSV", data=output.getvalue(), file_name="export_spendee.csv", mime="text/csv")

            excel_output = io.BytesIO()
            with pd.ExcelWriter(excel_output, engine='xlsxwriter') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Transacciones')
            st.download_button("Descargar como Excel", data=excel_output.getvalue(), file_name="export_spendee.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
