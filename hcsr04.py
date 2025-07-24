import machine
import time
from machine import Pin

__version__ = '0.2.1'
__author__ = 'Equipo Ecoteknia'
__license__ = "Apache License 2.0. https://www.apache.org/licenses/LICENSE-2.0"

class HCSR04:
    """
    Driver para el sensor ultrasónico HC-SR04.
    Rango del sensor entre 2 cm y 400 cm (4 m).

    Si el eco tarda mucho, lanza una excepción OSError('Out of range').
    """

    def __init__(self, trigger_pin, echo_pin, echo_timeout_us=500*2*30):
        """
        trigger_pin: pin de salida para enviar pulsos.
        echo_pin: pin de entrada para recibir eco. Requiere resistencia de 1kΩ para protección.
        echo_timeout_us: tiempo máximo de espera para el eco (en microsegundos).
        """
        self.echo_timeout_us = echo_timeout_us

        # Configuración de pines
        self.trigger = Pin(trigger_pin, mode=Pin.OUT)
        self.trigger.value(0)

        self.echo = Pin(echo_pin, mode=Pin.IN)

    def _send_pulse_and_wait(self):
        """
        Enviar un pulso por el pin de trigger y esperar el eco.
        Usa machine.time_pulse_us para medir duración del eco.
        """
        self.trigger.value(0)
        time.sleep_us(5)
        self.trigger.value(1)
        time.sleep_us(10)
        self.trigger.value(0)

        try:
            pulse_time = machine.time_pulse_us(self.echo, 1, self.echo_timeout_us)
            return pulse_time
        except OSError as ex:
            if ex.args[0] == 110:  # 110 = ETIMEDOUT
                raise OSError('Out of range')
            raise ex

    def distance_mm(self):
        """
        Obtener distancia en milímetros (entero).
        """
        pulse_time = self._send_pulse_and_wait()
        mm = pulse_time * 100 // 582
        return mm

    def distance_cm(self):
        """
        Obtener distancia en centímetros (float).
        """
        pulse_time = self._send_pulse_and_wait()
        cms = (pulse_time / 2) / 29.1
        return cms