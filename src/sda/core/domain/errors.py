class SdaError(Exception):
    """Базовая ошибка приложения с данными для web-ответа."""

    error_code = "internal_error"
    status_code = 500

    def __init__(
        self,
        message: str,
        *,
        details: dict | None = None,
        error_code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        if error_code is not None:
            self.error_code = error_code
        if status_code is not None:
            self.status_code = status_code


class GenerationError(SdaError):
    """Возникает, когда генерация данных не может быть выполнена."""

    error_code = "generation_failed"
    status_code = 400


class TemplateNotFoundError(GenerationError):
    """Возникает, когда запрошенный шаблон отсутствует."""

    error_code = "template_not_found"
    status_code = 404


class CsvError(SdaError):
    """Базовая ошибка при работе с CSV."""

    error_code = "csv_error"
    status_code = 400


class InvalidFileTypeError(CsvError):
    """Возникает, когда загружен не CSV-файл."""

    error_code = "invalid_file_type"


class FileTooLargeError(CsvError):
    """Возникает, когда CSV превышает допустимый размер."""

    error_code = "file_too_large"
    status_code = 413


class CsvEmptyError(CsvError):
    """Возникает, когда CSV пустой."""

    error_code = "empty_file"


class CsvMalformedError(CsvError):
    """Возникает при некорректной структуре CSV."""

    error_code = "csv_parse_error"


class CsvInvalidHeaderError(CsvError):
    """Возникает при отсутствующем или невалидном заголовке CSV."""

    error_code = "invalid_header"


class ValidationError(SdaError):
    """Возникает, когда нарушены ограничения API/use case."""

    error_code = "validation_error"
    status_code = 422


class UploadNotFoundError(SdaError):
    """Возникает, когда upload_id не найден."""

    error_code = "upload_not_found"
    status_code = 404


class AnalysisNotFoundError(SdaError):
    """Возникает, когда analysis_id не найден."""

    error_code = "analysis_not_found"
    status_code = 404


class UnknownColumnError(SdaError):
    """Возникает, когда правило ссылается на отсутствующую колонку."""

    error_code = "unknown_column"
    status_code = 400


class InvalidRuleError(SdaError):
    """Возникает, когда правило анонимизации не может быть применено."""

    error_code = "invalid_rule"
    status_code = 400


class UploadProcessingError(SdaError):
    """Возникает, когда загрузка CSV завершилась внутренней ошибкой."""

    error_code = "upload_processing_failed"
    status_code = 500


class AnonymizationFailedError(SdaError):
    """Возникает, когда анонимизация завершилась внутренней ошибкой."""

    error_code = "anonymization_failed"
    status_code = 500


class AnalysisFailedError(SdaError):
    """Возникает, когда анализ CSV для Similar завершился внутренней ошибкой."""

    error_code = "analysis_failed"
    status_code = 500


class SynthesisFailedError(SdaError):
    """Возникает, когда генерация похожего CSV завершилась внутренней ошибкой."""

    error_code = "synthesis_failed"
    status_code = 500
