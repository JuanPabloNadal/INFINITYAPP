# Desplegar Infinity en internet (Vercel + Neon)

Guía paso a paso para poner la app online, accesible desde cualquier PC con una
contraseña. Todo lo que se usa acá tiene **plan gratuito**.

Resultado final: una dirección tipo `https://infinity-inmobiliaria.vercel.app`
que pide una contraseña (`infinity26`) y adentro tiene la app con todos los
datos actuales (66 operaciones, 14 agentes).

> **Importante — privacidad:** el repositorio de GitHub tiene que ser **privado**.
> Los datos (operaciones, comisiones) NO se suben a GitHub: viven en Neon. El
> `.gitignore` ya está configurado para no subir la base de datos por accidente.

---

## Antes de empezar (crear 3 cuentas gratis)

1. **GitHub** → https://github.com/signup
2. **Neon** (base de datos) → https://neon.tech  (entrá con la cuenta de GitHub)
3. **Vercel** (hosting) → https://vercel.com/signup  (entrá con la cuenta de GitHub)

También necesitás **Git** instalado en la PC: https://git-scm.com/download/win

---

## Paso 1 — Subir el código a GitHub (repo PRIVADO)

1. En GitHub, arriba a la derecha: **+ → New repository**.
   - Name: `infinity-inmobiliaria`
   - Elegí **Private** (¡importante!).
   - No marques nada más. **Create repository**.
2. GitHub te muestra una dirección tipo
   `https://github.com/TU-USUARIO/infinity-inmobiliaria.git`. Copiala.
3. Abrí una terminal (PowerShell) dentro de `D:\INFINITY APP` y ejecutá, una por una:

   ```powershell
   git init
   git add .
   git commit -m "Infinity Inmobiliaria - primera version"
   git branch -M main
   git remote add origin https://github.com/TU-USUARIO/infinity-inmobiliaria.git
   git push -u origin main
   ```

   (La primera vez te va a pedir que inicies sesión en GitHub; seguí lo que aparezca.)

---

## Paso 2 — Crear la base de datos en Neon

1. En Neon: **Create project**.
   - Name: `infinity`
   - Region: la más cercana (por ejemplo *AWS US East* / *São Paulo* si aparece).
   - **Create project**.
2. Al crearlo, Neon muestra una **Connection string** que empieza con
   `postgresql://...`. Copiala completa (tiene usuario, clave y `?sslmode=require`).
   Guardala a mano, la vas a usar dos veces.

---

## Paso 3 — Cargar los datos actuales en Neon

Esto se hace **una sola vez**, desde la PC donde está la base con los datos
(`D:\INFINITY APP\instance\infinity.db`).

En PowerShell, dentro de `D:\INFINITY APP`:

```powershell
$env:DATABASE_URL = "PEGÁ_ACÁ_LA_CONNECTION_STRING_DE_NEON"
venv\Scripts\python.exe migrar_a_postgres.py
```

Tenés que ver al final `MIGRACION COMPLETA.` con las cantidades
(agentes 14, operaciones 66, etc.). Si algo falla, avisá y lo revisamos.

---

## Paso 4 — Desplegar en Vercel

1. En Vercel: **Add New… → Project**.
2. **Import** el repositorio `infinity-inmobiliaria` de GitHub.
3. Vercel detecta que es Python. Antes de dar *Deploy*, abrí
   **Environment Variables** y agregá estas tres:

   | Name                  | Value                                                        |
   |-----------------------|--------------------------------------------------------------|
   | `DATABASE_URL`        | la connection string de Neon (la misma del Paso 3)           |
   | `INFINITY_SECRET_KEY` | `3965c9aeb0e6ecf7ca4bb4fe4d5b72337529cfb6b8de24e9b0c54ec9d41db036` |
   | `APP_PASSWORD`        | `infinity26`                                                 |

4. **Deploy**. Esperá 1-2 minutos.
5. Vercel te da la dirección final (`https://....vercel.app`). Abrila: te pide la
   contraseña `infinity26` y entrás a la app con todos los datos.

Listo. Podés entrar desde cualquier PC con esa dirección y la contraseña.

---

## Cómo cambiar la contraseña más adelante

No hay que tocar código. En Vercel: **Settings → Environment Variables →**
editás `APP_PASSWORD` con la nueva clave y hacés **Redeploy**. Recomendación:
usá algo más largo que `infinity26` (ej. una frase con números).

---

## Cómo subir cambios futuros de la app

Cada vez que se modifique el código, desde `D:\INFINITY APP`:

```powershell
git add .
git commit -m "descripción del cambio"
git push
```

Vercel redepliega solo en cada `push`. (Los cambios de código no tocan los datos
de Neon.)

---

## Copias de seguridad de los datos

Los datos están en Neon. Neon tiene *branching* y retención automática, pero para
un backup manual podés, cuando quieras, volver a exportar desde la app (botones
**Excel/PDF** en Registro / Reportes) y guardar esos archivos.

---

## Notas y limitaciones

- **Arranque en frío:** con el plan gratis, si nadie usa la app por un rato, la
  primera carga puede tardar unos segundos más mientras "despierta". Después va normal.
- **Dos instalaciones separadas:** la versión de la nube y el instalador local de
  escritorio son independientes. Podés usar cualquiera de las dos; los datos de la
  nube están en Neon y los del escritorio en el archivo local.
- **Seguridad:** el acceso es por una única contraseña compartida sobre HTTPS.
  Alcanza para uso interno, pero cuantas más personas la conozcan, más conviene
  cambiarla cada tanto.
