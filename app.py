import streamlit as st
from ScalesBalances import (
    cargar_json, 
    procesar_certificado, 
    convertir_unidad, 
    obtener_info_certificado
)
from htmlTemplates import CSS_STYLES, LOGO_TITLE_HTML, get_image_base64
from datetime import datetime, date

# Get the background image in base64
background_base64 = get_image_base64("images/background.png")

# Apply custom CSS styles
st.markdown(CSS_STYLES, unsafe_allow_html=True)

# Show the title with gradient style
st.markdown(LOGO_TITLE_HTML, unsafe_allow_html=True)

# Initialize session state if necessary
if 'opcion' not in st.session_state:
    st.session_state.opcion = 'Enter certificate number'
if 'numero_certificado' not in st.session_state:
    st.session_state.numero_certificado = ''

# Load data
@st.cache_data
def load_data():
    return {
        'labrowe_datalogger': cargar_json("doc/LabRoweDatalogger.json"),
        'certificado_balance': cargar_json("doc/Balances&Scales.json"),
        'thermodynamics': cargar_json("doc/Thermodynamics.json")
    }

data = load_data()

# Application title
st.title('Calibration Assistant')

def apply_style(text, color=None, bold=False):
    if bold:
        text = f"**{text}**"
    if color:
        text = f"<font color='{color}'>{text}</font>"
    return text

def calculate_expiration_status(due_date_str):
    try:
        due_date = datetime.strptime(due_date_str, '%m/%d/%Y').date()
        current_date = date.today()
        days_until_expiration = (due_date - current_date).days
        
        if days_until_expiration < 0:
            return "Expired", f"{abs(days_until_expiration)} days ago"
        elif days_until_expiration == 0:
            return "Expires today", "Today"
        else:
            return "Valid", f"{days_until_expiration} days remaining"
    except ValueError:
        return "Invalid date", "Unable to calculate"

