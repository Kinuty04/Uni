# Uni
Uni projects with Raspberry Pi Model 3B and Comblock-2001


# Digital Modulation Simulation & Raspberry Pi DAC Signal Generator

This repository contains two Python scripts designed for digital communications analysis and hardware signal generation. Together, they provide a complete workflow—from simulating baseband digital modulation schemes and pulse shaping in software to transmitting real-time In-phase ($I$) and Quadrature ($Q$) waveforms from a **Raspberry Pi** to a **Comblock-2001** Digital-to-Analog Converter (DAC).

---

## 📂 Repository Overview

1. **`raspberry_simulation.py`**: An interactive visualization and simulation tool built with `NumPy` and `Matplotlib`. It models various digital modulation formats, applies Root-Raised Cosine (RRC) pulse shaping, introduces Additive White Gaussian Noise (AWGN), and renders interactive eye diagrams, time-domain waveforms, and constellation plots.
2. **`raspberry.py`**: A hardware driver script for the **Raspberry Pi (e.g., Model 3B)** that uses `pigpio` and Direct Memory Access (DMA) to output 10-bit parallel $I$ and $Q$ data streams along with a clock signal to a **Comblock-2001** DAC module for visualization on an oscilloscope or RF transmission.

---

## 🛠️ Prerequisites & Installation

### Software Dependencies
Both scripts require Python 3 and `NumPy`. Depending on whether you are running the simulation or the hardware output, install the following packages:

* **For Simulation (`raspberry_simulation.py`):**
  ```bash
  pip install numpy matplotlib
  ```
* **For Raspberry Pi Hardware Output (`raspberry.py`):**
  ```bash
  pip install numpy
  sudo apt update
  sudo apt install python3-pigpio pigpio
  sudo systemctl enable pigpiod
  sudo systemctl start pigpiod
  ```

### Required Assets (`raspberry_simulation.py`)
To run the interactive plot buttons without errors, ensure the following image assets exist in the working directory (or update their paths in the script):
* `./red.jpg` (Button icon for toggling the Quadrature/$Q$ channel)
* `./blu.jpg` (Button icon for toggling the In-phase/$I$ channel)

---

## 📊 1. Software Simulation (`raspberry_simulation.py`)

`raspberry_simulation.py` simulates a baseband communication transmitter and channel.

### Key Features
* **Supported Modulations:** `bpsk`, `qpsk`, `8psk`, `2ask`, `4ask`, `8ask`, and `ook`.
* **Pulse Shaping:** Implements a normalized Root-Raised Cosine (RRC) filter with configurable roll-off factor ($\alpha$) and symbol span.
* **Channel Modeling:** Adds Additive White Gaussian Noise (AWGN) based on a configurable Signal-to-Noise Ratio (`SNR_db`).
* **Interactive GUI Dashboard:**
  * **Eye Diagram:** Displays overlapping symbol periods for $I$ (blue) and $Q$ (red) components to evaluate Inter-Symbol Interference (ISI) and timing jitter.
  * **Time-Domain Zoom & Slider:** Splits the shaped waveform into 5 selectable spans via interactive buttons or a vertical slider.
  * **Channel Isolation:** Custom `BLU` and `RED` buttons allow isolating the $I$ and $Q$ traces in both the time-domain view and the eye diagram.
  * **Constellation Plots:** Side-by-side ideal and noisy ($I/Q$) constellation diagrams overlaid with geometric reference boundaries (unit circle and bounding squares).
* **Bit Logging:** Exports the generated pseudorandom bit sequence to `./Values.txt` (100 bits per line).

### Configuration & Execution
Parameters are configured directly inside the `MAIN` section of `raspberry_simulation.py`:
```python
Fs = 1_000_000      # Sampling frequency (Hz)
Rs = 100_000        # Symbol rate (Baud)
alpha = 0.4         # RRC roll-off factor (0.0 to 1.0)
N_bits = 1000       # Number of bits to simulate
mod_type = '8psk'   # Options: bpsk, qpsk, 8psk, 2ask, 4ask, 8ask, ook
SNR_db = 20         # Channel SNR in dB
```

Run the simulation:
```bash
python3 raspberry_simulation.py
```

---

## 🔌 2. Hardware DAC Transmitter (`raspberry.py`)

