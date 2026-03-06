# Makima Electron Launcher

## Setup (one time)

1. Install Node.js from https://nodejs.org
2. Open a terminal in this folder
3. Run:
```
npm install
```

## Run the launcher

```
npm start
```

## Build a .exe (portable, no install needed)

```
npm run build
```
The .exe will appear in the `dist/` folder.

## How it connects to your Python backend

In `main.js`, edit this line to point to your Makima main file:
```js
const scriptPath = path.join(__dirname, '..', 'makima_fixed', 'main.py')
```

The launcher talks to Python via stdin/stdout.
In your Python code, read input with:
```python
import sys
for line in sys.stdin:
    user_input = line.strip()
    response = makima.chat(user_input)
    print(response, flush=True)
```

## Window controls

The custom close/minimize/maximize buttons in the HTML
are already wired up via `window.makima.close()` etc.
Just make sure your HTML buttons call these:
```js
// Close button
window.makima.close()

// Minimize
window.makima.minimize()
```
