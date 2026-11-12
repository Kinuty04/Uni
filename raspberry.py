#!/usr/bin/env python3


# 1)

import argparse
import math
import sys
import time
import signal
import random
import numpy as np



'''Program interruption with SIGINT signal (CTRL + C)'''

def handler(signum, frame):
    signame = signal.Signals(signum).name
    print(f'\nSignal handler called with signal {signame} number ({signum})')
    sys.exit(0)

signal.signal(signal.SIGINT, handler)



#########################
# PHYSICAL CONSTRUCTION #
#########################


# DAC and Raspberry PI pinout diagram
# -----------------------------------

# DAC physical pins via in phase
I_PINS_BY_BIT = {
    0: 4, 
    1: 5, 
    2: 6, 
    3: 7, 
    4: 8, 
    5: 9, 
    6: 10, 
    7: 11, 
    8: 12, 
    9: 13
}


# DAC physical pins via quadrature
Q_PINS_BY_BIT = {
    0: 16, 
    1: 17, 
    2: 18, 
    3: 19, 
    4: 20, 
    5: 21, 
    6: 22, 
    7: 23, 
    8: 24, 
    9: 25
}

CLK_PIN = 26


# Correspondence between the logical and physical pins of the Comblock-2001
J3_PIN = {
    "I0": "A7", 
    "I1": "B6", 
    "I2": "A6", 
    "I3": "A5", 
    "I4": "B4",
    "I5": "A4", 
    "I6": "B3", 
    "I7": "A3", 
    "I8": "B2", 
    "I9": "A2",
    "Q0": "B12", 
    "Q1": "A12", 
    "Q2": "B11", 
    "Q3": "A11", 
    "Q4": "A10",
    "Q5": "B9", 
    "Q6": "A9", 
    "Q7": "B8", 
    "Q8": "A8", 
    "Q9": "B7",
    "CLK": "A13",
}

GND_J3 = "B5, B10, B15, B20"



# Correspondence between the physical pins and those of the Raspberry Pi GPIO
BCM_TO_PHYS = {
    4: 7, 
    5: 29, 
    6: 31, 
    7: 26, 
    8: 24, 
    9: 21, 
    10: 19, 
    11: 23, 
    12: 32, 
    13: 33,
    16: 36, 
    17: 11, 
    18: 12, 
    19: 35, 
    20: 38, 
    21: 40, 
    22: 15, 
    23: 16, 
    24: 18,
    25: 22, 
    26: 37,
}


CLK_MASK = 1 << CLK_PIN
DATA_MASK = sum(1 << g for g in list(I_PINS_BY_BIT.values()) + list(Q_PINS_BY_BIT.values()))
ALL_PINS = sorted(list(I_PINS_BY_BIT.values()) + list(Q_PINS_BY_BIT.values()) + [CLK_PIN])


FULL_SCALE = 1023
MID_CODE = 512





#--//--//----//--//----//--//----//--//----//--//----//--//----//--//----//--//--



# Root-Raised Cosine Function
#----------------------------

def rrcosfilter(alpha, span, sps):
    t = np.arange(-span * sps / 2, span * sps / 2 + 1) / sps
    h = np.zeros(len(t))
    
    for i in range(len(t)):
        ti = t[i]
        if ti == 0.0:
            h[i] = 1.0 - alpha + (4 * alpha / np.pi)
        elif alpha != 0 and abs(ti) == 1.0 / (4 * alpha):
            h[i] = (alpha / np.sqrt(2)) * (
                (1 + 2 / np.pi) * np.sin(np.pi / (4 * alpha)) +
                (1 - 2 / np.pi) * np.cos(np.pi / (4 * alpha))
            )
        else:
            numerator = (
                np.sin(np.pi * ti * (1 - alpha)) + 
                4 * alpha * ti * np.cos(np.pi * ti * (1 + alpha))
            )
            denominator = np.pi * ti * (1 - (4 * alpha * ti)**2)
            h[i] = numerator / denominator

    return h / np.sqrt(np.sum(h**2))



RRC_SPAN = 8



#--//--//----//--//----//--//----//--//----//--//----//--//----//--//----//--//--



###############
# Conversions #
###############


def sample_to_code(x):
    '''Normal sample 0..1023 -> Comblock-2001 (inverted).'''
    x = max(0, min(FULL_SCALE, int(x)))
    return FULL_SCALE - x




# Transform the 2 bin codes I and Q into bits

