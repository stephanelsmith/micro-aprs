import tkinter as tk
from ttkbootstrap import Style, ttk
from ttkbootstrap.constants import *
import os
import json
import threading
import time
import re
import wave
import struct
import asyncio
from core.transmitter import ResampleAndSend  # Assurez-vous d'importer correctement ResampleAndSend
from core import reset_hackrf

class Application(ttk.Frame):
    CONFIG_FILE = "config.json"

    def __init__(
        self,
        master,
        frequency_var,
        transmitting_var,
        message_queue,
        stop_event,
        gain_var,
        if_gain_var,
        receiver_stop_event,
        receiver_thread,
        received_message_queue,
        udp_transmitter,
        device_index_var,
        *args,
        **kwargs
    ):
        super().__init__(master, *args, **kwargs)

        self.master = master
        self.frequency_var = frequency_var
        self.transmitting_var = transmitting_var
        self.message_queue = message_queue
        self.stop_event = stop_event
        self.gain_var = gain_var
        self.if_gain_var = if_gain_var
        self.receiver_stop_event = receiver_stop_event
        self.receiver_thread = receiver_thread
        self.received_message_queue = received_message_queue
        self.udp_transmitter_func = udp_transmitter
        self.device_index_var = device_index_var

        # Valeurs par défaut
        self.send_ip = "127.0.0.1"
        self.send_port = 14581
        self.num_flags_before = tk.IntVar(value=10)
        self.num_flags_after = tk.IntVar(value=4)

        self.status_var = tk.StringVar(value="Prêt")
        self.receiver_status_var = tk.StringVar(value="Récepteur en cours")

        # Variable pour stocker l'instance du top block en mode Carrier Only
        self.carrier_top_block = None

        self.load_config()

        self.send_icon = None
        self.transmitting_icon = None
        self.idle_icon = None

        self.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.canvas = tk.Canvas(self, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.load_icons()
        self.create_widgets()

        self.after(500, self.check_transmission_status)
        self.after(500, self.check_received_messages)

        self.master.bind("<Escape>", self.exit_fullscreen)

    def exit_fullscreen(self, event=None):
        self.master.attributes('-fullscreen', False)

    def load_icons(self):
        assets_path = os.path.join(os.path.dirname(__file__), 'assets')
        if not os.path.isdir(assets_path):
            os.makedirs(assets_path)
            self.status_var.set(f"Répertoire 'assets' créé à {assets_path}. Ajoutez les fichiers d'icônes requis.")
            return
        try:
            self.send_icon = tk.PhotoImage(file=os.path.join(assets_path, 'send_icon.png'))
            self.transmitting_icon = tk.PhotoImage(file=os.path.join(assets_path, 'transmitting_icon.png'))
            self.idle_icon = tk.PhotoImage(file=os.path.join(assets_path, 'idle_icon.png'))
        except Exception as e:
            self.status_var.set(f"Erreur lors du chargement des icônes : {e}")
            self.send_icon = None
            self.transmitting_icon = None
            self.idle_icon = None

    def create_widgets(self):
        # Header
        header = ttk.Label(
            self.scrollable_frame,
            text="Contrôle de Transmission APRS",
            font=("Helvetica", 18, "bold")
        )
        header.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="w")

        # Left Container: Device Selection, HackRF Settings (including Frequency), Callsign, UDP Config
        left_container = ttk.Frame(self.scrollable_frame)
        left_container.grid(row=1, column=0, sticky="nsew", padx=(0, 10), pady=(0, 20))
        left_container.columnconfigure(0, weight=1)

        # Device Selection Frame
        device_frame = ttk.Labelframe(left_container, text="Sélection de l'appareil HackRF", padding=20)
        device_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        device_frame.columnconfigure(1, weight=1)

        ttk.Label(device_frame, text="HackRF :").grid(row=0, column=0, sticky="w")
        self.device_combobox = ttk.Combobox(device_frame, state="readonly")
        self.device_combobox.grid(row=0, column=1, pady=5, padx=10, sticky="ew")
        self.populate_device_combobox()

        # HackRF Settings Frame (including Frequency)
        hackrf_frame = ttk.Labelframe(left_container, text="Paramètres du HackRF", padding=20)
        hackrf_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        hackrf_frame.columnconfigure(1, weight=1)

        # Gain Settings
        ttk.Label(hackrf_frame, text="Gain :").grid(row=0, column=0, sticky="w")
        self.gain_entry = ttk.Entry(hackrf_frame, width=20)
        self.gain_entry.grid(row=0, column=1, pady=5, padx=10, sticky="ew")
        self.gain_entry.delete(0, tk.END)
        self.gain_entry.insert(0, str(self.gain_var.get()))

        ttk.Label(hackrf_frame, text="Gain IF :").grid(row=1, column=0, sticky="w")
        self.if_gain_entry = ttk.Entry(hackrf_frame, width=20)
        self.if_gain_entry.grid(row=1, column=1, pady=5, padx=10, sticky="ew")
        self.if_gain_entry.delete(0, tk.END)
        self.if_gain_entry.insert(0, str(self.if_gain_var.get()))

        # Frequency Settings (Integrated into HackRF Settings)
        ttk.Label(hackrf_frame, text="Fréquence (MHz) :").grid(row=2, column=0, sticky="w")
        self.frequency_entry = ttk.Entry(hackrf_frame, width=20)
        self.frequency_entry.grid(row=2, column=1, pady=5, padx=10, sticky="ew")
        freq_mhz = self.frequency_var.get() / 1e6
        self.frequency_entry.delete(0, tk.END)
        self.frequency_entry.insert(0, f"{freq_mhz:.2f}")

        self.freq_notification = ttk.Label(hackrf_frame, text="", foreground="red")
        self.freq_notification.grid(row=3, column=0, columnspan=2, sticky="w")

        # Callsign Parameters Frame
        callsign_frame = ttk.Labelframe(left_container, text="Paramètres de l'indicatif d'appel", padding=20)
        callsign_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        callsign_frame.columnconfigure(1, weight=1)

        ttk.Label(callsign_frame, text="Indicatif d'appel de source :").grid(row=0, column=0, sticky="w")
        self.callsign_entry = ttk.Entry(callsign_frame, width=25)
        self.callsign_entry.grid(row=0, column=1, pady=5, padx=10, sticky="ew")
        callsign = getattr(self, 'saved_callsign', "VE2FPD")
        self.callsign_entry.insert(0, callsign)

        ttk.Label(callsign_frame, text="Indicatif d'appel de destination :").grid(row=1, column=0, sticky="w")
        self.dest_callsign_entry = ttk.Entry(callsign_frame, width=25)
        self.dest_callsign_entry.grid(row=1, column=1, pady=5, padx=10, sticky="ew")
        dest_callsign = getattr(self, 'saved_dest_callsign', "VE2FPD-2")
        self.dest_callsign_entry.insert(0, dest_callsign)

        ttk.Label(callsign_frame, text="Longueur du préambule :").grid(row=2, column=0, sticky="w")
        self.flags_before_entry = ttk.Entry(callsign_frame, width=10)
        self.flags_before_entry.grid(row=2, column=1, pady=5, padx=10, sticky="ew")
        self.flags_before_entry.delete(0, tk.END)
        self.flags_before_entry.insert(0, str(self.num_flags_before.get()))

        ttk.Label(callsign_frame, text="Longueur du postambule :").grid(row=3, column=0, sticky="w")
        self.flags_after_entry = ttk.Entry(callsign_frame, width=10)
        self.flags_after_entry.grid(row=3, column=1, pady=5, padx=10, sticky="ew")
        self.flags_after_entry.delete(0, tk.END)
        self.flags_after_entry.insert(0, str(self.num_flags_after.get()))

        self.callsign_notification = ttk.Label(callsign_frame, text="", foreground="red")
        self.callsign_notification.grid(row=4, column=0, columnspan=2, sticky="w")

        # Transmission UDP Configuration Frame
        udp_frame = ttk.Labelframe(left_container, text="Paramètres UDP", padding=20)
        udp_frame.grid(row=3, column=0, sticky="ew", pady=(0, 20))
        udp_frame.columnconfigure(1, weight=1)

        ttk.Label(udp_frame, text="IP de destination:").grid(row=0, column=0, sticky="w")
        self.send_ip_entry = ttk.Entry(udp_frame, width=25)
        self.send_ip_entry.grid(row=0, column=1, pady=5, padx=10, sticky="ew")
        self.send_ip_entry.delete(0, tk.END)
        self.send_ip_entry.insert(0, self.send_ip)

        ttk.Label(udp_frame, text="Port UDP de destination:").grid(row=1, column=0, sticky="w")
        self.send_port_entry = ttk.Entry(udp_frame, width=25)
        self.send_port_entry.grid(row=1, column=1, pady=5, padx=10, sticky="ew")
        self.send_port_entry.delete(0, tk.END)
        self.send_port_entry.insert(0, str(self.send_port))

        # Apply Settings Button
        self.apply_all_button = ttk.Button(left_container, text="Appliquer tous les paramètres", command=self.apply_all_settings)
        self.apply_all_button.grid(row=4, column=0, sticky="ew", pady=(10, 0))

        # Right Container: Carrier Only, Send Button, Message Test, Messages Received, Status
        right_container = ttk.Frame(self.scrollable_frame)
        right_container.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(0, 20))
        right_container.columnconfigure(0, weight=1)

        # Carrier Only Frame
        carrier_frame = ttk.Labelframe(right_container, text="Mode de transmission", padding=20)
        carrier_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        carrier_frame.columnconfigure(0, weight=1)

        self.carrier_only_var = tk.BooleanVar(value=False)
        self.carrier_only_checkbox = ttk.Checkbutton(
            carrier_frame,
            text="Porteuse seulement",
            variable=self.carrier_only_var,
            command=self.toggle_carrier_only
        )
        self.carrier_only_checkbox.grid(row=0, column=0, sticky="w")

        # Send Button
        send_frame = ttk.Frame(right_container)
        send_frame.grid(row=1, column=0, sticky="ew", pady=(10, 20))
        send_frame.columnconfigure(0, weight=1)

        # Message Test APRS Frame
        test_frame = ttk.Labelframe(right_container, text="Message de test", padding=20)
        test_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        test_frame.columnconfigure(0, weight=1)

        ttk.Label(test_frame, text="Message:").grid(row=0, column=0, sticky="w")

        self.test_message_entry = ttk.Entry(test_frame, width=40)
        self.test_message_entry.grid(row=1, column=0, padx=5, pady=(0, 10), sticky="ew")
        self.test_message_entry.insert(0, "TEST 123!")  # Valeur par défaut

        self.test_button = ttk.Button(
            test_frame,
            text="Envoyer le message de test",
            command=self.queue_test_message
        )
        self.test_button.grid(row=2, column=0, sticky="ew", ipadx=10, ipady=5)

        # Messages Received Frame
        messages_frame = ttk.Labelframe(right_container, text="Messages Reçus", padding=20)
        messages_frame.grid(row=3, column=0, sticky="nsew", pady=(0, 20))
        messages_frame.columnconfigure(0, weight=1)
        messages_frame.rowconfigure(0, weight=1)

        self.messages_text = tk.Text(messages_frame, wrap='word', height=10)
        self.messages_text.grid(row=0, column=0, sticky="nsew")

        msg_scrollbar = ttk.Scrollbar(messages_frame, orient='vertical', command=self.messages_text.yview)
        msg_scrollbar.grid(row=0, column=1, sticky='ns')
        self.messages_text['yscrollcommand'] = msg_scrollbar.set

        # Status Frames
        status_frame = ttk.Frame(right_container)
        status_frame.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)
        status_frame.columnconfigure(2, weight=0)

        ttk.Label(status_frame, text="Statut :", font=("Helvetica", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.transmission_label = ttk.Label(
            status_frame,
            text="Inactif",
            font=("Helvetica", 12),
            background="#6c757d",
            foreground="white",
            padding=5
        )
        self.transmission_label.grid(row=0, column=1, sticky="w", padx=10)

        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress.grid(row=0, column=2, sticky="ew", padx=(10, 0))
        self.progress.stop()

        status_bar = ttk.Label(
            right_container,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor='w'
        )
        status_bar.grid(row=5, column=0, sticky="ew", pady=(0,5))

        receiver_status_bar = ttk.Label(
            right_container,
            textvariable=self.receiver_status_var,
            relief=tk.SUNKEN,
            anchor='w'
        )
        receiver_status_bar.grid(row=6, column=0, sticky="ew")

        # Configure grid weights for the main scrollable frame
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        self.scrollable_frame.grid_columnconfigure(1, weight=1)

        # Configure grid weights for right_container to allow messages_frame to expand
        right_container.grid_rowconfigure(3, weight=1)  # messages_frame row
        right_container.grid_columnconfigure(0, weight=1)


    def populate_device_combobox(self):
        from core import list_hackrf_devices
        devices = list_hackrf_devices()
        if not devices:
            self.device_combobox['values'] = ["Aucun appareil HackRF détecté"]
            self.device_combobox.current(0)
            self.device_combobox.config(state="disabled")
            self.status_var.set("Aucun appareil HackRF détecté. Veuillez connecter un appareil.")
        else:
            device_list = [f"HackRF {dev['index']}" for dev in devices]
            self.device_combobox['values'] = device_list
            self.device_combobox.current(0)
            self.device_combobox.bind("<<ComboboxSelected>>", self.on_device_selected)
            self.device_index_var.set(devices[0]['index'])
            self.status_var.set(f"{len(devices)} appareil(s) HackRF détecté(s).")

    def on_device_selected(self, event):
        from core import list_hackrf_devices, start_receiver
        selection = self.device_combobox.current()
        devices = list_hackrf_devices()
        if devices:
            if selection < len(devices):
                selected_device = devices[selection]
                self.device_index_var.set(selected_device['index'])
                self.status_var.set(f"Appareil HackRF {selected_device['index']} sélectionné - Série : {selected_device['serial']}")
                print(f"Appareil HackRF {selected_device['index']} sélectionné - Série : {selected_device['serial']}")

                self.receiver_stop_event.set()
                self.receiver_thread.join()
                time.sleep(1)

                self.receiver_stop_event.clear()
                from core import start_receiver as sr
                self.receiver_thread = threading.Thread(
                    target=sr,
                    args=(self.receiver_stop_event, self.received_message_queue, self.device_index_var.get(), self.frequency_var.get()),
                    daemon=True
                )
                self.receiver_thread.start()

                self.receiver_status_var.set("Récepteur en cours")
                self.status_var.set(f"Récepteur redémarré pour l'appareil {selected_device['index']}.")
                print(f"Récepteur redémarré pour l'appareil {selected_device['index']}.")
            else:
                self.status_var.set("Index de l'appareil sélectionné hors de portée.")
                print("Index de l'appareil sélectionné hors de portée.")
        else:
            self.device_index_var.set(0)
            self.status_var.set("Aucun appareil HackRF détecté.")

    def apply_all_settings(self):
        try:
            gain = float(self.gain_entry.get())
            if_gain = float(self.if_gain_entry.get())
            self.gain_var.set(gain)
            self.if_gain_var.set(if_gain)

            frequency_mhz = float(self.frequency_entry.get())
            if not (0 < frequency_mhz < 3000):
                raise ValueError("Fréquence hors de la plage valide.")
            self.frequency_var.set(frequency_mhz * 1e6)
            self.freq_notification.config(text="Fréquence mise à jour avec succès.", foreground="green")

            callsign_source = self.get_callsign_source()
            callsign_dest = self.get_callsign_dest()
            if not self.validate_source_callsign(callsign_source):
                raise ValueError("Le Callsign source doit comporter 3 à 6 caractères alphanumériques.")
            if not self.validate_dest_callsign(callsign_dest):
                raise ValueError("Le Callsign destination doit comporter 3 à 10 caractères alphanumériques ou des tirets.")

            flags_before = int(self.flags_before_entry.get())
            flags_after = int(self.flags_after_entry.get())
            if flags_before < 0 or flags_after < 0:
                raise ValueError("Les flags doivent être des entiers non négatifs.")
            self.num_flags_before.set(flags_before)
            self.num_flags_after.set(flags_after)

            ip = self.send_ip_entry.get().strip()
            port_str = self.send_port_entry.get().strip()
            port = int(port_str)
            if port <= 0 or port > 65535:
                raise ValueError("Le port doit être compris entre 1 et 65535.")

            self.send_ip = ip
            self.send_port = port

            self.status_var.set("Tous les paramètres ont été mis à jour.")
            self.callsign_notification.config(text="Paramètres Callsign appliqués.", foreground="green")

            self.save_config()

            print("Tous les paramètres ont été appliqués avec succès.")
        except ValueError as ve:
            self.status_var.set(f"Erreur : {ve}")
            print(f"Erreur : {ve}")

    def queue_test_message(self):
        # Cette méthode reste inchangée, car elle sert à envoyer un message APRS de test
        # Mais en mode Carrier Only, ce message n'est pas utilisé. On pourrait l'ignorer ou
        # envoyer quand même un message factice.
        # Ici, on garde le code tel quel, mais sachez qu'en mode Carrier Only, le message est sans effet.
        try:
            callsign_source = self.get_callsign_source()
            callsign_dest = self.get_callsign_dest()
            if not self.validate_source_callsign(callsign_source):
                self.callsign_notification.config(
                    text="Le Callsign source doit comporter 3 à 6 caractères alphanumériques.",
                    foreground="red"
                )
                self.status_var.set("Entrée de Callsign source invalide.")
                print("Entrée de Callsign source invalide.")
                return
            if not self.validate_dest_callsign(callsign_dest):
                self.callsign_notification.config(
                    text="Le Callsign destination doit comporter 3 à 10 caractères alphanumériques ou des tirets.",
                    foreground="red"
                )
                self.status_var.set("Entrée de Callsign destination invalide.")
                print("Entrée de Callsign destination invalide.")
                return

            flags_before = self.num_flags_before.get()
            flags_after = self.num_flags_after.get()
            device_index = self.device_index_var.get()
            carrier_only = self.carrier_only_var.get()

            aprs_message = self.test_message_entry.get().strip()
            if not aprs_message:
                aprs_message = "TEST"

            if carrier_only:
                aprs_message = "CARRIER ONLY"

            self.message_queue.put((aprs_message, flags_before, flags_after, device_index, carrier_only))

            self.callsign_notification.config(text="Message de test en file d'attente.", foreground="green")
            self.status_var.set(f"Message de test en file d'attente : {aprs_message}")
            print(f"Message de test en file d'attente : {aprs_message}, flags_before : {flags_before}, flags_after : {flags_after}, device_index : {device_index}, carrier_only : {carrier_only}")
            self.save_config()
        except Exception as e:
            self.callsign_notification.config(text=f"Erreur : {e}", foreground="red")
            self.status_var.set("Erreur lors de l'envoi du message de test.")
            print(f"Erreur lors de l'envoi du message de test : {e}")

    def toggle_carrier_only(self):
        carrier_only = self.carrier_only_var.get()
        if carrier_only:
            # Activer le mode Carrier Only
            # Créer et démarrer le top block
            self.start_carrier_transmission()
        else:
            # Désactiver le mode Carrier Only
            # Arrêter le top block
            self.stop_carrier_transmission()

    def start_carrier_transmission(self):
        # S'assurer qu'aucun autre top block carrier n'est en cours
        reset_hackrf()
        self.receiver_stop_event.set()
        self.receiver_thread.join()
        time.sleep(1)
        if self.carrier_top_block is not None:
            # Si déjà actif, on ne fait rien
            print("Carrier only déjà actif.")
            return

        try:
            gain = float(self.gain_entry.get())
            if_gain = float(self.if_gain_entry.get())
            current_frequency = self.frequency_var.get()

            self.carrier_top_block = ResampleAndSend(
                input_file=None,
                output_rate=2205000,
                device_index=self.device_index_var.get(),
                carrier_only=True,
                carrier_freq=current_frequency
            )

            if self.carrier_top_block.initialize_hackrf(gain, if_gain):
                self.carrier_top_block.set_center_freq(current_frequency)
                self.carrier_top_block.start()
                self.transmitting_var.set()
                self.status_var.set("Carrier only transmission active.")
                print("Carrier only transmission started.")
            else:
                # Échec d'initialisation HackRF
                self.carrier_top_block = None
                self.carrier_only_var.set(False)
                self.status_var.set("Échec de l'initialisation du HackRF pour le mode Carrier Only.")
                print("Échec de l'initialisation du HackRF pour le mode Carrier Only.")
        except Exception as e:
            self.carrier_top_block = None
            self.carrier_only_var.set(False)
            self.status_var.set(f"Erreur lors du démarrage du mode Carrier Only : {e}")
            print(f"Erreur lors du démarrage du mode Carrier Only : {e}")

    def stop_carrier_transmission(self):
        if self.carrier_top_block is not None:
            try:
                self.carrier_top_block.stop_and_wait()
                self.carrier_top_block = None
                self.transmitting_var.clear()
                self.status_var.set("Carrier only transmission stopped.")
                print("Carrier only transmission stopped.")
                self.receiver_stop_event.set()
                self.receiver_thread.join()
                time.sleep(1)

                self.receiver_stop_event.clear()
                from core import start_receiver as sr
                self.receiver_thread = threading.Thread(
                    target=sr,
                    args=(self.receiver_stop_event, self.received_message_queue, self.device_index_var.get(), self.frequency_var.get()),
                    daemon=True
                )
                self.receiver_thread.start()
            except Exception as e:
                self.status_var.set(f"Erreur lors de l'arrêt du mode Carrier Only : {e}")
                print(f"Erreur lors de l'arrêt du mode Carrier Only : {e}")

    def validate_source_callsign(self, callsign):
        return bool(re.fullmatch(r'[A-Za-z0-9]{3,6}', callsign))

    def validate_dest_callsign(self, callsign):
        return bool(re.fullmatch(r'[A-Za-z0-9\-]{3,10}', callsign))

    def get_callsign_source(self):
        return self.callsign_entry.get().strip()

    def get_callsign_dest(self):
        return self.dest_callsign_entry.get().strip()

    def check_transmission_status(self):
        if self.transmitting_var.is_set():
            self.transmission_label.config(text="Transmission", background="#28a745")
        else:
            self.transmission_label.config(text="Inactif", background="#6c757d")
        self.after(500, self.check_transmission_status)

    def check_received_messages(self):
        from queue import Empty
        try:
            while True:
                message = self.received_message_queue.get_nowait()
                self.messages_text.insert('end', '\n' + message + '\n')
                self.messages_text.see('end')
                self.udp_transmitter_func(self.send_ip, self.send_port, message)
        except Empty:
            pass
        self.after(500, self.check_received_messages)

    def update_udp_settings(self):
        ip = self.send_ip_entry.get().strip()
        port_str = self.send_port_entry.get().strip()

        try:
            port = int(port_str)
            if port <= 0 or port > 65535:
                raise ValueError("Le port doit être compris entre 1 et 65535.")
        except ValueError as ve:
            self.status_var.set(f"Port invalide : {ve}")
            print(f"Port invalide : {ve}")
            return

        self.send_ip = ip
        self.send_port = port
        self.status_var.set(f"Paramètres UDP mis à jour : {ip}:{port}")
        print(f"Paramètres UDP mis à jour : {ip}:{port}")
        self.save_config()

    def save_config(self):
        config = {
            "frequency_hz": self.frequency_var.get(),
            "gain": self.gain_var.get(),
            "if_gain": self.if_gain_var.get(),
            "callsign_source": self.get_callsign_source(),
            "callsign_dest": self.get_callsign_dest(),
            "flags_before": int(self.flags_before_entry.get()),
            "flags_after": int(self.flags_after_entry.get()),
            "send_ip": self.send_ip,
            "send_port": self.send_port,
            "carrier_only": self.carrier_only_var.get()
        }
        with open(self.CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
        print("Configuration enregistrée.")

    def load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            with open(self.CONFIG_FILE, "r") as f:
                config = json.load(f)
            self.frequency_var.set(config.get("frequency_hz", 28.12e6))
            self.gain_var.set(config.get("gain", 14))
            self.if_gain_var.set(config.get("if_gain", 47))
            self.saved_callsign = config.get("callsign_source", "VE2FPD")
            self.saved_dest_callsign = config.get("callsign_dest", "VE2FPD")
            self.num_flags_before.set(config.get("flags_before", 10))
            self.num_flags_after.set(config.get("flags_after", 4))
            self.send_ip = config.get("send_ip", "127.0.0.1")
            self.send_port = config.get("send_port", 14581)
            carrier_only = config.get("carrier_only", False)
            self.carrier_only_var = tk.BooleanVar(value=carrier_only)
            print("Configuration chargée.")
        else:
            self.carrier_only_var = tk.BooleanVar(value=False)
            print("Aucun fichier de configuration trouvé ; utilisation des valeurs par défaut.")
