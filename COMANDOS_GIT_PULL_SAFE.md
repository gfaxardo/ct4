# COMANDOS GIT PULL SEGURO - PowerShell

## FASE 1: DIAGNÓSTICO (Ejecutar en orden)

```powershell
# 1a) Confirmar rama actual y tracking
cd C:\cursor\CT4
git branch --show-current
git branch -vv

# 1b) Verificar estado del working tree
git status

# 1c) Traer información del remoto SIN modificar tu código
git fetch origin

# 1d) Comparar tu rama local vs remota
git log HEAD..origin/master --oneline
git log origin/master..HEAD --oneline
```

---

## RUTA A: SAFE (Working tree limpio + sin conflictos)

```powershell
# Si git status muestra "working tree clean" Y no hay commits remotos nuevos:
git pull origin master

# O si prefieres ser más explícito:
git pull origin master --no-rebase
```

---

## RUTA B: Tengo cambios locales que QUIERO CONSERVAR (commit WIP)

```powershell
# 1) Ver qué archivos cambiaron
git status

# 2) Agregar todos los cambios
git add .

# 3) Commit WIP (Work In Progress)
git commit -m "WIP: cambios locales antes de pull"

# 4) Ahora hacer pull
git pull origin master

# 5) Si hay conflictos, resolverlos y luego:
git add .
git commit -m "Merge: resolver conflictos post-pull"
```

---

## RUTA C: Tengo cambios locales pero NO QUIERO COMMITEAR (stash)

```powershell
# 1) Guardar cambios temporalmente
git stash push -m "Cambios locales antes de pull"

# 2) Verificar que está limpio
git status

# 3) Hacer pull
git pull origin master

# 4) Recuperar tus cambios
git stash pop

# 5) Si hay conflictos al hacer pop, resolverlos manualmente
# Luego eliminar el stash: git stash drop
```

---

## FASE 2: VERIFICACIÓN POST-PULL

```powershell
# Ver últimos 5 commits
git log --oneline -5

# Ver hash del commit remoto
git ls-remote origin master

# Comparar tu HEAD con remoto
git log HEAD..origin/master --oneline
git log origin/master..HEAD --oneline

# Ver estado final
git status
```

---

## CASO ESPECIAL: Si el remoto usa 'main' en vez de 'master'

```powershell
# Verificar qué rama usa el remoto
git ls-remote --heads origin

# Si el remoto tiene 'main', cambiar tracking:
git branch --set-upstream-to=origin/main master
# O crear rama local main:
git checkout -b main origin/main

# Luego hacer pull a la rama correcta
git pull origin main
```

---

# CÓMO INTERPRETAR LAS SALIDAS

## 1a) `git branch --show-current` y `git branch -vv`

**Salida esperada:**
```
master
* master abc1234 [origin/master: ahead 13, behind 0] Último commit message
```

**Interpretación:**
- `master`: Tu rama actual
- `[origin/master: ahead 13, behind 0]`: 
  - `ahead 13`: Tienes 13 commits locales que NO están en el remoto
  - `behind 0`: El remoto NO tiene commits que tú no tengas
- Si dice `behind 5`: El remoto tiene 5 commits nuevos que necesitas bajar

---

## 1b) `git status`

**Salida SAFE (Ruta A):**
```
On branch master
Your branch is ahead of 'origin/master' by 13 commits.
nothing to commit, working tree clean
```
✅ **Significa:** Puedes hacer pull sin riesgo. No hay cambios sin commitear.

**Salida RUTA B (tienes cambios):**
```
On branch master
Your branch is ahead of 'origin/master' by 13 commits.
Changes not staged for commit:
  modified:   frontend/lib/types.ts
  modified:   backend/app/api/endpoints.py
```
⚠️ **Significa:** Tienes cambios locales. Usa Ruta B (commit WIP) o Ruta C (stash).

**Salida con archivos sin trackear:**
```
Untracked files:
  nuevo_archivo.py
```
⚠️ **Significa:** Archivos nuevos. `git add .` los incluirá en el commit.

---

## 1c) `git fetch origin`

**Salida esperada:**
```
From https://github.com/gfaxardo/ct4.git
   abc1234..def5678  master     -> origin/master
```
✅ **Significa:** Se trajeron cambios del remoto. Ahora `origin/master` está actualizado.

**Si no hay cambios:**
```
From https://github.com/gfaxardo/ct4.git
```
(Sin líneas adicionales) = No hay commits nuevos en el remoto.

---

## 1d) `git log HEAD..origin/master --oneline`

**Salida con commits remotos nuevos:**
```
def5678 Fix: endpoint Yango Cabinet
ghi9012 Add: health checks view
jkl3456 Update: refresh scripts
```
⚠️ **Significa:** El remoto tiene estos commits que tú NO tienes. Necesitas hacer pull.