def codes_to_mask(code_i, code_q):
    mask = 0
    for bit in range(10):
        if (code_i >> bit) & 1:
            mask |= 1 << I_PINS_BY_BIT[bit]
        if (code_q >> bit) & 1:
            mask |= 1 << Q_PINS_BY_BIT[bit]
    return mask


def mask_to_codes(mask):
    ci = sum(((mask >> I_PINS_BY_BIT[b]) & 1) << b for b in range(10))
    cq = sum(((mask >> Q_PINS_BY_BIT[b]) & 1) << b for b in range(10))
    return ci, cq



'''
Generates an I sample and a Q sample.
Converts them to the codes required by Comblock-2001.
Transforms the codes into the GPIO mask.
Reconstructs the codes from the mask.
Compares the reconstructed codes with the original ones.
'''



#--//--//----//--//----//--//----//--//----//--//----//--//----//--//----//--//--



###################
# Signal creation #
###################


def make_signal(freq_hz, amp, mode, num_symbols, alpha, fs):
    
    half = FULL_SCALE / 2.0
    signal = []


    # Signal modulation
    # -----------------
    
    if mode in ("iq", "i-only", "q-only", "ramp"):
        n = round(fs / freq_hz)
        if n < 3:
            raise SystemExit(f"fs={fs:.0f} S/s too low")
        real_freq = fs / n

    elif mode in ("qpsk", "4ask", "8fsk"):
        # freq_hz viene interpretato come symbol rates
        sps = max(1, round(fs / freq_hz)) #sps = samples per symbol
        if mode == "8fsk" and sps < 8:
           raise SystemExit(f"8fsk requires at least 8 samples per symbol (sps); lower the --freq value (e.g., 10000)")
        real_symrate = fs / sps

    else:
        raise SystemExit("Unknown mode")



    

    if mode == "iq":        #(Ok) 
        for k in range(n):
            ph = 2.0 * math.pi * k / n
            i = half + amp * half * math.cos(ph)
            q = half + amp * half * math.sin(ph)
            signal.append((round(i), round(q)))
        return real_freq, signal

    elif mode == "i-only":  #(OK)
        for k in range(n):
            ph = 2.0 * math.pi * k / n
            i = half + amp * half * math.cos(ph)
            q = MID_CODE
            signal.append((round(i), round(q)))
        return real_freq, signal

    elif mode == "q-only":  #(OK)
        for k in range(n):
            ph = 2.0 * math.pi * k / n
            i = MID_CODE
            q = half + amp * half * math.sin(ph)
            signal.append((round(i), round(q)))
        return real_freq, signal

    elif mode == "ramp":    #(OK)
        for k in range(n):
            r = -1.0 + 2.0 * k / (n - 1)
            i = half + amp * half * r
            q = half - amp * half * r
            signal.append((round(i), round(q)))
        return real_freq, signal

    elif mode == "qpsk":    #(OK)

        level = amp * half
        const = {
            0b00: (+1.0, +1.0),
            0b01: (-1.0, +1.0),
            0b11: (-1.0, -1.0),
            0b10: (+1.0, -1.0),
        }


        random.seed(42)
        symbols = [random.randint(0, 3) for _ in range(num_symbols)]

        def shape(x, h): 
            N = len(x)
            half_len = (len(h) - 1) // 2
            reps = 2 * math.ceil(half_len / N) + 1
            mid = reps // 2
            y = np.convolve(np.tile(x, reps), h, mode="same")
            return y[mid * N : (mid + 1) * N]

        def clip(x):
            return max(0, min(FULL_SCALE, round(x)))



        N = len(symbols) * sps
        i_up = np.zeros(N)
        q_up = np.zeros(N)

        for idx, sym in enumerate(symbols):
            i_up[idx * sps], q_up[idx * sps] = const[sym]

        h = rrcosfilter(alpha, RRC_SPAN, sps)
 

        
        i_shaped = shape(i_up, h)
        q_shaped = shape(q_up, h)
        peak = max(np.max(np.abs(i_shaped)), np.max(np.abs(q_shaped)))
        if peak > 0:
            i_shaped /= peak
            q_shaped /= peak
        

        for i_n, q_n in zip(i_shaped, q_shaped):
            signal.append((clip(half + level * i_n),
                           clip(half + level * q_n)))

        return real_symrate, signal
    

    elif mode == "4ask":    #(Ok)

        level = amp * half

        const = {
            0: -3.0,
            1: -1.0,
            2: +1.0,
            3: +3.0,
        }

        random.seed(42)
        symbols = [random.randint(0, 3) for _ in range(num_symbols)]


        def shape(x, h):
            N = len(x)
            half_len = (len(h) - 1) // 2
            reps = 2 * math.ceil(half_len / N) + 1
            mid = reps // 2
            y = np.convolve(np.tile(x, reps), h, mode="same")
            return y[mid * N : (mid + 1) * N]

        def clip(x):
            return max(0, min(FULL_SCALE, round(x)))



        N = len(symbols) * sps
        i_up = np.zeros(N)
        for idx, sym in enumerate(symbols):
            i_up[idx * sps] = const[sym]

        h = rrcosfilter(alpha, RRC_SPAN, sps)

        i_shaped = shape(i_up, h)

        peak = np.max(np.abs(i_shaped))
        if peak > 0:
            i_shaped /= peak



        for i_n in i_shaped:
            signal.append((clip(half + level * i_n), MID_CODE))

        return real_symrate, signal

    else:#8fsk              #(Ok)

        delta_f = real_symrate * 1.0         

        tone_offsets = [(k - 3.5) * delta_f for k in range(8)]

        random.seed(42)                       # sequenza ripetibile
        symbols = [random.randint(0, 7) for _ in range(num_symbols)]

        phase = 0.0
        two_pi = 2.0 * math.pi

        for sym in symbols:
            freq = tone_offsets[sym]
            phase_inc = two_pi * freq / fs

            for _ in range(sps):
                i = half + amp * half * math.cos(phase)
                q = half + amp * half * math.sin(phase)
                signal.append((round(i), round(q)))
                phase += phase_inc
                # phase %= two_pi          # opzionale (tiene la fase limitata)

        return real_symrate, signal






