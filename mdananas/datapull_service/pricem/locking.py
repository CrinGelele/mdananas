from contextlib import contextmanager

from django.db import connections

from .errors import ImportConfigurationError, ImportLockLost


def assert_import_lock():
    with connections["ideal"].cursor() as cursor:
        cursor.execute(
            "SELECT APPLOCK_MODE('public', %s, 'Session')", ["mdananas.priceva.import"]
        )
        if cursor.fetchone()[0] != "Exclusive":
            raise ImportLockLost(
                "SQL session lost the Priceva import lock; next tick will recover"
            )


@contextmanager
def import_lock():
    connection = connections["ideal"]
    if connection.vendor != "microsoft":
        raise ImportConfigurationError("The Priceva worker requires SQL Server")
    connection.ensure_connection()
    session = connection.connection
    with connection.cursor() as cursor:
        cursor.execute(
            """
            DECLARE @result int;
            EXEC @result = sys.sp_getapplock
                @Resource = %s, @LockMode = 'Exclusive',
                @LockOwner = 'Session', @LockTimeout = 0;
            SELECT @result;
        """,
            ["mdananas.priceva.import"],
        )
        result = cursor.fetchone()[0]
    if result == -1:
        yield False
        return
    if result in (-2, -3):
        raise ImportLockLost(
            f"SQL Server cancelled the Priceva lock (code {result}); retry next tick"
        )
    if result < 0:
        raise ImportConfigurationError(
            f"SQL Server refused the Priceva lock (code {result})"
        )
    try:
        yield True
    finally:
        if connection.connection is session:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        EXEC sys.sp_releaseapplock @Resource = %s, @LockOwner = 'Session';
                    """,
                        ["mdananas.priceva.import"],
                    )
            except Exception:
                # Closing the session releases its locks, including after a DB error.
                connection.close()
