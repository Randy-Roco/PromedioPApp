# 📍 PromedioPApp

Aplicación para el **procesamiento y promediado automático de Puntos de Apoyo (PA)** obtenidos en terreno, diseñada para flujos de trabajo en **Geomensura, Topografía y Fotogrametría**.

---

## 🚀 ¿Qué hace esta app?

PromedioPApp permite:

- 📂 Cargar uno o varios archivos `.txt` de levantamientos en terreno
- 🔍 Identificar automáticamente puntos de apoyo (PA)
- 🧠 Normalizar descriptores (ej: `PA-01`, `PA01`, `PA001`)
- 🔗 Unificar puntos mediante **aliases personalizados**
- 📊 Calcular promedios de coordenadas (X, Y, Z)
- ✏️ Revisar y editar resultados antes de exportar
- 📤 Exportar resultados en múltiples formatos compatibles con software topográfico

---

## 📥 Formato de entrada

Archivos `.txt` con estructura tipo:

ID,Y,X,Z,DESCRIPTOR

Ejemplo:

P1,7300000.123,500000.456,123.789,PA01

---

## 📤 Formatos de salida

🟢 Civil 3D  
- Codificación: UTF-8  
- Sin cabecera  
- Formato:  
Y,X,Z,DESCRIPTOR  

🔵 ERDAS  
- Con cabecera  
- Formato:  
P,Y,X,Z,DESCRIPTOR  

---

## 🧩 Funcionalidades clave

🔄 Normalización automática  
Convierte automáticamente:  
PA-01, PA 01, PA001 → PA01  

🔗 Sistema de aliases  
Permite agrupar manualmente puntos mal digitados  

Ejemplo (`aliases_pa_ejemplo.json`):

{
  "PA001": "PA01",
  "PA1": "PA01"
}

📊 Promedio de coordenadas  

X_prom = promedio(X)  
Y_prom = promedio(Y)  
Z_prom = promedio(Z)  

---

## 🖥️ Uso de la aplicación

Ejecutar:

pip install -r requirements.txt  
python app_desktop.py  

O usar:

START_APP.bat  

---

## 🧪 Flujo de trabajo

1. Cargar archivos `.txt`
2. Revisar agrupación automática
3. Aplicar aliases si es necesario
4. Visualizar resultados
5. Exportar a Excel o TXT (Civil 3D / ERDAS)

---

## 📁 Estructura del proyecto

PromedioPApp/  
├── app_desktop.py  
├── promediopapp/core.py  
├── api/index.py  
├── requirements.txt  
├── vercel.json  
├── README.md  

---

## 🌐 Futuro (Roadmap)

- Versión web en Vercel  
- Exportación a Leica, Trimble, Topcon  
- Detección de outliers  
- Visualización espacial  
- Integración con ArcGIS / QGIS  

---

## 👷 Autor

Randy Roco Mellado  
Ingeniero en Geomensura  

---

## ⚡ Enfoque

Reducir errores humanos, estandarizar datos y acelerar el procesamiento de puntos de apoyo.

---

## 🧠 Licencia

Uso libre para fines académicos y profesionales.
