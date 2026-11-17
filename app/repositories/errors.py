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