**Salida vacía:**
```
(no output)
```
✅ **Significa:** No hay commits remotos nuevos. Estás al día.

**`git log origin/master..HEAD --oneline`** (tus commits locales):
```
abc1234 WIP: cambios locales
mno7890 Add: UI improvements
pqr1234 Fix: reconciliation logic
```
✅ **Significa:** Estos son tus commits locales que aún no has pusheado.

---

## RUTA A: `git pull origin master`

**Salida exitosa (sin conflictos):**
```
Updating abc1234..def5678
Fast-forward
 frontend/lib/types.ts | 5 +++++
 backend/app/api/endpoints.py | 10 ++++++++++
 2 files changed, 15 insertions(+)
```
✅ **Significa:** Pull exitoso. Tus cambios locales se mantienen, se agregaron los remotos.

**Salida con merge commit:**
```
Merge made by the 'recursive' strategy.
 frontend/lib/types.ts | 5 +++++
 backend/app/api/endpoints.py | 10 ++++++++++
```
✅ **Significa:** Se creó un merge commit combinando tus cambios con los remotos. Normal si ambos tenían commits.

**Salida con CONFLICTOS:**
```
Auto-merging frontend/lib/types.ts
CONFLICT (content): Merge conflict in frontend/lib/types.ts
Automatic merge failed; fix conflicts and then commit the result.
```
⚠️ **Significa:** Hay conflictos. Debes:
1. Abrir `frontend/lib/types.ts`
2. Buscar marcadores `<<<<<<<`, `=======`, `>>>>>>>`
3. Resolver manualmente
4. `git add frontend/lib/types.ts`
5. `git commit -m "Resolve merge conflicts"`

---

## RUTA C: `git stash pop`

**Salida exitosa:**
```
On branch master
Changes not staged for commit:
  modified:   frontend/lib/types.ts
Dropped refs/stash@{0} (abc1234...)
```
✅ **Significa:** Tus cambios se recuperaron correctamente.

**Salida con conflictos en stash:**
```
Auto-merging frontend/lib/types.ts
CONFLICT (content): Merge conflict in frontend/lib/types.ts
```
⚠️ **Significa:** Los cambios del stash chocan con los nuevos del pull. Resuelve igual que arriba.

---

## FASE 2: Verificación Post-Pull

**`git log --oneline -5`:**
```
def5678 (HEAD -> master, origin/master) Fix: endpoint Yango Cabinet
ghi9012 Add: health checks view
jkl3456 Update: refresh scripts
abc1234 WIP: cambios locales
mno7890 Add: UI improvements
```
✅ **Interpretación:** 
- `(HEAD -> master, origin/master)`: Tu HEAD y el remoto están en el mismo commit
- Si `origin/master` NO aparece en el último commit: estás detrás o adelante

**`git ls-remote origin master`:**
```
def5678abc1234...    refs/heads/master
```
✅ **Interpretación:** El hash `def5678...` es el commit más reciente en el remoto.

**`git log HEAD..origin/master --oneline`:**
```
(no output)
```
✅ **Significa:** No hay commits remotos que no tengas. Estás sincronizado.

**`git log origin/master..HEAD --oneline`:**
```
(no output o lista de tus commits locales)
```
✅ **Si vacío:** Estás 100% sincronizado con el remoto.
✅ **Si hay commits:** Son tus cambios locales que aún no has pusheado.

---

## DECISIÓN FINAL: ¿Qué ruta elegir?

### Elige RUTA A si:
- ✅ `git status` dice "working tree clean"
- ✅ `git log HEAD..origin/master` muestra commits remotos nuevos
- ✅ Quieres bajar cambios del remoto sin complicaciones

### Elige RUTA B si:
- ⚠️ `git status` muestra archivos modificados
- ✅ Quieres guardar tus cambios en un commit permanente
- ✅ No te importa tener un commit WIP en el historial

### Elige RUTA C si:
- ⚠️ `git status` muestra archivos modificados
- ✅ NO quieres commitear todavía (cambios experimentales)
- ✅ Quieres probar el pull primero y luego decidir qué hacer con tus cambios

---

## ⚠️ SITUACIÓN ACTUAL DETECTADA

Según el diagnóstico:
- **Rama:** `master`
- **Estado:** Working tree limpio ✅
- **Posición:** Estás 13 commits ADELANTE de `origin/master`

**Recomendación:**
1. Primero ejecuta `git fetch origin` para ver si hay commits remotos nuevos
2. Si `git log HEAD..origin/master` muestra commits: hacer pull (Ruta A)
3. Si está vacío: el remoto está detrás de ti. Considera hacer `git push` en vez de pull
4. Si después del fetch aparecen commits remotos Y locales divergentes: puede haber conflictos al hacer pull

