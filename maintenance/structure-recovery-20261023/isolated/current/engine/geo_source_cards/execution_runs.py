"""Server-authorized execution identity, without timeout-based replay."""

from pathlib import Path

from .runtime import atomic_json, process_lock
from .staged_editorial import read


def authorize(root, ticket, client, run_id):
    from .daily_editorial import IDENTIFIER

    if any(not IDENTIFIER.fullmatch(value) for value in (ticket, client, run_id)):
        raise ValueError("Invalid execution identifier")
    root = Path(root)
    with process_lock(root / "coordinator.lock"):
        path = root / "queue" / ticket / "ticket.json"
        job = read(path)
        if job["state"] != "claimed" or job.get("client") != client:
            raise ValueError("Execution requires an active claim by this client")
        execution = {"run_id": run_id, "generation": 1}
        if job.get("execution"):
            if job["execution"] != execution:
                raise ValueError(
                    "Previous execution must be reconciled before another run"
                )
            return job
        if (path.parent / "receipt.json").exists():
            raise ValueError(
                "Delivered execution must be reconciled before authorization"
            )
        job["execution"] = execution
        atomic_json(path, job)
        return job


def verify_execution(job, receipt):
    current = job.get("execution")
    submitted = receipt.get("execution")
    if current != submitted:
        raise ValueError("Stale, missing or unauthorized execution receipt")