#--//--//----//--//----//--//----//--//----//--//----//--//----//--//----//--//--




############################
# Creation waveform pigpio #
############################


# Transmission via DMA (Direct Memory Access)


def build_masks(signal):
    return [codes_to_mask(sample_to_code(i), 
                          sample_to_code(q)) 
                          for i, q in signal]



# Prepare the timeline with which the GPIOs will be updated

def build_pulses(masks, period_us, pulse_cls):
    low_us = period_us - 1
    pulses = []
    for m in masks:
        pulses.append(pulse_cls(m, (DATA_MASK & ~m) | CLK_MASK, low_us))
        pulses.append(pulse_cls(CLK_MASK, 0, 1))
    return pulses


#--//--//----//--//----//--//----//--//----//--//----//--//----//--//----//--//--



# Print the connection table to the terminal
# ------------------------------------------

def print_wiring():
    print(f"Clock : GPIO{CLK_PIN} (pin Pi {BCM_TO_PHYS[CLK_PIN]}) -> J3 {J3_PIN['CLK']}")
    print(f"Massa : GND Pi (pin 6, 9, 14, 20, 25, 30, 34, 39) -> J3 {GND_J3}")              # Guarda i pin sulla raspberry
    print(f"{'segnale':<14}{'GPIO':>6}{'pin Pi':>8}   J3")
    for bit in range(9, -1, -1):    # start / stop / step
        for ch, signal in (("I", I_PINS_BY_BIT), ("Q", Q_PINS_BY_BIT)):
            g = signal[bit]
            print(f"DATA_{ch}_IN({bit})".ljust(14) + f"{g:>6}{BCM_TO_PHYS[g]:>8}   {J3_PIN[f'{ch}{bit}']}")

                # Signal name.
                # GPIO number.
                # Physical pin of the Raspberry Pi.
                # Corresponding pin of the J3 connector.




#---//--//----//--//----//--//----//--//----//--//----//--//----//--//----//--//-
#--//--//----//--//----//--//----//--//----//--//----//--//----//--//----//--//--




# ---------------------------  MAIN  ----------------------------


