

#-----------Librerie------------


import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.widgets import Slider, Button
import os







# ------------------------ Functions + Modem -------------------------



# Funzione a coseno rialzato (Root-Raised Cosine)
# -----------------------------------------------

def rrcosfilter(alpha, span, sps):
    
    t = np.arange(-span * sps / 2, span * sps / 2 + 1) / sps
    h = np.zeros(len(t)) 
    
    for i in range(len(t)):
        ti = t[i] 

        if ti == 0.0: 
            h[i] = 1.0 - alpha + (4 * alpha / np.pi)

        elif alpha != 0 and abs(ti) == 1.0 / (4 * alpha):
            #print(ti)
            h[i] = (alpha / np.sqrt(2)) * (
                (1 + 2 / np.pi) * np.sin(np.pi / (4 * alpha)) +
                (1 - 2 / np.pi) * np.cos(np.pi / (4 * alpha))
            )

        else:
            numerator = (
                np.sin(np.pi * ti * (1 - alpha)) + 
                4 * alpha * ti * np.cos(np.pi * ti * (1 + alpha)))
            denominator = np.pi * ti * (1 - (4 * alpha * ti)**2)
            h[i] = numerator / denominator

    return h / np.sqrt(np.sum(h**2))




# Define the geometric shapes within the constellations
# -----------------------------------------------------

class Geometric_Shapes:

    def __init__(self, data):
        self.data = data


    def circle(self, data): 
        circle = mpatches.Circle(
            (0, 0),              # center of the circle
            1.0,                 # radius
            transform=self.data.transData,
            facecolor='none',    # border only
            edgecolor='black',
            linestyle='--',
            linewidth=0.8,
            alpha=0.75
        )
        return circle


    def small_rectangle(self, data): 
        small_rectangle = mpatches.Rectangle(
            (-np.sqrt(2)/2, -np.sqrt(2)/2),             
            transform=self.data.transData,
            width=np.sqrt(2),                     
            height=np.sqrt(2),
            facecolor='none',                      
            edgecolor='black',
            linestyle='--',
            linewidth=0.8,
            alpha=0.75,
            zorder=1
        )
        return small_rectangle

    
    def large_rectangle(self, data): 
        large_rectangle = mpatches.Rectangle(
            (-1, -1),           
            transform=self.data.transData,
            width=2,                    
            height=2,
            facecolor='none',                      
            edgecolor='black',
            linestyle='--',
            linewidth=0.8,
            alpha=0.75,
            zorder=2
        )
        return large_rectangle






# Add AWGN (Additive White Gaussian Noise)
# ----------------------------------------

def add_noise(signal, snr_db):
    signal_power = np.mean(np.abs(signal)**2)
    linear_snr = 10**(snr_db / 10.0)
    noise_power = signal_power / linear_snr
    noise = np.sqrt(noise_power / 2) * (np.random.randn(len(signal))
    + 1j * np.random.randn(len(signal)))
    return signal + noise


def add_noise_common(clusters, snr_db):
    all_pts = np.concatenate(clusters)
    signal_power = np.mean(np.abs(all_pts)**2)       
    noise_power = signal_power / 10**(snr_db / 10)
    sigma = np.sqrt(noise_power / 2)/4            
    return [c + sigma * (np.random.randn(len(c)) + 1j*np.random.randn(len(c)))
            for c in clusters]




################################################################
# Class definition for creating a digital-type modulation mode #
################################################################


