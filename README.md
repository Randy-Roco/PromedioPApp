# PromedioPApp

App para consolidar y promediar **Puntos de Apoyo (PA)** obtenidos en terreno, agrupando por descriptor y permitiendo corregir variantes como `PA01`, `PA-01`, `PA001` o aliases manuales como `PA001 -> PA01`.

## Qué resuelve
- carga uno o varios `.txt`
- detecta registros de PA
- normaliza descriptores automáticamente
- permite aliases manuales por proyecto u operador
- promedia coordenadas `X,Y,Z` por descriptor final
- exporta a **Excel** y a **TXT** según perfil de software
- deja el núcleo listo para usar luego en una web o API

## Formatos de entrada soportados
### 1) Formato tipo Civil 3D / terreno
```txt
ID,Y,X,Z,DESC
```

### 2) Formato sin ID
```txt
Y,X,Z,DESC
```

## Formatos de salida implementados
### Civil 3D
- codificación UTF-8
- sin cabecera
- orden: `Y,X,Z,DESC`

### ERDAS
- con cabecera
- orden: `P,Y,X,Z,DESC`

## Estructura del proyecto
```txt
PromedioPApp/
├─ api/
│  └─ index.py
├─ promediopapp/
│  ├─ __init__.py
│  └─ core.py
├─ app_desktop.py
├─ requirements.txt
├─ vercel.json
├─ .gitignore
└─ README.md
```

## Ejecución local
```bash
pip install -r requirements.txt
python app_desktop.py
```

## Uso de la app desktop
1. Cargar archivos `.txt`
2. Agregar aliases si hace falta, por ejemplo `PA001 -> PA01`
3. Procesar
4. Revisar la tabla **Promedios editables**
5. Elegir formato de salida
6. Exportar a Excel o TXT

## API preparada para Vercel
Ya viene una API mínima en `api/index.py` para más adelante conectar una web. Endpoints base:
- `GET /`
- `POST /procesar`

## Cómo subir a GitHub desde tu PC
Tu carpeta local será:
```txt
C:\Users\Randy\Desktop\PromedioPA
```

Copia aquí todos los archivos del repo y luego ejecuta en PowerShell:

```powershell
cd C:\Users\Randy\Desktop\PromedioPA
git init
git branch -M main
git remote add origin https://github.com/Randy-Roco/PromedioPApp.git
git add .
git commit -m "Primer commit PromedioPApp"
git push -u origin main
```

Si el repositorio ya existe con contenido remoto:
```powershell
cd C:\Users\Randy\Desktop\PromedioPA
git init
git branch -M main
git remote add origin https://github.com/Randy-Roco/PromedioPApp.git
git pull origin main --allow-unrelated-histories
git add .
git commit -m "Actualiza PromedioPApp con exportación TXT y API base"
git push -u origin main
```

## Cómo dejarlo listo para Vercel
Cuando el repo ya esté en GitHub:
1. Entrar a Vercel
2. Import Project desde GitHub
3. Elegir `PromedioPApp`
4. Framework: **Other**
5. Deploy

Con eso quedará publicada la API Python definida en `api/index.py`.

## Próximos pasos recomendados
- perfiles extra de exportación para Leica / Trimble / Topcon / Carlson / ArcGIS
- tolerancia y outliers por descriptor
- validación de duplicados sospechosos
- interfaz web con drag & drop
- histórico de aliases por faena
- empaquetado `.exe`