`raspberry.py` synthesizes baseband digital waveforms and drives 21 GPIO pins on the Raspberry Pi using `pigpio` DMA waveforms, ensuring deterministic, jitter-free timing without CPU overhead.

### Key Features
* **Supported Waveforms & Modulations:**
  * **Test Signals:** `iq` (complex exponential/circle), `i-only` (cosine), `q-only` (sine), `ramp` (differential sawtooth).
  * **Digital Modulations:** `qpsk` (RRC-filtered), `4ask` (RRC-filtered), and `8fsk` (continuous-phase 8-tone FSK).
* **Comblock-2001 Encoding:** Automatically converts standard 10-bit unsigned integers ($0\text{--}1023$, mid-scale $512$) into the inverted binary format expected by the Comblock-2001 DAC (`1023 - x`).
* **DMA Pulse Generation:** Generates two DMA pulses per sample period:
  1. Sets the 20 parallel data pins ($I_0\text{--}I_9$, $Q_0\text{--}Q_9$) while holding `CLK` LOW for $(\text{period\_us} - 1)\,\mu\text{s}$.
  2. Drives `CLK` HIGH for $1\,\mu\text{s}$ to latch the data into the DAC.
* **Safe Shutdown:** Catches `SIGINT` (`Ctrl+C`), stops DMA transmission, resets data lines to mid-scale (`512`), and pulls the clock LOW.

### Hardware Wiring (Raspberry Pi to Comblock-2001 J3)

You can print the full pinout directly in your terminal using `python3 raspberry.py --wiring`.

| Signal | Bit | Raspberry Pi BCM GPIO | Raspberry Pi Physical Pin | Comblock-2001 J3 Pin |
| :--- | :---: | :---: | :---: | :---: |
| **CLK** | — | `GPIO 26` | Pin 37 | `A13` |
| **GND** | — | `GND` | Pins 6, 9, 14, 20, 25, 30, 34, 39 | `B5, B10, B15, B20` |
| **DATA_I_IN** | 0–9 | `GPIO 4` – `GPIO 13` | Pins 7, 29, 31, 26, 24, 21, 19, 23, 32, 33 | `A7, B6, A6, A5, B4, A4, B3, A3, B2, A2` |
| **DATA_Q_IN** | 0–9 | `GPIO 16` – `GPIO 25` | Pins 36, 11, 12, 35, 38, 40, 15, 16, 18, 22 | `B12, A12, B11, A11, A10, B9, A9, B8, A8, B7` |

### Command-Line Arguments

| Flag | Default | Description |
| :--- | :--- | :--- |
| `--mode` | `iq` | Signal mode: `iq`, `i-only`, `q-only`, `ramp`, `qpsk`, `4ask`, or `8fsk`. |
| `--freq` | `100000` | Tone frequency in Hz (for continuous modes) or symbol rate in Baud (for `qpsk`, `4ask`, `8fsk`). |
| `--period-us` | `2` | Sampling period in microseconds ($\ge 2\,\mu\text{s}$). Default $2\,\mu\text{s} = 500\text{ kS/s}$. |
| `--amp` | `0.5` | Output amplitude scaling factor in the range $(0, 1]$. |
| `--alpha` | `0.35` | Root-Raised Cosine roll-off factor (used in `qpsk` and `4ask`). |
| `--symbols` | `32` | Number of random symbols in the repeating sequence (seed `42`). |
| `--wiring` | `False` | Displays the GPIO-to-Comblock J3 wiring table and exits. |
| `--dry-run` | `False` | Computes samples, verifies bit-mask encoding, prints the first 40 hex values, and exits without touching GPIOs. |

### Usage Examples

1. **Print the wiring diagram:**
   ```bash
   python3 raspberry.py --wiring
   ```
2. **Test signal generation without hardware (`--dry-run`):**
   ```bash
   python3 raspberry.py --mode qpsk --freq 50000 --period-us 2 --dry-run
   ```
3. **Transmit a 50 kBaud QPSK signal at 500 kS/s ($\alpha = 0.35$):**
   ```bash
   python3 raspberry.py --mode qpsk --freq 50000 --period-us 2 --alpha 0.35 --amp 0.8
   ```
4. **Transmit an 8-FSK signal at 10 kBaud (requires $\ge 8$ samples per symbol):**
   ```bash
   python3 raspberry.py --mode 8fsk --freq 10000 --period-us 2 --symbols 64