class Modem:

    def __init__(self, mod_type):
        self.mod_type = mod_type.lower()


    def modulate(self, bits, fase, n):
        cos = np.cos(fase + np.pi/n); sin = 1j*np.sin(fase + np.pi/n)

        
        if self.mod_type == 'bpsk' or self.mod_type == '2ask':
            
            constellation = np.array([1j* (-cos-sin), 1j* (cos+sin)])
            return constellation[bits]


        elif self.mod_type == 'ook':

            constellation = np.array([0, -1j* (cos+sin)])
            return constellation[bits]


        elif self.mod_type == '4ask':

            constellation = np.array([
                1j*(-cos-sin),
                1j*(+cos+sin),
                3j*(-cos-sin),
                3j*(+cos+sin)
            ])

            symbols = np.zeros(len(bits) // 2, dtype=complex)
            for i in range(0, len(bits), 2):
                idx = (bits[i] << 1) | bits[i+1]
                symbols[i // 2] = constellation[idx]
            return symbols


        elif self.mod_type == '8ask':
        
            constellation = np.array([
                1j*(-cos-sin),
                1j*(+cos+sin),
                3j*(-cos-sin),
                3j*(+cos+sin),
                5j*(-cos-sin),
                5j*(+cos+sin),
                7j*(-cos-sin),
                7j*(+cos+sin)
            ])

            # costellation = = np.array([-7, -5, -1, -3, +7, +5, +1, +3])

            symbols = np.zeros(len(bits) // 3, dtype=complex)
            for i in range(0, len(bits), 3):
                idx = (bits[i] << 2) | (bits[i+1] << 1) | bits[i+2]
                symbols[i // 3] = constellation[idx]
            return symbols

        
        elif self.mod_type == 'qpsk':
            
            constellation = np.array([
                -cos-sin,
                1j*(-cos-sin),
                1j*(+cos+sin),
                +cos+sin
            ])

            symbols = np.zeros(len(bits) // 2, dtype=complex)

            for i in range(0, len(bits), 2):
                idx = (bits[i] << 1) | bits[i+1] 
                symbols[i // 2] = constellation[idx]
            return symbols

        
        elif self.mod_type == '8psk':

            constellation = np.array([
                (-cos-sin) * np.sqrt(2),
                (1j*(-cos-sin)) * np.sqrt(2),
                (1j*(+cos+sin)) * np.sqrt(2),
                (+cos+sin)* np.sqrt(2),
                ((-cos-sin) + 1j*(-cos-sin)),
                ((+cos+sin) + 1j*(-cos-sin)),
                ((-cos-sin) + 1j*(+cos+sin)),
                ((+cos+sin) + 1j*(+cos+sin)),
            ]) / np.sqrt(2)


            symbols = np.zeros(len(bits) // 3, dtype=complex)

            for i in range(0, len(bits), 3):
                idx = (bits[i] << 2) | (bits[i+1] << 1) | bits[i+2]
                symbols[i // 3] = constellation[idx]
            return symbols
                
        else:
            raise ValueError("Unsupported modulation type")




################
# Eye diagramm #
################

def eye_diagram(num_traces):
    global eye_real_lines, eye_imag_lines

    eye_real_lines = []
    eye_imag_lines = []

    for i in range(num_traces):
        start_idx = i * sps
        
        segnale_reale = np.real(real_signal[start_idx : start_idx + trace_length])
        segnale_immaginario = np.imag(real_signal[start_idx : start_idx + trace_length])
            

        if mod_type in ('bpsk', '2ask', '8ask', '4ask', 'ook'):
            line, = f2_ax4.plot(segnale_reale, color='b', linewidth=0.5)
            eye_real_lines.append(line)
        elif mod_type == 'qpsk':
            line, = f2_ax4.plot(segnale_reale, color='b', linewidth=0.5)
            eye_real_lines.append(line)
            line, = f2_ax4.plot(segnale_immaginario, color='r', linewidth=0.6)
            eye_imag_lines.append(line)
        elif mod_type == '8psk':
            line, = f2_ax4.plot(segnale_reale, color='b', linewidth=0.5)
            eye_real_lines.append(line)
            line, = f2_ax4.plot(segnale_immaginario, color='r', linewidth=0.6)
            eye_imag_lines.append(line)
        else:
            raise ValueError("Unsupported modulation type")
        


# ------------------------ End Functions + End Modem -------------------------



#---//--//----//--//----//--//----//--//----//--//----//--//----//--//----//--//-
#--//--//----//--//----//--//----//--//----//--//----//--//----//--//----//--//--




# ---------------------------  MAIN  ----------------------------

# Parameters
Fs = 1_000_000                                  # Sampling frequency
Rs = 100_000                                    # Symbol rate (it is better to have a reasonable oversampling)
sps = int(Fs / Rs)                              # Samples per symbol (I convert it to an integer; otherwise, Upsample will throw an error)
alpha = 0.4                                     # Roll-off factor
N_bits = 1000


# Filter parameters
span = 8                                        # Filter lifespan in symbols
filter_length = span * sps                      # Filter length
mod_type = '8psk'                               # Modulation type
phase = np.pi*2;                                # Maximum phase for differences to be visible (np.pi/6)
deg_angle = np.rad2deg(phase)

# Possible mod_types: bpsk, qpsk, 8psk, 2ask, 4ask, 8ask, ook


if mod_type == ( '8psk' ) :
    N_bits = N_bits // 3
    N_bits = N_bits * 3 + 3
    n=8
elif mod_type == '8ask':
    N_bits = N_bits // 3
    N_bits = N_bits * 3 + 3
    n = 2
elif mod_type == ( 'qpsk' ):
    n=4
else:
    n=2



bits = np.random.randint(0, 2, N_bits) 
bits = np.array([0] * (N_bits // 2) + [1] * (N_bits // 2))
np.random.shuffle(bits)


# Note
if alpha == 0:

    print("The time-domain response is an ideal sinc(t/T) function; " \
        "it oscillates for a long duration and decays very slowly (1/t). " \
        "This makes the system extremely sensitive to clock jitter and sampling errors, " \
        "leading to ISI (intersymbol interference) if synchronization is not perfect. " \
        " " \
        "Furthermore, an ideal filter is non-causal and physically unrealizable. " \
        "Nevertheless, we can explore it using this Python script!")
    
elif alpha == 1:

    print("The response decays very rapidly over time (1/t^3) and features additional intermediate zeros. \
          This makes the system exceptionally robust against timing errors. \
          Furthermore, the risk of practical ISI (intersymbol interference) is drastically reduced. \
          However, there is a disadvantage in terms of spectral efficiency, which is halved.")
    
else:
    print("")





# Saving bits
"""
exists = os.path.exists('/home/cirelli/Desktop/UNI/Wireless/Valori.txt') 
isfile = os.path.isfile('/home/cirelli/Desktop/UNI/Wireless/Valori.txt')

if ((exists == True) and (isfile == True)):
    print("I want this file!")
else:
    print("The file will be created!")
"""


# Include the correct $PATH in oder to see in Values.txt the bits values
with open(r"./Values.txt", "w") as file:
    for i in range(0, len(bits), 100):
        file.write("".join(map(str, bits[i:i+100])) + "\n")
file.close()




# Program initialization
# ----------------------

modulazione = Modem(mod_type)
symbols = modulazione.modulate(bits, phase, n)


# Upsample
signal = np.zeros(len(symbols) * sps, dtype=complex)            # Empty vector
signal[::sps] = symbols                                         # Fill the vector
psf_coeff = rrcosfilter(alpha, span, sps)                       # Pulse shaping with RRC filter
shaped_signal = np.convolve(signal, psf_coeff, mode='same')     # Convoution between signal e RRC filter
SNR_db = 20; real_signal = add_noise(shaped_signal, SNR_db)     # Add AWGN 



# ------------------------ END MAIN -----------------------




#---//--//----//--//----//--//----//--//----//--//----//--//----//--//----//--//-
#--//--//----//--//----//--//----//--//----//--//----//--//----//--//----//--//--




# ------------------------ Plots --------------------------


fig2 = plt.figure(figsize=(16, 9), constrained_layout=True)
bordi = fig2.add_gridspec(12, 12)




#######################
# Diagramma ad occhio #
#######################

if mod_type in ('4ask', '8ask'):
    f2_ax4 = fig2.add_subplot(bordi[6:, :7]) 
    trace_length = 2 * sps
else:
    f2_ax4 = fig2.add_subplot(bordi[6:, :8]) 
    trace_length = 2 * (sps + 5)

# With the +5, it extends the signal so that two eyes become visible.


num_traces = (len(real_signal) - trace_length) // sps



# Mostro solo il diagramma
eye_diagram(num_traces)


f2_ax4.autoscale(enable=True, axis="x", tight=True)
f2_ax4.set_title("Oscilloscopio: Eye Diagram of s(t)")
f2_ax4.set_xlabel("Samples within " + str(trace_length / sps) + " Symbol Periods")
#f2_ax4.set_ylabel("Amplitude")
ay_top = f2_ax4.twinx()
ay_top.set_ylim(-1 ,1)

f2_ax4.grid(True)




############################
# Fine Diagramma ad occhio #
############################



#--//--//----//--//----//--//----//--//----//--//----//--//----//--//----//--//--



#################
# Ingrandimento #
#################

figura2 = fig2.add_subplot(bordi[:6, :7])




# Represented signals
# -------------------


# (Note) I have to put a comma otherwise the sets are useless.
line_real, = figura2.plot([], [], color='b', label='I') 
if mod_type not in ('bpsk', '2ask', '4ask', '8ask', 'ook'):
    line_imag, = figura2.plot([], [], color='r', label='Q')



N = len(shaped_signal)
parte_len = N // 5
parti = [(i * parte_len, (i + 1) * parte_len) for i in range(5)]



# Slider
# ------

if mod_type in ('4ask', '8ask'):
    left = 0.64
else:
    left = 0.72

ax_slider = fig2.add_axes((left, 0.04, 0.0225, 0.42)) #[left, bottom, width, height]
slider = Slider(
    ax=ax_slider,
    label="Bits",
    valmin=1,
    valmax=5,
    valinit=1,
    valstep=1,
    orientation="vertical"
)


# Update Slider
# -------------

def update(val):
    idx = int(slider.val) - 1                
    start, stop = parti[idx]
    x = np.arange(start, stop)

    y_real = np.real(shaped_signal[start:stop])
    line_real.set_data(x, y_real)

    if mod_type not in ('bpsk', '2ask', '4ask', '8ask', 'ook'):
        y_imag = np.imag(shaped_signal[start:stop])
        line_imag.set_data(x, y_imag)
        ymin = min(y_real.min(), y_imag.min())
        ymax = max(y_real.max(), y_imag.max())
        line_imag.set_visible(True)
    else:
        ymin, ymax = y_real.min(), y_real.max()


    figura2.set_xlim(start, stop)
    figura2.set_ylim(ymin, ymax)
    figura2.set_title(f"Parte {idx+1} / 5  (campioni {start} -> {stop-1})")
    figura2.set_xlabel("Campione", loc='left')
    #figura2.set_ylabel("Ampiezza")
    line_real.set_visible(True)

    for line in eye_real_lines:
        line.set_visible(True)

    for line in eye_imag_lines:
        line.set_visible(True)

    ay_top = figura2.twinx()
    ay_top.set_ylim(-1 ,1)
    figura2.grid(True)
    figura2.legend()
    figura2.legend(loc='lower right')
    fig2.canvas.draw_idle()


# I'll show the various spans, starting with the first one.
slider.on_changed(update); update(1)




###########
# Bottoni #
###########


# 5 Buttons for the 5 spans
# -------------------------

selector0 = fig2.add_axes((0.642, 0.510, 0.06, 0.035)) #[left, bottom, width, height]
selector1 = fig2.add_axes((0.642, 0.555, 0.06, 0.035)) #[left, bottom, width, height]
selector2 = fig2.add_axes((0.642, 0.600, 0.06, 0.035)) #[left, bottom, width, height]
selector3 = fig2.add_axes((0.642, 0.645, 0.06, 0.035)) #[left, bottom, width, height]
selector4 = fig2.add_axes((0.642, 0.690, 0.06, 0.035)) #[left, bottom, width, height]


# 2 buttons for the 2 colors
# --------------------------
selector8 = fig2.add_axes((0.61, 0.732, 0.125, 0.128)) #[left, bottom, width, height]
selector9 = fig2.add_axes((0.61, 0.865, 0.125, 0.128)) #[left, bottom, width, height]





# Correlation: Buttons <==> Slider
# --------------------------------

color_button = 'purple'
color_button_label = 'white'

button0 = Button(selector0, 'Span  1', color=color_button, hovercolor='0.0')
button1 = Button(selector1, 'Span  2', color=color_button, hovercolor='0.0')
button2 = Button(selector2, 'Span  3', color=color_button, hovercolor='0.0')
button3 = Button(selector3, 'Span  4', color=color_button, hovercolor='0.0')
button4 = Button(selector4, 'Span  5', color=color_button, hovercolor='0.0')
button0.label.set_color(color_button_label)
button1.label.set_color(color_button_label)
button2.label.set_color(color_button_label)
button3.label.set_color(color_button_label)
button4.label.set_color(color_button_label)



# Include the correct $PATH in oder to see button_image_red/blu
image_red = plt.imread(r'./red.jpg')
image_blu = plt.imread(r'./blu.jpg')


button8 = Button(selector8, 'BLU', image=image_blu, hovercolor='0.975')
button9 = Button(selector9, 'RED', image=image_red, hovercolor='0.975')




# Update dei valori coi bottoni
# -----------------------------

def change(event):
    slider.set_val(update)

button0.on_clicked(lambda event: slider.set_val(1))
button1.on_clicked(lambda event: slider.set_val(2))
button2.on_clicked(lambda event: slider.set_val(3)) 
button3.on_clicked(lambda event: slider.set_val(4))
button4.on_clicked(lambda event: slider.set_val(5))



# BLUE + RED buttons, BLUE and RED
# --------------------------------

REAL_ONLY = mod_type in ('bpsk', '2ask', '4ask', '8ask', 'ook')


def show_blue(event):

    line_real.set_visible(True)
    for line in eye_real_lines:
        line.set_visible(True)

    if not REAL_ONLY:                      
        line_imag.set_visible(False)
        for line in eye_imag_lines:
            line.set_visible(False)

    fig2.canvas.draw_idle()




def show_red(event):

    if REAL_ONLY:
        return

    line_real.set_visible(False)
    line_imag.set_visible(True)

    for line in eye_real_lines:
        line.set_visible(False)
    for line in eye_imag_lines:
        line.set_visible(True)

    fig2.canvas.draw_idle()



button8.on_clicked(show_blue)   # BLU
button9.on_clicked(show_red)    # RED




#####################################
# Fine Magnification + Fine Buttons #
#####################################



#--//--//----//--//----//--//----//--//----//--//----//--//----//--//----//--//--




#################
# Constellation #
#################



f2_ax2 = fig2.add_subplot(bordi[:6, 9:])



# Various types of modulation
# ---------------------------

N_pts = sps * 100                                   
rot   = np.exp(1j * phase)                          


if mod_type in ('qpsk', '8psk'):
    M = 4 if mod_type == 'qpsk' else 8
    data = np.random.randint(0, M, N_pts)
    clusters = [np.exp(1j * (2*np.pi*data/M + np.pi/M + phase))]

elif mod_type == 'ook':
    clusters = [np.full(N_pts, rot), np.zeros(N_pts, dtype=complex)]

elif mod_type in ('bpsk', '2ask', '4ask', '8ask'):
    levels = {'bpsk': [1], '2ask': [1], '4ask': [1, 3], '8ask': [1, 3, 5, 7]}[mod_type]
    sign = np.random.choice([-1, 1], N_pts)
    clusters = [lv * sign * rot for lv in levels]

else:
    raise ValueError("Unsupported modulation type")



for c in clusters:
    f2_ax2.plot(np.real(c), np.imag(c), '.b')

if mod_type == 'ook':
    f2_ax2.set_title("OOK")
elif mod_type == 'qpsk' and phase != np.pi/4:
    f2_ax2.set_title("4qam / qpsk")
else:
    f2_ax2.set_title(mod_type)




f2_ax2.set_ylabel( "Amplitude" )
forma = Geometric_Shapes(f2_ax2)
circle = forma.circle(f2_ax2)
rect1 = forma.small_rectangle(f2_ax2)
rect2 = forma.large_rectangle(f2_ax2)
f2_ax2.add_patch(circle)
f2_ax2.add_patch(rect1)
f2_ax2.add_patch(rect2)


f2_ax2.grid(True)



#####################
# End Constellation #
#####################



#--//--//----//--//----//--//----//--//----//--//----//--//----//--//----//--//--




###########################
# Constellation with AWGN #
###########################

if mod_type in ('4ask', '8ask'):
    f2_ax3 = fig2.add_subplot(bordi[6:, 8:])
else:
    f2_ax3 = fig2.add_subplot(bordi[6:, 9:])



n = (np.random.randn(sps*100) + 1j*np.random.randn(sps*100))/np.sqrt(2)
snr_lineare = 10**(-SNR_db / 10.0)



#clusters = [np.ravel(s) for s in (x_sym, *[globals()[k] for k in ('x1_sym', 'x2_sym', 'x3_sym') if k in globals()])]
for r in add_noise_common(clusters, SNR_db):
    f2_ax3.plot(np.real(r), np.imag(r), '.b')



if phase == np.pi/4 and mod_type == 'qpsk':
    f2_ax3.set_title( "4PSK constellation with noise")
elif phase == np.pi/4 and mod_type == '4psk':
    f2_ax3.set_title( "4PSK constellation with noise")
else:
    f2_ax3.set_title( "Constellation " + mod_type + " with noise")

f2_ax3.set_xlabel( "Time (Symbols)" )
#f2_ax3.set_ylabel( "Amplitude" )



forma = Geometric_Shapes(f2_ax3)
circle = forma.circle(f2_ax3)
rect1 = forma.small_rectangle(f2_ax3)
rect2 = forma.large_rectangle(f2_ax3)
f2_ax3.add_patch(circle)
f2_ax3.add_patch(rect1)
f2_ax3.add_patch(rect2)



f2_ax3.grid(True)



plt.show()


################################
# Fine constellation with AWGN #
################################


# ------------------------ End Plots --------------------------







# ---------------------------- End  ---------------------------