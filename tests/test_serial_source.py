import serial

from blackout_mesh.serial_source import read_serial


class FakeSerialPort:
    """Stands in for pyserial's Serial: a fixed script of readline()
    results, raising serial.SerialException where the real board would
    have gone silent (disconnected).
    """

    def __init__(self, port, baud, timeout=1):
        self.port = port
        self._lines = list(FakeSerialPort.SCRIPT)

    def readline(self):
        line = self._lines.pop(0)
        if line is FakeSerialPort.DISCONNECT:
            raise serial.SerialException("device disconnected")
        return line

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


DISCONNECT = object()
FakeSerialPort.DISCONNECT = DISCONNECT
FakeSerialPort.SCRIPT = [
    b'{"node":1,"seq":1,"ts":10,"voltage":3.3,"current":0.4,"anomaly":0.02,"state":0,"heartbeat":true}\n',
    DISCONNECT,
]


class ReconnectingFakePort(FakeSerialPort):
    """First connection attempt dies after one good line; the second
    connection attempt (the reconnect) succeeds and yields more data.
    """

    _factory_calls = 0

    def __init__(self, port, baud, timeout=1):
        super().__init__(port, baud, timeout)
        ReconnectingFakePort._factory_calls += 1
        if ReconnectingFakePort._factory_calls == 1:
            self._lines = [
                b'{"node":1,"seq":1,"ts":10,"voltage":3.3,"current":0.4,"anomaly":0.02,"state":0,"heartbeat":true}\n',
                DISCONNECT,
            ]
        else:
            self._lines = [
                b'{"node":1,"seq":2,"ts":20,"voltage":3.31,"current":0.4,"anomaly":0.02,"state":0,"heartbeat":true}\n',
            ]


def test_reads_readings_until_disconnect():
    gen = read_serial(port="/dev/fake", serial_factory=FakeSerialPort)
    reading = next(gen)
    assert reading.node_id == "N1"
    assert reading.seq == 1


def test_reconnects_after_disconnect(monkeypatch):
    ReconnectingFakePort._factory_calls = 0
    monkeypatch.setattr("time.sleep", lambda _seconds: None)  # skip the real retry delay

    gen = read_serial(port="/dev/fake", serial_factory=ReconnectingFakePort, reconnect_delay_s=0)
    first = next(gen)
    second = next(gen)

    assert first.seq == 1
    assert second.seq == 2  # came from the second (reconnected) port instance
    assert ReconnectingFakePort._factory_calls == 2
