
# ScalesBalances.py
import streamlit as st
import json
import math
import re

def cargar_json(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return json.load(file)
    except UnicodeDecodeError:
        with open(filename, 'r', encoding='iso-8859-1') as file:
            return json.load(file)
    except Exception as e:
        raise Exception(f"Error al cargar el archivo {filename}: {e}")

def buscar_en_labrowe_datalogger(labrowe_datalogger_data, certificado_objetivo, grupo_objetivo, nominal_objetivo_str, unidad_objetivo):
    try:
        nominal_objetivo = float(nominal_objetivo_str)
    except ValueError:
        raise ValueError(f"Error al convertir el valor nominal '{nominal_objetivo_str}' a float")

    for certificado in labrowe_datalogger_data:
        if certificado['CertNo'] == certificado_objetivo:
            for datasheet in certificado['Datasheet']:
                if datasheet['Group'] == grupo_objetivo:
                    for measurement in datasheet['Measurements']:
                        if measurement['Units'] == unidad_objetivo and abs(float(measurement['Nominal']) - nominal_objetivo) < 1e-6:
                            return float(measurement['MeasUncert'])
    raise ValueError(f"No se encontró coincidencia para el certificado {certificado_objetivo}, grupo {grupo_objetivo}, nominal {nominal_objetivo_str}, unidad {unidad_objetivo}")

def elegir_modelo(labrowe_datalogger_data):
    input_usuario = input("Ingrese las primeras letras del modelo: ").upper()
    modelos_disponibles = []
    for certificado in labrowe_datalogger_data:
        modelo = certificado['Model']
        if modelo not in modelos_disponibles and modelo.upper().startswith(input_usuario):
            modelos_disponibles.append(modelo)
    if not modelos_disponibles:
        raise Exception("No se encontraron modelos que coincidan con su búsqueda.")
    print("Modelos disponibles que coinciden con su búsqueda:")
    for i, modelo in enumerate(modelos_disponibles, start=1):
        print(f"{i}. {modelo}")
    seleccion = int(input("Seleccione el número del modelo deseado: ")) - 1
    if seleccion < 0 or seleccion >= len(modelos_disponibles):
        raise ValueError("Selección de modelo inválida.")
    return modelos_disponibles[seleccion]

def elegir_grupo(labrowe_datalogger_data, certificado_objetivo):
    grupos_disponibles = []
    for certificado in labrowe_datalogger_data:
        if certificado['CertNo'] == certificado_objetivo:
            for datasheet in certificado['Datasheet']:
                grupo = datasheet['Group']
                if grupo not in grupos_disponibles:
                    grupos_disponibles.append(grupo)
    if not grupos_disponibles:
        raise Exception("No se encontraron grupos para el certificado proporcionado.")
    print("Grupos disponibles:")
    for i, grupo in enumerate(grupos_disponibles, start=1):
        print(f"{i}. {grupo}")
    seleccion = int(input("Seleccione el número del grupo deseado: ")) - 1
    if seleccion < 0 or seleccion >= len(grupos_disponibles):
        raise ValueError("Selección de grupo inválida.")
    return grupos_disponibles[seleccion]

def elegir_nominal(labrowe_datalogger_data, certificado_objetivo, grupo_objetivo):
    nominales_disponibles = []
    for certificado in labrowe_datalogger_data:
        if certificado['CertNo'] == certificado_objetivo:
            for datasheet in certificado['Datasheet']:
                if datasheet['Group'] == grupo_objetivo:
                    for measurement in datasheet['Measurements']:
                        nominal = measurement['Nominal']
                        if nominal not in nominales_disponibles:
                            nominales_disponibles.append(nominal)
    if not nominales_disponibles:
        raise Exception("No se encontraron nominales para el grupo proporcionado.")
    print("Valores nominales disponibles:")
    for i, nominal in enumerate(nominales_disponibles, start=1):
        print(f"{i}. {nominal} {datasheet['Measurements'][0]['Units']}")
    seleccion = int(input("Seleccione el número del valor nominal deseado: ")) - 1
    if seleccion < 0 or seleccion >= len(nominales_disponibles):
        raise ValueError("Selección de nominal inválida.")
    return nominales_disponibles[seleccion]

def elegir_unidad():
    unidades_disponibles = ['g', 'kg', 'lb', '°C', '%RH', '°F']
    print("Unidades disponibles:")
    for i, unidad in enumerate(unidades_disponibles, start=1):
        print(f"{i}. {unidad}")
    seleccion = int(input("Seleccione el número de la unidad deseada: ")) - 1
    if seleccion < 0 or seleccion >= len(unidades_disponibles):
        raise ValueError("Selección de unidad inválida.")
    return unidades_disponibles[seleccion]

def convertir_unidad(valor, unidad_origen, unidad_destino):
    conversiones = {
        'g': 1,
        'kg': 1e3,
        'lb': 453.59237,
        '°C': 1,
        '%RH': 1,
        '°F': 1
    }
    
    if unidad_origen == unidad_destino:
        return valor
    
    if unidad_origen in ['g', 'kg', 'lb'] and unidad_destino in ['g', 'kg', 'lb']:
        return valor * conversiones[unidad_origen] / conversiones[unidad_destino]
    elif unidad_origen == '°F' and unidad_destino == '°C':
        return (valor - 32) * 5/9
    elif unidad_origen == '°C' and unidad_destino == '°F':
        return valor * 9/5 + 32
    else:
        raise ValueError(f"Conversión no soportada: de {unidad_origen} a {unidad_destino}")

def convertir_unidad_a_gramos(valor, unidad):
    conversiones = {
        'µg': 1e-6,
        'μg': 1e-6,
        'mg': 1e-3,
        'g': 1,
        'kg': 1e3
    }
    if '/' in unidad:
        unidad_base, unidad_referencia = unidad.split('/')
        valor_base = valor * conversiones.get(unidad_base.strip(), 0)
        numero_referencia = float(re.findall(r'\d+', unidad_referencia)[0]) if re.findall(r'\d+', unidad_referencia) else 1.0
        if 'kg' in unidad_referencia:
            return valor_base / (numero_referencia * conversiones['kg'])
        elif 'g' in unidad_referencia:
            return valor_base / (numero_referencia * conversiones['g'])
    else:
        return valor * conversiones.get(unidad, 0)


def identificar_rango_en_certificado(certificado_data, valor, unidad):
    for registro in certificado_data:
        if registro['Equipment'] == unidad:
            minimo = registro['Range']['Min']
            maximo = registro['Range']['Max']
            if minimo <= valor <= maximo:
                return registro['ID'], registro['CMC']
    raise ValueError(f"No se encontró un rango adecuado para {valor} {unidad}")

def extraer_cmc_fijo_proporcional(cmc):
    partes = cmc.split('+')
    if len(partes) == 1:
        return float(partes[0].split()[0]), 0
    cmc_fijo = float(partes[0].strip().split()[0])
    cmc_proporcional = float(partes[1].strip().split()[0])
    return cmc_fijo, cmc_proporcional

def calcular_incertidumbre(valor_nominal, cmc_fijo, cmc_proporcional, meas_uncert, unidad):
    # Convertir todos los valores a gramos
    valor_nominal_g = convertir_unidad_a_gramos(valor_nominal, unidad)
    cmc_fijo_g = convertir_unidad_a_gramos(cmc_fijo, 'μg')
    cmc_proporcional_g = convertir_unidad_a_gramos(cmc_proporcional, 'μg/g')
    meas_uncert_g = convertir_unidad_a_gramos(meas_uncert, unidad)

    # Calcular CMC total
    cmc_total = cmc_fijo_g + (cmc_proporcional_g * valor_nominal_g)

    # Calcular incertidumbre combinada
    incertidumbre_combinada = math.sqrt(cmc_total**2 + meas_uncert_g**2)

    # Convertir el resultado a diferentes unidades
    return (
        f"{incertidumbre_combinada:.4f} g",
        f"{incertidumbre_combinada * 1000:.4f} mg",
        f"{incertidumbre_combinada * 1e6:.4f} μg"
    )

def procesar_certificado(labrowe_datalogger_data, certificado_balance_data, thermodynamics_data, certificado_objetivo, grupo_objetivo, nominal_objetivo, unidad_objetivo):
    meas_uncert = buscar_en_labrowe_datalogger(labrowe_datalogger_data, certificado_objetivo, grupo_objetivo, nominal_objetivo, unidad_objetivo)
    
    if unidad_objetivo in ['g', 'kg', 'lb']:
        valor_en_gramos = convertir_unidad(float(nominal_objetivo), unidad_objetivo, 'g')
        id_cmc, cmc_string = identificar_rango_en_certificado(certificado_balance_data, valor_en_gramos, 'Balances & Scales')
    elif unidad_objetivo in ['°C', '°F', '%RH']:
        valor_convertido = convertir_unidad(float(nominal_objetivo), unidad_objetivo, '°C') if unidad_objetivo == '°F' else float(nominal_objetivo)
        id_cmc, cmc_string = identificar_rango_en_certificado(thermodynamics_data, valor_convertido, unidad_objetivo)
    else:
        raise ValueError(f"Unidad no soportada: {unidad_objetivo}")
    
    cmc_fijo, cmc_proporcional = extraer_cmc_fijo_proporcional(cmc_string)
    total_uncertainty = calcular_incertidumbre(float(nominal_objetivo), cmc_fijo, cmc_proporcional, meas_uncert, unidad_objetivo)
    
    return {
        "meas_uncert": meas_uncert,
        "cmc_used": cmc_string,
        "total_uncertainty": total_uncertainty
    }

def obtener_info_certificado(labrowe_datalogger_data, certificado_objetivo):
    for certificado in labrowe_datalogger_data:
        if certificado['CertNo'] == certificado_objetivo:
            return {
                'CertNo': certificado['CertNo'],
                'EquipmentType': certificado['EquipmentType'],
                'AssetDescription': certificado['AssetDescription'],
                'Manufacturer': certificado['Manufacturer'],
                'Model': certificado['Model'],
                'OperatingRange': certificado['OperatingRange'],
                'EnvironmentalConditions': {
                    'Temperature': certificado['EnvironmentalTemperature'],
                    'RelativeHumidity': certificado['EnvironmentalRelativeHumidity'],
                    'BarometricPressure': certificado['EnvironmentalBarometricPressure']
                },
                'Standards': certificado['Standards'],
                'CustomerRequirements': certificado['CustomerRequirements'],
                'Remarks': certificado['Remarks']
            }
    raise ValueError(f"No se encontró el certificado {certificado_objetivo}")

"""
Interacción con el menú:
- Elija una opción del menú principal tecleando 1, 2 o 3 y presione Enter.

Opción 1: Búsqueda por certificado
  1.1 Ingrese el número de certificado específico.
  1.2 Se mostrará la información detallada del certificado.
  1.3 Seleccione un grupo de medición de la lista proporcionada.
  1.4 Elija un valor nominal de los disponibles para el grupo seleccionado.
  1.5 Seleccione la unidad de medida (g, kg, lb, °C, %RH).
  1.6 El sistema buscará y mostrará la incertidumbre de medición correspondiente, junto con el CMC utilizado y la incertidumbre total calculada.

Opción 2: Búsqueda por modelo
  2.1 Escriba las primeras letras del modelo y seleccione de la lista filtrada.
  2.2 Se mostrarán los certificados asociados al modelo seleccionado.
  2.3 Elija un número de certificado de la lista para realizar una búsqueda detallada, repitiendo los pasos 1.2 a 1.6 para este certificado específico.
Opción 3: Salir del programa
- Utilice esta opción para finalizar la ejecución del programa en cualquier momento.
"""