def main():

    ap = argparse.ArgumentParser(description="Raspberry Pi Model 3B -> Comblock-2001 -> Oscilloscope")
    ap.add_argument("--freq", type=float, default=100_000, help="Tone frequency [Hz] or symbol rate in QPSK mode (default 100_000)")
    ap.add_argument("--period-us", type=int, default=2, help="Sampling period [µs] (default 2 = 500 kS/s)")
    ap.add_argument("--amp", type=float, default=0.5, help="Amplitude 0..1 (default 0.5)")
    ap.add_argument("--mode", default="iq", choices=["iq", "i-only", "q-only", "ramp", "qpsk", "4ask", "8fsk"], help="iq | i-only | q-only | ramp | qpsk | 4ask | 8fsk")
    ap.add_argument("--alpha", type=float, default=0.35, help="RRC filter roll-off factor (default 0.35)")
    ap.add_argument("--symbols", type=int, default=32, help="Number of QPSK symbols in table (default 32)")
    ap.add_argument("--wiring", action="store_true", help="Show wiring diagram and exit")
    ap.add_argument("--dry-run", action="store_true", help="Only perform calculations, without interacting with GPIOs")
    a = ap.parse_args()

    

    # Essential conditions otherwise the project makes no sense
    # ---------------------------------------------------------

    if a.period_us < 2:
        raise SystemExit("--period-us must be >= 2 (2 pulses of >= 1 us each are required per sample)")
    if not 0 < a.amp <= 1:
        raise SystemExit("--amp must be (0, 1]")

    print_wiring()
    if a.wiring:
        return

    fs = 1e6 / a.period_us

    real_freq, signal = make_signal(a.freq, a.amp, a.mode, a.symbols, a.alpha, fs)
    masks = build_masks(signal)


    # Self-check
    # If the values ​​do not match, the assert statement generates an error
    for (i, q), m in zip(signal, masks):
        assert mask_to_codes(m) == (sample_to_code(i), sample_to_code(q))



    # Digital modulation mode
    if a.mode in ("qpsk", "4ask", "8fsk"):
        print(f"fs = {fs/1e3:.0f} kS/s | simboli = {a.symbols} | "
              f"symbol rate = {real_freq/1e3:.3f} kBaud (richiesto {a.freq/1e3:.3f} kBaud)")
        print(f"Campioni per simbolo ≈ {len(signal)//a.symbols}")
    else:   # iq / i-only / ramp
        print(f"fs = {fs/1e3:.0f} kS/s | campioni/periodo = {len(signal)} | "
              f"frequenza tono = {real_freq/1e3:.3f} kHz (richiesta {a.freq/1e3:.3f} kHz)")
    print("k   I(norm) Q(norm)   I(COM) Q(COM) [hex]")





    # Creating the 2nd table on the terminal
    # --------------------------------------

    # At least print only the first 40 samples
    for k, (i, q) in enumerate(signal[:min(40, len(signal))]):  
        print(f"{k:<3}{i:>8}{q:>8}     {sample_to_code(i):03X}    {sample_to_code(q):03X}")
                                                        #:03x is a hexadecimal number, uppercase, at least 3 digits
    
    if len(signal) > 40:                                
        print(f"... ({len(signal)} total samples)")

    if a.dry_run:
        print("\ndry-run: no GPIO touched.")
        return

    
    try:
        import pigpio
    except ImportError:
        raise SystemExit("pigpio is not installed: sudo apt install python3-pigpio")
    

    pi = pigpio.pi()

    if not pi.connected:
        raise SystemExit("pigpiod is not active: sudo systemctl start pigpiod")


    center = codes_to_mask(sample_to_code(MID_CODE), sample_to_code(MID_CODE))

    
    try:
        for g in ALL_PINS:
            pi.set_mode(g, pigpio.OUTPUT)
            pi.write(g, 0)


        # Preparing for DMA transmission
        pi.wave_clear()
        pi.wave_add_generic(build_pulses(masks, a.period_us, pigpio.pulse)) # I delete previously stored waveforms
        wid = pi.wave_create()                                              
        # The pulse sequence that will be transmitted on the GPIOs is constructed and added
        
        if wid < 0:
            raise SystemExit(f"wave_create has returned {wid}")

        print("\nDMA transmission started. Use Ctrl+C to stop transmission.")
        pi.wave_send_repeat(wid)
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStop transmission.")

    finally:
        pi.wave_tx_stop()
        pi.wave_clear()

        for g in ALL_PINS:
            pi.write(g, 1 if (center >> g) & 1 and g != CLK_PIN else 0)
        pi.stop()




if __name__ == "__main__":
    main()


# ------------------------ END MAIN -----------------------


#---//--//----//--//----//--//----//--//----//--//----//--//----//--//----//--//-
#--//--//----//--//----//--//----//--//----//--//----//--//----//--//----//--//--
