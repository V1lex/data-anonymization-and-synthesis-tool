# Ошибки доменного уровня (генерация)
class GenerationError(Exception):
    """Возникает, когда генерация данных не может быть выполнена."""


# Ошибки слоя IO (чтение/запись CSV)
class CsvError(GenerationError):
    """Базовая ошибка при работе с CSV."""


class CsvEmptyError(CsvError):
    """Возникает, когда CSV пустой."""


class CsvMalformedError(CsvError):
    """Возникает при некорректной структуре CSV."""


class CsvInvalidHeaderError(CsvError):
    """Возникает при отсутствующем или невалидном заголовке CSV."""
