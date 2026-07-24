# Infinity Inmobiliaria — Control de Operaciones

Software interno para registrar operaciones (compraventa y alquiler), calcular
automáticamente las comisiones y su reparto entre el agente y la inmobiliaria,
ver la agenda mensual, obtener el registro/balance del mes y exportar a **PDF** y **Excel**.

Hecho con **Python + Flask + SQLite** (base de datos local, sin servidor externo).

---

## Requisitos

- **Python 3.10 o superior** instalado en Windows.
  Descargalo de https://www.python.org/downloads/ y, durante la instalación,
  marcá la casilla **"Add Python to PATH"**.

## Instalación (primera vez, en cualquier PC)

1. Copiá toda la carpeta del proyecto a la PC.
2. Hacé doble clic en **`setup.bat`** y esperá a que termine.
   (Crea el entorno e instala las dependencias automáticamente.)

## Uso diario

- Hacé doble clic en **`iniciar.vbs`**.
- Arranca **sin ninguna ventana de terminal** y se abre solo en el navegador
  en `http://127.0.0.1:5000`.
- Aparece un **ícono de Infinity en la bandeja del sistema** (al lado del reloj):
  - **Clic** sobre el ícono → abre la app en el navegador.
  - **Clic derecho → Salir** → cierra la aplicación.

> **Consejo:** clic derecho sobre `iniciar.vbs` → *Enviar a → Escritorio (crear acceso directo)*
> para tener el ícono a mano. Podés cambiarle el ícono al de `app/static/img/favicon.ico`.

> **¿Algo falla al abrir?** Usá **`iniciar.bat`** (modo consola): muestra una ventana
> con los mensajes y errores. También quedan registrados en **`infinity.log`**.

> Los datos se guardan en el archivo **`instance/infinity.db`**.
> Para hacer una **copia de seguridad**, copiá ese archivo.
> Para **mudar los datos** a otra PC, copiá ese mismo archivo a la carpeta `instance/` de la otra instalación.

---

## Funcionalidades

- **Panel**: resumen del mes en curso por moneda, ranking de agentes y últimas operaciones.
- **Nueva operación**: carga de compraventa o alquiler con **cálculo en vivo** de comisiones.
- **Operaciones**: listado con filtros por tipo, agente, propiedad/texto y rango de fechas.
- **Agenda**: vista calendario mensual de las operaciones por día.
- **Registro mensual**: balance por moneda (comisión bruta, total inmobiliaria y reparto por agente)
  con exportación a **PDF** y **Excel**.
- **Agentes**: alta/baja/edición; el título de corredor sugiere retención del 20%.
- **Configuración**: comisiones por defecto (3% CV / 4,5% ALQ), opciones de retención y moneda de alquiler.

## Reglas de cálculo (núcleo)

Por cada punta representada por **Infinity**:

```
comisión bruta     = base × (comisión % / 100)     ó   monto fijo
monto inmobiliaria = comisión bruta × (retención % / 100)
monto agente       = comisión bruta − monto inmobiliaria
```

- **Compraventa**: siempre en US$, comisión por defecto **3%**.
- **Alquiler**: ARS por defecto (o US$), comisión por defecto **4,5%** del total del contrato,
  o un **monto fijo** ("un canon").
- Si el porcentaje difiere del valor por defecto, es **obligatorio cargar el motivo**.
- Retención de la inmobiliaria: **30% / 20% / 10%**.
- Solo las puntas de Infinity generan comisión; otra inmobiliaria o particular no.

## Verificación

```
venv\Scripts\python.exe tests_calculo.py   (criterios de cálculo)
venv\Scripts\python.exe tests_app.py       (prueba de humo de toda la app)
```

## Personalización rápida de la estética

Los colores y el estilo están centralizados en
`app/static/css/styles.css` (bloque `:root`). El logo está en
`app/static/img/`. Cambiando esos archivos se rediseña sin tocar la lógica.