def display_certificate_info(certificado):
    st.markdown(f"## Certificate Information {apply_style(certificado.get('CertNo', 'N/A'), color='#ed6f38', bold=True)}", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Equipment Details")
        st.markdown(f"**Equipment Type:** {certificado.get('EquipmentType', 'N/A')}")
        st.markdown(f"**Description:** {certificado.get('AssetDescription', 'N/A')}")
        st.markdown(f"**Manufacturer:** {certificado.get('Manufacturer', 'N/A')}")
        st.markdown(f"**Model:** {apply_style(certificado.get('Model', 'N/A'), bold=True)}")
        st.markdown(f"**Operating Range:** {certificado.get('OperatingRange', 'N/A')}")

    with col2:
        st.markdown("### Environmental Conditions")
        env_conditions = certificado.get('EnvironmentalConditions', {})
        st.markdown(f"**Temperature:** {env_conditions.get('Temperature', 'N/A')}")
        st.markdown(f"**Relative Humidity:** {env_conditions.get('RelativeHumidity', 'N/A')}")
        if env_conditions.get('BarometricPressure'):
            st.markdown(f"**Barometric Pressure:** {env_conditions.get('BarometricPressure', 'N/A')}")
    
    st.markdown("### Standards Used")
    table_header = "| Description | Serial No | Calibration Date | Due Date | Status |\n|-------------|-----------|------------------|----------|--------|"
    table_rows = []
    for standard in certificado.get('Standards', []):
        status, time_info = calculate_expiration_status(standard.get('DueDate', ''))
        color = '#00FF00' if status == 'Valid' else '#FF0000'
        table_rows.append(f"| {standard.get('Description', 'N/A')} | {standard.get('SerialNo', 'N/A')} | {standard.get('CalDate', 'N/A')} | {standard.get('DueDate', 'N/A')} | {apply_style(f'{status} ({time_info})', color=color)} |")
    
    table_content = "\n".join([table_header] + table_rows)
    st.markdown(table_content, unsafe_allow_html=True)
    
    st.markdown("### Remarks")
    st.markdown(f"_{certificado.get('Remarks', 'N/A')}_")

# Navigation menu
opcion = st.sidebar.radio('Select an option:', ['Enter certificate number', 'Search certificate by model', 'Exit'], index=0 if 'opcion' not in st.session_state else ['Enter certificate number', 'Search certificate by model', 'Exit'].index(st.session_state.opcion))

if opcion == 'Enter certificate number':
    st.header('Search by Certificate')
    certificado_objetivo = st.text_input("Enter the target certificate number:", value=st.session_state.numero_certificado if 'numero_certificado' in st.session_state else '')
    
    if certificado_objetivo:
        try:
            info_certificado = obtener_info_certificado(data['labrowe_datalogger'], certificado_objetivo)
            display_certificate_info(info_certificado)

            st.markdown("---")
            st.markdown("### Uncertainty Calculation")

            grupo_seleccionado = st.selectbox('Target Group:', ['Select group'] + [g['Group'] for g in next(cert for cert in data['labrowe_datalogger'] if cert['CertNo'] == certificado_objetivo)['Datasheet']])
            
            if grupo_seleccionado != 'Select group':
                mediciones = next(g['Measurements'] for g in next(cert for cert in data['labrowe_datalogger'] if cert['CertNo'] == certificado_objetivo)['Datasheet'] if g['Group'] == grupo_seleccionado)
                nominal_seleccionado = st.selectbox('Target Nominal Value:', ['Select nominal value'] + [str(m['Nominal']) for m in mediciones])
                
                if nominal_seleccionado != 'Select nominal value':
                    medicion_seleccionada = next(m for m in mediciones if str(m['Nominal']) == nominal_seleccionado)
                    
                    if st.button('Perform calculation'):
                        try:
                            resultado = procesar_certificado(
                                data['labrowe_datalogger'],
                                data['certificado_balance'],
                                data['thermodynamics'],
                                certificado_objetivo,
                                grupo_seleccionado,
                                nominal_seleccionado,
                                medicion_seleccionada['Units']
                            )
                            
                            st.success(f"""
                            **Calculation Results:**
                            - **Target Group**: {grupo_seleccionado}
                            - **Target Nominal Value**: {nominal_seleccionado} {medicion_seleccionada['Units']}
                            - **Measurement Uncertainty**: {resultado['meas_uncert']} {medicion_seleccionada['Units']}
                            - **CMC used**: {resultado['cmc_used']}
                            - **Total Uncertainty**: {resultado['total_uncertainty'][0]}, {resultado['total_uncertainty'][1]}, {resultado['total_uncertainty'][2]}
                            - **TUR**: {medicion_seleccionada['TUR']}
                            """)
                        except Exception as e:
                            st.error(f"Error during calculation: {str(e)}")
        except ValueError as e:
            st.warning(f"Target certificate not found: {str(e)}")

elif opcion == 'Search certificate by model':
    st.header('Search by Model')
    modelo_objetivo = st.text_input("Enter the target model:")

    if modelo_objetivo:
        modelos_disponibles = list(set([cert['Model'] for cert in data['labrowe_datalogger'] if modelo_objetivo.lower() in cert['Model'].lower()]))
        if modelos_disponibles:
            modelo_seleccionado = st.selectbox('Available models:', modelos_disponibles)
            certificados_modelo = [cert for cert in data['labrowe_datalogger'] if cert['Model'] == modelo_seleccionado]

            st.markdown(f"### Available certificates for model {apply_style(modelo_seleccionado, color='#ed6f38', bold=True)}", unsafe_allow_html=True)
            
            # Create a markdown table
            table_header = "| Certificate | Description | Operating Range | Due Date | Status |\n|------------|-------------|------------------|----------|--------|"
            table_rows = []
            for cert in certificados_modelo:
                status, time_info = calculate_expiration_status(cert['Standards'][0]['DueDate'])
                color = '#00FF00' if status == 'Valid' else '#FF0000'
                due_date = cert['Standards'][0]['DueDate']
                table_rows.append(f"| {apply_style(cert['CertNo'], bold=True)} | {cert['AssetDescription']} | {cert['OperatingRange']} | {due_date} | {apply_style(f'{status} ({time_info})', color=color)} |")
            
            table_content = "\n".join([table_header] + table_rows)
            st.markdown(table_content, unsafe_allow_html=True)

            certificado_seleccionado = st.selectbox(
                "Select a certificate number:",
                [cert['CertNo'] for cert in certificados_modelo]
            )

            if st.button('Use this certificate number'):
                st.session_state['numero_certificado'] = certificado_seleccionado
                st.session_state['opcion'] = 'Enter certificate number'
                st.rerun()
        else:
            st.warning("No models found matching your search.")
elif opcion == 'Exit':
    st.stop()

# Add a footer
st.markdown("---")
st.markdown("© 2023 Calibration Assistant. All rights reserved.")