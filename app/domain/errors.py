import uuid


class ConflictError(Exception):
    pass


class DuplicateSerialNumberError(ConflictError):
    def __init__(self, serial_number: str, message: str | None = None):
        self.serial_number = serial_number
        super().__init__(message or f"Duplicate serial number: '{serial_number}'.")


class DuplicatePumpNumberError(ConflictError):
    def __init__(
        self, station_id: uuid.UUID, pump_number: int, message: str | None = None
    ):
        self.station_id = station_id
        self.pump_number = pump_number
        super().__init__(
            message
            or f"Duplicate pump number {pump_number} for station '{station_id}'."
        )


class NotFoundError(Exception):
    pass


class StationNotFoundError(NotFoundError):
    def __init__(self, station_id: uuid.UUID, message: str | None = None):
        self.station_id = station_id
        super().__init__(message or f"Station {station_id} not found")


class TerminalNotFoundError(NotFoundError):
    def __init__(self, terminal_id: uuid.UUID, message: str | None = None):
        self.terminal_id = terminal_id
        super().__init__(message or f"Terminal {terminal_id} not found")
