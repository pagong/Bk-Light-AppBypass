<div align="center">

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Windows](https://img.shields.io/badge/Windows-0078D6?logo=windows&logoColor=white)](https://www.microsoft.com/windows)
[![Linux](https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=black)](https://www.linux.org/)
[![macOS](https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=white)](https://www.apple.com/macos/)
[![BLE](https://img.shields.io/badge/BLE-4.0+-0082FC?logo=bluetooth&logoColor=white)](https://www.bluetooth.com/)
[![Bleak](https://img.shields.io/badge/Bleak-BLE%20client-3776AB)](https://github.com/hbldh/bleak)
[![Pillow](https://img.shields.io/badge/Pillow-Imaging-3776AB)](https://python-pillow.org/)
[![PyYAML](https://img.shields.io/badge/PyYAML-Config-CB0000)](https://pyyaml.org/)

</div>

# BLE LED Display Toolkit

Utilities for driving BK-Light RGB LED matrices over Bluetooth Low Energy (command sequence from device logs). **Supported panels:** 32×32 (ACT1026) and 64×16 (ACT1025). Set `panels.tile_width` and `panels.tile_height` in `config.yaml` to match your panel; the BLE handshake supports both variants automatically.

Everything is now configurable through `config.yaml`, so you can define presets, multi-panel layouts, and runtime modes without touching code.

## Requirements

- Python 3.13+
- `pip install bleak Pillow PyYAML`
- Bluetooth adapter with BLE support enabled
- Hardware capabilities:
  - BLE 4.0 or newer with GATT/ATT support
  - Central role / GATT client mode
  - LE 1M PHY
  - Long ATT write support (Prepare/Execute or Write-with-response handling for fragmented payloads)
  - MTU negotiation and L2CAP fragmentation

The tools assume the screen advertises as `LED_BLE_*` (BK-Light firmware). Update the MAC address in `config.yaml` (or via `BK_LIGHT_ADDRESS`) if your unit differs. For **64×16 (ACT1025)** panels use `tile_width: 64` and `tile_height: 16`; for **32×32 (ACT1026)** the default `tile_width: 32`, `tile_height: 32` is correct.

## Acknowledgment (Windows / Python 3.13)

If you see `ModuleNotFoundError: No module named 'bleak'` or `ModuleNotFoundError: No module named 'PIL'` after `pip install -r requirements.txt`, or a **LNK1104** / failed wheel build for `winrt-Windows.Devices.Bluetooth.GenericAttributeProfile`, you are likely using the **free-threaded** Python 3.13 build (`python3.13t`). Bleak’s Windows dependencies (winrt) do not ship pre-built wheels for that variant, so pip tries to compile them and the build often fails.

Use the **standard** Python 3.13 (not the “t” build) for this project. Example:

```powershell
py -3.13 -m pip install -r requirements.txt
py -3.13 .\scripts\production.py
```

If `py -3.13` is not available, install the non–free-threaded Python 3.13 from [python.org](https://www.python.org/downloads/) and use that interpreter for install and run.

## Project Structure

- `config.yaml` – device defaults, multi-panel layout, presets, runtime mode.
- `config.py` – loader/validators for the configuration tree.
- `panel_manager.py` – orchestrates single/multi-panel sessions and image slicing.
- `display_session.py` – BLE transport: handshake, ACK tracking, brightness/rotation, auto-reconnect.
- `production.py` – production entrypoint that reads `config.yaml` and runs the selected mode/preset.
- Toolkit scripts (still usable standalone):
  - `clock_display.py`
  - `display_text.py`
  - `send_image.py`
  - `increment_counter.py`
  - `identify_panels.py`
- Legacy smoke tests: `bootstrap_demo.py`, `red_corners.py`.

## Quick Start

1. Install dependencies:

   ```bash
   pip install bleak Pillow PyYAML
   ```

2. Edit `config.yaml`.

   - Single panel (32×32 default):

     ```yaml
     device:
       address: "F0:27:3C:1A:8B:C3"
     panels:
       list: ["F0:27:3C:1A:8B:C3"]
     display:
       antialias_text: true  # set to false for crisp bitmap text
     ```

   - Single 64×16 panel (ACT1025):

     ```yaml
     panels:
       tile_width: 64
       tile_height: 16
       list: ["F0:27:3C:1A:8B:C3"]
     ```

   - Fonts:

     Place `.ttf` / `.otf` files under `assets/fonts/` and reference them by name (extension optional):

     ```yaml
     presets:
       clock:
         default:
           font: "Aldo PC"     # resolves to assets/fonts/Aldo PC.ttf
           size: 22
     ```

   - Multi-panel:

     ```yaml
     panels:
       tile_width: 32
       tile_height: 32
       layout:
         columns: 2
         rows: 1
       list:
         - name: left
           address: "F0:27:3C:1A:8B:C3"
           grid_x: 0
           grid_y: 0
         - name: right
           address: "F0:27:3C:1A:8B:C4"
           grid_x: 1
           grid_y: 0
     ```

     For 64×16 panels use `tile_width: 64`, `tile_height: 16`. A bare MAC string is accepted; defaults are inferred.

3. Pick the runtime mode and preset:

   ```yaml
   runtime:
     mode: clock
     preset: default
     options:
       timezone: "Europe/Paris"
   ```

   Other examples:

   ```yaml
   runtime:
     mode: text
     preset: marquee_left
     options:
       text: "WELCOME"
       color: "#00FFAA"
       background: "#000000"

   runtime:
     mode: image
     preset: signage
     options:
       image: "assets/promo.png"

   runtime:
     mode: counter
     preset: default
     options:
       start: 100
       count: 50
       delay: 0.5
   ```

4. Launch the production entrypoint:

   ```bash
   python scripts/production.py
   ```

   Override anything ad hoc:

   ```bash
   python scripts/production.py --mode text --text "HELLO" --option color=#00FFAA
   ```

5. Need to identify MAC ↔ panel placement or force a clean BLE reset? Run:

   ```bash
   python scripts/identify_panels.py
   ```

   (Each panel displays its index and then disconnects cleanly.)

## Toolkit Scripts

- `scripts/clock_display.py` – async HH:MM clock (supports 12/24h, dot flashing, themes). Exit with `Ctrl+C` so the BLE session closes cleanly and you can relaunch immediately.
- `scripts/display_text.py` – renders text using presets (colour/background/font/spacing) or marquee scrolls.

  Example scroll preset in `config.yaml`:

  ```yaml
  text:
    marquee_left:
      mode: scroll
      direction: left
      speed: 30.0
      step: 3          # pixels moved per frame
      gap: 32
      size: 18
      spacing: 2
      offset_y: 0
      interval: 0.04
  ```

  Launch:

  ```bash
  python scripts/display_text.py "HELLO" --preset marquee_left
  ```

- `scripts/send_image.py` – uploads any image with fit/cover/scale + rotate/mirror/invert.
- `scripts/increment_counter.py` – numeric animation for diagnostics.
- `scripts/identify_panels.py` – flashes digits on each configured panel.
- `scripts/list_fonts.py`

  Prints the fonts resolved from `assets/fonts/`. Bundled names and defaults:
  - `Aldo PC`
  - `Dolce Vita Light`
  - `Kenyan Coffee Rg`
  - `Kimberley Bl`

  ```bash
  python scripts/list_fonts.py [--config config.yaml]
  ```

Each script honours `--config`, `--address`, and preset overrides so you can reuse the same YAML in development or production.

## Building New Effects

Use Pillow to draw onto a canvas sized to `columns × rows` tiles, then:

```python
async with PanelManager(load_config()) as manager:
    await manager.send_image(image)
```

`PanelManager` slices the image per tile and `BleDisplaySession` handles BLE writes/ACKs for each panel automatically. Sessions will auto-reconnect if a panel restarts (tunable via `reconnect_delay` / `max_retries` / `scan_timeout`).

## Attribution & License

- Created by Puparia — GitHub: [Pupariaa](<https://github.com/Pupariaa>).
- Code is open-source and contributions are welcome; open a pull request with improvements or new effects.
- If you reuse this toolkit (or derivatives) in your own projects, credit “Puparia / <https://github.com/Pupariaa>” and link back to the original repository.
- Licensed under the [MIT License](./LICENSE).
